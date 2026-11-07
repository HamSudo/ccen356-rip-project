"""
visualize.py - generate convergence comparison and route-change timeline charts.

Reads data/results.csv (or builds it from data/debug_logs/ + data/monitor_logs/)
and plots:
  1. convergence_comparison.png    every run of every test as a dot, with the
                                   mean marked, against RIP's timer values
  2. timeline_<test>_<router>.png  the watched route's state over time (direct,
                                   backup, possibly down, gone) from a
                                   monitor_convergence.py log

    python scripts/visualize.py
    python scripts/visualize.py --results data/results.csv --timeline data/monitor_logs/T1-run1_LIB-R1.csv

T5 (~240-270 s) is an order of magnitude longer than T1..T4 (~5-30 s), so the
comparison figure puts the link tests and the silent failure in two panels,
each on its own scale, with the timer that explains each one drawn on it.
Only 3-4 runs exist per test, so the runs are shown as dots rather than hidden
inside a bar.

Whenever any input row is marked 'simulated', the chart title, watermark and
file name clearly mark it as SIMULATED SAMPLE DATA so it can never be mistaken
for real lab measurements.
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless-safe for tests and SSH terminals
import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory

from collect_results import collect, load_results_csv, summarize_by_test, write_results_csv
from experiments import EXPERIMENTS, FAILURE_TESTS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHARTS_DIR = DATA_DIR / "charts"

SIM_WATERMARK = "SIMULATED SAMPLE DATA — NOT FROM PHYSICAL ROUTERS"

# One palette for every chart. Ink colours carry text and reference lines;
# a single blue carries the data, so colour never competes with the labels.
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = "#2a78d6"
BAND = "#cde2fb"   # light step of the same blue, for "expected range" shading
GAP = "#ecebe6"    # shading for times the monitor could not see the router

LINK_TESTS = ["T1", "T2", "T3", "T4"]


def _float(val):
    if val in (None, ""):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def is_simulated_rows(rows, force=False):
    if force:
        return True
    for r in rows:
        src = str(r.get("source") or r.get("detail") or "").lower()
        if "sim" in src:
            return True
    return False


def _stamp_simulated(fig):
    """Add an unmistakable banner and diagonal watermark to a simulated chart."""
    fig.text(0.5, 0.995, SIM_WATERMARK, ha="center", va="top", fontsize=10,
             fontweight="bold", color="#8b0000",
             bbox={"boxstyle": "round,pad=0.3", "facecolor": "#ffe8e8", "edgecolor": "#cc0000"})
    fig.text(0.5, 0.5, "SIMULATED SAMPLE", ha="center", va="center", fontsize=34,
             fontweight="bold", color="#cc0000", alpha=0.10, rotation=22)


def _style_axes(ax):
    """Recessive frame: hairline grid on y only, no top/right spines, muted ticks."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelcolor=INK_2, labelsize=9, length=3)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _titles(fig, title, subtitle, sim):
    """Left-aligned title and one-line subtitle, the way a report figure reads."""
    top = 0.95 if sim else 0.98
    fig.text(0.012, top, title + (" [SIMULATED SAMPLE DATA]" if sim else ""),
             ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.012, top - 0.075, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)


def _short_title(test):
    return {
        "T1": "Library–Teachers\nlink down",
        "T2": "Library–Lab\nlink down",
        "T3": "Teachers–Lab\nlink down",
        "T4": "Library–Teachers\nlink restored",
        "T5": "LAB-R3 stops\nsending updates",
    }.get(test, test)


def _draw_runs(ax, tests, summary):
    """Dots for each run, a short black line for the mean, the mean as text beside it."""
    for idx, t in enumerate(tests):
        s = summary.get(t) or {"runs": {}, "values": [], "avg": None}
        runs = [v for _, v in sorted(s["runs"].items())]
        n = len(runs)
        for k, val in enumerate(runs):
            # Spread the dots sideways so equal values never hide each other
            dx = (k - (n - 1) / 2) * 0.09
            ax.scatter(idx + dx, val, s=52, color=SERIES, edgecolor="white", linewidth=1.4, zorder=3)
        if s["avg"] is not None:
            ax.hlines(s["avg"], idx - 0.24, idx + 0.24, color=INK, linewidth=2.2, zorder=4)
            ax.text(idx + 0.28, s["avg"], f"{s['avg']:.1f} s", ha="left", va="center",
                    fontsize=9.5, fontweight="bold", color=INK, zorder=5)
        else:
            ax.text(idx, 0, "no data", ha="center", va="bottom", fontsize=8.5,
                    style="italic", color=MUTED)
    ax.set_xticks(range(len(tests)))
    ax.set_xticklabels([f"{t}\n{_short_title(t)}\n"
                        f"n = {len((summary.get(t) or {}).get('values', []))}" for t in tests],
                       fontsize=8.5)
    ax.set_xlim(-0.6, len(tests) - 0.25)


