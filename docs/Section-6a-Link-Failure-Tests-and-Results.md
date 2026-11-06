# Section 6a — Link-Failure Tests and Results

> **Author:** Zayed (Measurement, Testing and Visualisation)
> **Status:** Results from the lab session on 6 Nov 2026 (Cisco 2901 routers, Catalyst 3560-8PC switches, all-Ethernet design). All values come from `data/results.csv`, built by `scripts/collect_results.py`.

---

## 6a.1 Purpose of the Experiments

The three routers form a triangle between the Library (`LIB-R1`), the Teachers' room (`TCH-R2`) and the Laboratory (`LAB-R3`), so every room LAN (`192.168.10.0/24`, `192.168.20.0/24`, `192.168.30.0/24`) has two paths to every other LAN: a direct 1-hop path and a 2-hop backup through the third router. The lab routers have no serial modules, so the three WAN links are Ethernet VLANs carried through the room switches (VLAN 12, 13 and 23; see `docs/Design-Change-All-Ethernet.md`).

The tests measure how quickly RIPv2 removes a broken route and installs the backup, for two failure modes:

1. **Link failures (`T1`–`T3`) and recovery (`T4`):** the router sees its own interface go down (or up), deletes the routes through it at once and sends a triggered update. RIP keeps no backup route, so the router then waits for its surviving neighbour's next periodic update (every 30 s) to learn the 2-hop path.
2. **Silent neighbour failure (`T5`):** `LAB-R3` stops sending updates to `LIB-R1` (`passive-interface GigabitEthernet0/1`) while the link stays up. `LIB-R1` gets no interface event and waits for RIP's timers: 180 s invalid (route `possibly down`, metric 16), 240 s flush, then the next update from `TCH-R2`.

Because each WAN link passes through a switch, a router does not see the far end's port go down. Every link test therefore shuts **both ends** of the link, as a cut cable would: the measured router's physical `G0/1` on "go", then the far end's subinterface a few seconds later.

---

## 6a.2 Test Methodology and Measurement Techniques

Each test was run **three times** (`T1` four times: the extra cut put the link down again so the last `T4` run could start). Before the first test, [`configs/push/timestamps.txt`](../configs/push/timestamps.txt) was pushed to all three routers with [`scripts/push_config.py`](../scripts/push_config.py), and all router clocks were set to the laptop's time:

```text
service timestamps debug datetime msec
service timestamps log datetime msec
logging buffered 64000 debugging
```

Each run was driven by [`scripts/run_experiment.py`](../scripts/run_experiment.py), which takes a before-snapshot, checks the starting state, clears the log buffer, turns on `debug ip rip` and `debug ip routing`, runs the route monitor, reads the debug buffer back, turns debugging off, takes an after-snapshot and prints the route changes. Three measurements were taken:

1. **Router debug log (primary, millisecond precision).** [`scripts/parse_rip_debug.py`](../scripts/parse_rip_debug.py) measures on the measured router's own clock:
   - **Start:** for `T1`–`T3`, the first `RT: del` of the failed route. IOS deletes the routes the moment `shutdown` is entered but logs `%LINK-5-CHANGED` about 2 s later (16:25:28.223 vs 16:25:30.219 in `T1` run 1), so the `%LINK` line would understate convergence by 2 s. For `T4`, the `%LINK` line of the interface coming up. For `T5`, the last `RIP: received v2 update` from the silent neighbour (`10.0.13.2`), where the invalid timer starts.
   - **End:** the `RT: add <network> via <next hop>, rip metric [120/<m>]` line where the new route is installed.