def _ref_line(ax, y, text, above=True):
    """Horizontal reference line with its label written on it (no legend needed)."""
    ax.axhline(y, color=MUTED, linewidth=1.0, linestyle=(0, (4, 3)), zorder=1)
    trans = blended_transform_factory(ax.transAxes, ax.transData)
    ax.text(0.01, y, text, transform=trans, ha="left", va="bottom" if above else "top",
            fontsize=8.5, color=INK_2,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})


def plot_convergence_comparison(rows, out_path, simulated=False, method_field="debug_convergence_s"):
    """Plot every run of T1..T5 with its mean, against the RIP timers that bound it.

    Returns the saved Path. Handles missing tests or partial runs gracefully.
    """
    sim = is_simulated_rows(rows, force=simulated)
    summary = summarize_by_test(rows, field=method_field)

    fig, (ax_link, ax_silent) = plt.subplots(
        1, 2, figsize=(11, 5.0), gridspec_kw={"width_ratios": [4, 1.45], "wspace": 0.32})

    # Left: link failures and recovery, bounded by one 30 s update interval
    _draw_runs(ax_link, LINK_TESTS, summary)
    link_max = max([v for t in LINK_TESTS for v in (summary.get(t) or {}).get("values", [])] + [0])
    ax_link.set_ylim(0, max(36.0, link_max * 1.15))
    _ref_line(ax_link, 30, "RIP update interval (30 s)")
    ax_link.set_ylabel("Convergence time (s)", fontsize=9.5, color=INK_2)
    ax_link.set_title("Link failures and recovery", loc="left", fontsize=10.5,
                      fontweight="bold", color=INK, pad=10)

    # Right: silent failure, bounded by the flush timer plus one update
    _draw_runs(ax_silent, ["T5"], summary)
    ax_silent.axhspan(240, 270, color=BAND, alpha=0.7, zorder=0, linewidth=0)
    t5_max = max((summary.get("T5") or {}).get("values", []) + [0])
    ax_silent.set_ylim(0, max(300.0, t5_max * 1.1))
    _ref_line(ax_silent, 180, "invalid (180 s)")
    _ref_line(ax_silent, 240, "flush (240 s)", above=False)
    ax_silent.text(0.01, 271, "expected:\nflush + next update", ha="left", va="bottom",
                   transform=blended_transform_factory(ax_silent.transAxes, ax_silent.transData),
                   fontsize=8, color=INK_2)
    ax_silent.set_ylabel("Convergence time (s)", fontsize=9.5, color=INK_2)
    ax_silent.set_title("Silent failure", loc="left", fontsize=10.5,
                        fontweight="bold", color=INK, pad=10)

    for ax in (ax_link, ax_silent):
        _style_axes(ax)

    _titles(fig, "RIPv2 convergence time per test",
            "Each dot is one run; the black line is the mean. The two panels use different "
            "scales. Measured from each router's debug log.", sim)
    if sim:
        _stamp_simulated(fig)

    fig.subplots_adjust(left=0.06, right=0.985, top=0.75 if sim else 0.78, bottom=0.19)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, facecolor="white")
    plt.close(fig)
    return out_path


def load_monitor_csv(path):
    """Read a monitor_convergence.py event CSV, skipping malformed lines."""
    path = Path(path)
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "event" not in reader.fieldnames:
            return []
        for raw in reader:
            if not raw:
                continue
            t = _float(raw.get("t_rel_s"))
            if t is None and raw.get("obs_time"):
                try:
                    t = datetime.fromisoformat(raw["obs_time"]).timestamp()
                except ValueError:
                    t = None
            if t is None:
                continue
            rows.append({**raw, "_t": t})
    if rows and rows[0]["_t"] > 1e6:
        t0 = rows[0]["_t"]
        for r in rows:
            r["_t"] = round(r["_t"] - t0, 3)
    return rows


def load_polls_csv(event_csv_path):
    """Load the matching _polls.csv if present next to the event CSV."""
    p = Path(event_csv_path)
    polls_path = p.with_name(p.stem + "_polls.csv")
    if not polls_path.is_file():
        return []
    out = []
    with polls_path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "t_rel_s" not in reader.fieldnames:
            return []
        for raw in reader:
            t = _float(raw.get("t_rel_s"))
            if t is not None:
                out.append({**raw, "_t": t})
    return out


def _choose_target_network(rows, network=None):
    if network:
        return network
    # 1. Explicit target recorded in monitor_start detail or converged row
    for r in rows:
        if r.get("event") == "converged" and r.get("network"):
            return r["network"]
        if r.get("event") == "monitor_start":
            for part in (r.get("detail") or "").split(";"):
                if "target=" in part:
                    val = part.split("target=", 1)[1].strip()
                    if val and val != "all":
                        return val
    # 2. Prefer a 192.168.x.0/24 room LAN that changed over a 10.0.x.0/30 transit link
    change_evs = ("route_changed", "route_lost", "route_restored", "possibly_down")
    for r in rows:
        if r.get("event") in change_evs and (r.get("network") or "").startswith("192.168."):
            return r["network"]
    for r in rows:
        if r.get("event") in change_evs and r.get("network"):
            return r["network"]
    for r in rows:
        if (r.get("network") or "").startswith("192.168."):
            return r["network"]
    for r in rows:
        if r.get("network"):
            return r["network"]
    return "unknown"


def build_route_series(rows, network, polls=None):
    """Build step points (t, metric_display, status, next_hop) for `network`.

    metric_display is 1..15 for 'up', 16 for 'possibly_down', and 0 when missing
    from the routing table so disappearance is clearly visible on the chart.
    """
    points = []
    last_metric, last_status, last_nh = None, "missing", "-"

    for r in rows:
        ev = r.get("event", "")
        t = r["_t"]
        if r.get("network") == network and ev in (
            "baseline", "route_added", "route_restored", "route_changed", "possibly_down", "route_lost"
        ):
            if ev == "route_lost" or "not in routing table" in (r.get("detail") or ""):
                last_metric, last_status, last_nh = 0, "missing", "-"
            else:
                m = _float(r.get("metric_after"))
                st = (r.get("status_after") or "up").strip()
                nh = (r.get("next_hop_after") or "-").strip()
                if st == "possibly_down" or m == 16:
                    last_metric, last_status, last_nh = 16, "possibly_down", nh
                elif m is not None:
                    last_metric, last_status, last_nh = int(m), "up", nh
            points.append((t, last_metric, last_status, last_nh, ev))
        elif ev == "monitor_stop" and points:
            points.append((t, last_metric, last_status, last_nh, "end"))

    if not points and polls:
        for p in polls:
            points.append((p["_t"], 0, "missing", "-", "poll"))
    return points


# Route states on the timeline, best at the top: a drop on the chart is the
# route getting worse, a rise is it recovering.
STATE_ROWS = [
    (0, "Not in table"),
    (1, "Possibly down\n(metric 16)"),
    (2, "Backup path\n(metric 2)"),
    (3, "Direct path\n(metric 1)"),
]


def _state_y(metric, status):
    if status == "missing" or metric in (None, 0):
        return 0
    if status == "possibly_down" or metric >= 16:
        return 1
    return 3 if metric <= 1 else 2


def _monitor_gaps(rows, polls, min_gap=2.5):
    """Spans where the monitor could not see the router (slow polls, SSH reconnects), merged."""
    spans = []
    for p in polls:
        iv = _float(p.get("interval_s"))
        if iv is not None and iv > min_gap:
            spans.append([p["_t"] - iv, p["_t"]])
    down_t = None
    for r in rows:
        if r.get("event") == "session_lost":
            down_t = r["_t"]
        elif r.get("event") == "session_restored" and down_t is not None:
            spans.append([down_t, r["_t"]])
            down_t = None
    merged = []
    for s in sorted(spans):
        if merged and s[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], s[1])
        else:
            merged.append(list(s))
    return [tuple(s) for s in merged]


def _split_by_gaps(t0, t1, gaps):
    """Cut [t0, t1] into (start, end, inside_gap) pieces."""
    cuts = sorted({t0, t1, *[g for span in gaps for g in span if t0 < g < t1]})
    pieces = []
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2
        pieces.append((a, b, any(s <= mid <= e for s, e in gaps)))
    return pieces


def _draw_state_line(ax, ts, ys, gaps):
    """Step line: solid where the monitor saw the router, dotted where it could not."""
    for i in range(len(ts) - 1):
        for a, b, hidden in _split_by_gaps(ts[i], ts[i + 1], gaps):
            ax.plot([a, b], [ys[i], ys[i]], color=SERIES, zorder=3, solid_capstyle="butt",
                    linewidth=1.6 if hidden else 2.4, linestyle=(0, (1.5, 2)) if hidden else "-")
        if ys[i + 1] != ys[i]:
            ax.plot([ts[i + 1]] * 2, [ys[i], ys[i + 1]], color=SERIES, linewidth=2.4, zorder=3)