2. **Python route monitor (about 1 s granularity).** [`scripts/monitor_convergence.py`](../scripts/monitor_convergence.py) polls `show ip route rip` once a second over one SSH session, logs every change, and counts a run as converged once the new route has held for 35 s. Its times are measured from the operator's Enter keypress, which landed 0.3–4 s from the real failure, so the monitor figures are a cross-check, not the result.
3. **Ping loss and path, from a lab PC.** A continuous `ping -O -W 1` (Ubuntu, 1 s timeout) from the Library PC (Teachers' PC for `T3`) to the far router's LAN address, counted with `grep -cE "no answer yet|Unreachable"`, plus a `traceroute` before and after each run. The TTL of the replies shows the return path: 254 direct, 253 through the third router.

---

## 6a.3 Description of Each Test Scenario

| Test | Measured router | Watched route | How the event is triggered | Expected behaviour |
|---|---|---|---|---|
| **T0** Baseline | all | all | All links up; `run_experiment.py T0` | Every remote LAN at metric 1; the far WAN link with two equal-cost paths |
| **T1** Library–Teachers link down | `LIB-R1` | `192.168.20.0/24` | `LIB-R1` console: `interface GigabitEthernet0/1` → `shutdown`; then `t1-far-down.txt` pushed to `TCH-R2` (`G0/0.12`) | Metric 2 via `LAB-R3` (`10.0.13.2`, `G0/0.13`) on `LAB-R3`'s next update (0–30 s) |
| **T2** Library–Lab link down | `LAB-R3` | `192.168.10.0/24` | `t2-measured-down.txt` pushed to `LAB-R3` (`G0/1`); then `LIB-R1` console: `interface GigabitEthernet0/0.13` → `shutdown` | Metric 2 via `TCH-R2` (`10.0.23.1`, `G0/0.23`) on `TCH-R2`'s next update |
| **T3** Teachers–Lab link down | `TCH-R2` | `192.168.30.0/24` | `TCH-R2` console: `interface GigabitEthernet0/1` → `shutdown`; then `t3-far-down.txt` pushed to `LAB-R3` (`G0/0.23`) | Metric 2 via `LIB-R1` (`10.0.12.1`, `G0/0.12`); the laptop's SSH path to `TCH-R2` uses this link, so the monitor's session drops and reconnects |
| **T4** Recovery | `LIB-R1` | `192.168.20.0/24` | After `T1`: `t1-far-up.txt` pushed to `TCH-R2` first, then `LIB-R1` console: `no shutdown` on `G0/1` | Back to metric 1 via `10.0.12.2` on `TCH-R2`'s next update |
| **T5** Silent failure | `LIB-R1` | `192.168.30.0/24` | [`t5-start.txt`](../configs/push/t5-start.txt) (`passive-interface GigabitEthernet0/1`) pushed to `LAB-R3` with `--no-save` | Possibly down at 180 s, flushed at 240 s, then metric 2 via `TCH-R2` (`10.0.12.2`) on its next update (240–270 s); asymmetric routing afterwards |

---

## 6a.4 Experimental Results

### Table 6a.1 — Convergence time (router debug log)

| Test | Run 1 (s) | Run 2 (s) | Run 3 (s) | Average (s) | Min–Max (s) | Pings lost (avg) |
|---|---:|---:|---:|---:|---:|---:|
| **T1** Library–Teachers link down | 7.10 | 5.64 | 4.65 | 8.56 (4 runs; run 4: 16.85) | 4.65–16.85 | 32.0 |
| **T2** Library–Lab link down | 16.47 | 19.12 | 27.04 | 20.87 | 16.47–27.04 | 29.3 |
| **T3** Teachers–Lab link down | 9.20 | 16.93 | 11.36 | 12.50 | 9.20–16.93 | 33.3 |
| **T4** Recovery (T1 link back up) | 17.56 | 20.41 | 27.96 | 21.98 | 17.56–27.96 | 0.0 |
| **T5** Silent failure | 260.26 | 248.65 | 262.35 | 257.09 | 248.65–262.35 | 24.0 |

### Table 6a.2 — Every run, all three measurements

| Run | Debug (s) | Debug start → end (router clock) | Monitor converged (s after mark) | SSH gap (s) | Pings lost |
|---|---:|---|---:|---:|---:|
| T1-run1 | 7.104 | 16:25:28.223 → 16:25:35.327 | 5.19 ¹ | – | 42 |
| T1-run2 | 5.636 | 16:49:57.547 → 16:50:03.183 | 8.20 | – | 22 |
| T1-run3 | 4.652 | 17:03:59.243 → 17:04:03.895 | 2.84 | – | 32 |
| T1-run4 | 16.848 | 17:15:14.475 → 17:15:31.323 | 18.24 | – | 32 |
| T2-run1 | 16.468 | 17:31:25.011 → 17:31:41.479 | 21.27 | – | 19 |
| T2-run2 | 19.116 | 17:37:58.355 → 17:38:17.471 | 23.11 | – | 34 |
| T2-run3 | 27.036 | 17:43:46.803 → 17:44:13.839 | 31.31 | – | 35 |
| T3-run1 | 9.204 | 18:07:48.051 → 18:07:57.255 | 24.57 | 13.7 | 32 |
| T3-run2 | 16.928 | 18:17:55.135 → 18:18:12.063 | 31.40 | 7.7 | 45 |
| T3-run3 | 11.364 | 18:25:56.691 → 18:26:08.055 | 24.20 | 0.7 | 23 |
| T4-run1 | 17.560 | 16:58:01.743 → 16:58:19.303 | 18.23 | – | 0 |
| T4-run2 | 20.412 | 17:09:42.911 → 17:10:03.323 | 25.11 | – | 0 |
| T4-run3 | 27.956 | 17:24:09.543 → 17:24:37.499 | 29.36 | – | 0 |
| T5-run1 | 260.260 | 18:31:10.779 → 18:35:31.039 | 245.64 | – | 22 |
| T5-run2 | 248.648 | 18:54:28.303 → 18:58:36.951 | 247.98 | 9.2 | 12 |
| T5-run3 | 262.348 | 19:04:57.719 → 19:09:20.067 | 238.58 | – | 38 |

¹ From the runner's printed output; the monitor log files of T1-run1 were lost (6a.6).

### Table 6a.3 — T5: each step against RIP's timers (seconds after the last update from LAB-R3)

| Run | Possibly down (invalid, 180 s) | Flushed (240 s) | New route installed |
|---|---:|---:|---:|
| T5-run1 | 188.7 | 248.8 | 260.3 |
| T5-run2 | 182.0 | 242.1 | 248.6 |
| T5-run3 | 183.0 | 243.0 | 262.3 |

Each step lands a few seconds after its timer (IOS checks its timers periodically, not continuously), and the new route arrives with `TCH-R2`'s next periodic update after the flush.

---

## 6a.5 Charts and Figure Captions

[`scripts/visualize.py`](../scripts/visualize.py) draws the charts in `data/charts/` from the collected logs.

1. **Figure 6a.1 — `convergence_comparison.png`:** Mean RIPv2 convergence time per test with min–max error bars and each run as a point. The left panel compares all five tests against the 180 s invalid and 240 s flush timers; the right panel zooms into the link tests (`T1`–`T4`) against the 30 s update interval.
2. **Figure 6a.2 — `timeline_T5-run1_LIB-R1.png`:** `192.168.30.0/24` on `LIB-R1` during `T5`: metric 1 via `10.0.13.2`, metric 16 (possibly down) at about 205 s of observation, metric 2 via `10.0.12.2` at about 287 s. The brief flushed state was not seen by the monitor: during those seconds `LIB-R1` had no route back to the laptop, so the poll stalled (the spike in the lower panel).
3. **Figure 6a.3 — `timeline_T3-run1_TCH-R2.png`:** `192.168.30.0/24` on `TCH-R2` during `T3`: metric 1 via `10.0.23.2`, then the shaded 13.7 s SSH session gap (the laptop's path to `TCH-R2` used the cut link), then metric 2 via `10.0.12.1`.
4. **Figures 6a.4–6a.5 — `timeline_T2-run1_LAB-R3.png`, `timeline_T4-run1_LIB-R1.png`:** the same view for `T2` (measured on `LAB-R3`, no session gap) and `T4` (recovery to metric 1). There is no `T1` timeline: the chart uses run 1, whose monitor files were lost.

---

## 6a.6 Evidence

For every run the repository holds:

1. **Before/after routing snapshots:** `data/snapshots/<timestamp>_<label>-before.json` / `-after.json` and `data/routes.csv` ([`get_routes.py`](../scripts/get_routes.py)), diffed by [`compare_routes.py`](../scripts/compare_routes.py).
2. **Debug captures:** `data/debug_logs/<test>-run<n>_<router>.txt`, with the parsed events in `.csv` and metadata in `.meta.json`.
3. **Monitor logs:** `data/monitor_logs/<test>-run<n>_<router>.csv`, `_polls.csv`, `_summary.json`.
4. **Ping and traceroute photos:** `data/ping_logs/photos/<test>-run<n>_before.jpg` / `_after.jpg`.
5. **Results table:** `data/results.csv` ([`collect_results.py`](../scripts/collect_results.py)).

**Recovered data.** The laptop's `data/debug_logs/` folder was deleted during the session, after `T1`–`T4` had finished. The raw debug lines for all `T1`, `T3` and `T4` runs were recovered from the PuTTY console logs (`data/console_logs/`), because the console on the measured router printed the same debug output; all 10 recovered runs recompute to the figures the runner printed at the time. `T2`'s figures come from the runner's printed output (`data/debug_logs/runner_debug_lines_T1-T4.txt`), because the console was not on `LAB-R3`. `T5` run 1 keeps its four key debug lines. Each recovered file states its source in its header.

---

## 6a.7 Observations and Measurement Limitations

1. **The spread follows the 30 s update timer.** In `T1`–`T3` the router deletes the route at once, then waits for the neighbour's next periodic update, which comes 0–30 s later. That is why `T1` ranges from 4.65 to 16.85 s. With 3–4 runs per test, the differences between the `T1`, `T2` and `T3` averages are within this 0–30 s spread, so they say more about where each cut fell in the neighbour's update cycle than about the links themselves.
2. **Recovery is not faster than failure.** In `T4`, `LIB-R1` sent a RIP request as soon as the link came up (`T4` run 1, 16:58:06), but the better route only arrived with `TCH-R2`'s next periodic update: 17.6–28.0 s in total, with no lost pings because the 2-hop route kept working meanwhile.
3. **Ping loss measures the slower router.** A ping needs both directions; the return path depends on the far router, which only dropped its route when its end was shut a few seconds after "go", then waited for its own neighbour's update. Ping loss (22–45 lost replies) is therefore longer than the measured router's convergence. The counts may include a packet twice where ping printed both `Unreachable` and `no answer yet` for it, so treat them as approximate.
4. **One-sided failures on switched links.** A port going down on one router is invisible to the router at the other end of a VLAN link through a switch, which then has to wait for RIP's invalid timer, as in `T5`. Shutting both ends emulates a cut cable. In real networks this is the case for BFD or a faster protocol.
5. **SSH gaps.** In `T3` the monitor's SSH path to `TCH-R2` ran over the cut link (gaps of 0.7–13.7 s); the debug capture was unaffected because it was read from the router's log buffer afterwards. In `T5` run 2, `LIB-R1` briefly had no route back to the laptop between the flush and the new route (9.2 s gap).
6. **Asymmetric routing after `T5`.** The traceroute from the Library PC went through `TCH-R2` (`10.0.12.2`, `10.0.23.2`) while the replies kept `ttl=254`: `LAB-R3` still heard `LIB-R1` and kept sending its replies over the direct link.
7. **Unsynchronised clocks.** The router clocks were set to the laptop's time before testing (to within 1 s), but every convergence figure uses a single router's clock, so clock offsets do not affect it.