def plot_route_timeline(event_csv_path, out_path=None, network=None, simulated=False, debug_s=None):
    """Plot the watched route's state over one run, with the change and convergence marked.

    debug_s, if given, is the same run's convergence time from the router's debug
    log; it is printed next to the monitor's figure so the two can be compared.
    """
    event_csv_path = Path(event_csv_path)
    rows = load_monitor_csv(event_csv_path)
    polls = load_polls_csv(event_csv_path)
    sim = is_simulated_rows(rows, force=simulated)
    router = next((r.get("router") for r in rows if r.get("router")), event_csv_path.stem.split("_")[-1])
    label = event_csv_path.stem.replace(f"_{router}", "")
    target = _choose_target_network(rows, network)
    points = build_route_series(rows, target, polls)
    gaps = _monitor_gaps(rows, polls)

    fig, ax = plt.subplots(figsize=(11, 4.8))
    _style_axes(ax)
    trans = blended_transform_factory(ax.transData, ax.transAxes)

    for start, end in gaps:
        ax.axvspan(start, end, color=GAP, zorder=0, linewidth=0)
        ax.text((start + end) / 2, 0.02, f"router not\nvisible {end - start:.0f} s", transform=trans,
                ha="center", va="bottom", fontsize=7.5, color=MUTED)

    if not points:
        ax.text(0.5, 0.5, f"No valid route events in {event_csv_path.name}",
                ha="center", va="center", transform=ax.transAxes, fontsize=11, color=INK_2)
    else:
        ts = [p[0] for p in points]
        ys = [_state_y(p[1], p[2]) for p in points]
        _draw_state_line(ax, ts, ys, gaps)
        # A dot and a next-hop label only where the state actually changes
        span = (ts[-1] - ts[0]) or 1.0
        last = None
        for t, m, st, nh, ev in points:
            y = _state_y(m, st)
            key = (y, nh)
            if ev == "end" or key == last:
                continue
            ax.scatter(t, y, s=48, color=SERIES, edgecolor="white", linewidth=1.4, zorder=4)
            if y > 0 and nh not in ("", "-"):
                ax.text(t + span * 0.008, y + 0.12, f"via {nh}", ha="left", va="bottom",
                        fontsize=8.5, color=INK_2, zorder=5,
                        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2})
            last = key

    mark_t = next((r["_t"] for r in rows if r.get("event") == "mark"), None)
    conv_t = next((r["_t"] for r in rows if r.get("event") == "converged"), None)
    if mark_t is not None:
        ax.axvline(mark_t, color=INK_2, linestyle=(0, (4, 3)), linewidth=1.1, zorder=2)
        ax.text(mark_t, 1.01, "change applied", transform=trans, ha="right", va="bottom",
                fontsize=8.5, color=INK_2)
    if conv_t is not None:
        ax.axvline(conv_t, color=INK, linewidth=1.1, zorder=2)
        ax.text(conv_t, 1.01, "new route seen", transform=trans, ha="left", va="bottom",
                fontsize=8.5, color=INK)
    if mark_t is not None and conv_t is not None and conv_t > mark_t:
        hi = conv_t - mark_t
        # If the monitor was blind just before it saw the new route, the switch happened
        # somewhere inside that blind span: report the range, not a false-precise number.
        blind = next((s for s, e in gaps if abs(e - conv_t) <= 1.5 and s < conv_t), None)
        lo = max(0.0, blind - mark_t) if blind is not None else None
        text = f"{lo:.1f}–{hi:.1f} s" if lo is not None else f"{hi:.1f} s"
        ax.annotate("", xy=(conv_t, 3.82), xytext=(mark_t, 3.82),
                    arrowprops={"arrowstyle": "<->", "color": INK, "linewidth": 1.0,
                                "shrinkA": 0, "shrinkB": 0})
        # Centre the figures over a wide bracket; beside the convergence line when narrow
        x_lo, x_hi = ax.get_xlim()
        if (conv_t - mark_t) / (x_hi - x_lo) > 0.35:
            tx, ha = (mark_t + conv_t) / 2, "center"
        else:
            tx, ha = conv_t + (x_hi - x_lo) * 0.012, "left"
        box = {"facecolor": "white", "edgecolor": "none", "pad": 1.0}
        ax.text(tx, 3.88, f"monitor: {text}", ha=ha, va="bottom", fontsize=10,
                fontweight="bold", color=INK, bbox=box, zorder=6)
        if debug_s is not None:
            # The debug figure starts at a different moment than the operator's mark
            start = ("from the last update heard" if label.startswith("T5")
                     else "from link up to new route" if label.startswith("T4")
                     else "from route removal to new route")
            ax.text(tx, 3.76, f"router debug log: {debug_s:.1f} s ({start})", ha=ha, va="top",
                    fontsize=8.5, color=INK_2, bbox=box, zorder=6)

    ax.set_yticks([y for y, _ in STATE_ROWS])
    ax.set_yticklabels([name for _, name in STATE_ROWS], fontsize=8.5)
    ax.set_ylim(-0.45, 4.35)
    ax.set_xlabel("Time since monitoring started (s)", fontsize=9.5, color=INK_2)

    test, _, run = label.partition("-run")
    nice = f"{test} run {run}" if run else label
    _titles(fig, f"{nice}: {router}'s route to {target}",
            "Polled about once a second over SSH. Monitor time runs from the operator's mark to the "
            "first poll showing the new route; dotted = router not visible.", sim)
    if sim:
        _stamp_simulated(fig)

    fig.subplots_adjust(left=0.12, right=0.985, top=0.79 if sim else 0.81, bottom=0.12)
    if out_path is None:
        prefix = "SIMULATED_" if sim else ""
        out_path = CHARTS_DIR / f"{prefix}timeline_{label}_{router}.png"
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, facecolor="white")
    plt.close(fig)
    return out_path


def generate_all_charts(results_path=DATA_DIR / "results.csv",
                        debug_dir=DATA_DIR / "debug_logs",
                        monitor_dir=DATA_DIR / "monitor_logs",
                        charts_dir=CHARTS_DIR,
                        timeline_files=None,
                        simulated=False):
    """Build the comparison chart + timeline charts and return the list of saved PNG paths."""
    results_path = Path(results_path)
    charts_dir = Path(charts_dir)
    rows = load_results_csv(results_path)
    if not rows:
        rows = collect(debug_dir=debug_dir, monitor_dir=monitor_dir,
                       source="simulated" if simulated else "")
        if any(r.get("debug_convergence_s") != "" or r.get("monitor_converged_s") != "" for r in rows):
            write_results_csv(rows, results_path)

    sim = is_simulated_rows(rows, force=simulated)
    prefix = "SIMULATED_" if sim else ""
    saved = []

    comp_path = charts_dir / f"{prefix}convergence_comparison.png"
    saved.append(plot_convergence_comparison(rows, comp_path, simulated=sim))

    if timeline_files is None:
        # Pick one representative run per test if available (preferring T1-run1 and T5-run1)
        candidates = sorted(Path(monitor_dir).glob("*-run1_*.csv"))
        timeline_files = [p for p in candidates if not p.name.endswith("_polls.csv")]
    for csv_path in timeline_files:
        csv_path = Path(csv_path)
        if not csv_path.is_file():
            continue
        c_rows = load_monitor_csv(csv_path)
        c_sim = is_simulated_rows(c_rows, force=sim)
        c_prefix = "SIMULATED_" if c_sim else ""
        out = charts_dir / f"{c_prefix}timeline_{csv_path.stem}.png"
        test, _, rest = csv_path.stem.partition("-run")
        run = rest.split("_")[0]
        debug_s = next((_float(r.get("debug_convergence_s")) for r in rows
                        if r.get("test") == test and str(r.get("run")) == run), None)
        saved.append(plot_route_timeline(csv_path, out, simulated=c_sim, debug_s=debug_s))
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plot RIP convergence charts and route-change timelines.")
    parser.add_argument("--results", type=Path, help="path to results.csv")
    parser.add_argument("--debug-dir", type=Path, help="debug_logs directory")
    parser.add_argument("--monitor-dir", type=Path, help="monitor_logs directory")
    parser.add_argument("--charts-dir", type=Path, help="where to save PNG charts")
    parser.add_argument("--timeline", type=Path, nargs="*", help="specific monitor CSV file(s) to plot")
    args = parser.parse_args(argv)

    results_path = args.results or (DATA_DIR / "results.csv")
    debug_dir = args.debug_dir or (DATA_DIR / "debug_logs")
    monitor_dir = args.monitor_dir or (DATA_DIR / "monitor_logs")
    charts_dir = args.charts_dir or CHARTS_DIR

    saved = generate_all_charts(
        results_path=results_path, debug_dir=debug_dir, monitor_dir=monitor_dir,
        charts_dir=charts_dir, timeline_files=args.timeline,
    )
    for p in saved:
        print(f"Saved chart: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
