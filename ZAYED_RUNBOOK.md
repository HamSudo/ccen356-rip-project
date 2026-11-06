# Zayed's Runbook: Measurement Commands and Demo Steps (CCEN 356 Project 1)

The commands that collect every measurement, as run in the lab on 6 Nov 2026 on the all-Ethernet build ([`docs/Design-Change-All-Ethernet.md`](docs/Design-Change-All-Ethernet.md)). Who presses what, and when, is in [`docs/Lab-Day-Test-Plan.md`](docs/Lab-Day-Test-Plan.md); this file is the command reference.

---

## 1. Before you start

- The script machine sits on SW-LAB Fa0/5 as AUTO-PC: `192.168.30.20/24`, no default gateway, with routes to `192.168.10.0/24` and `192.168.20.0/24` via `192.168.30.1` (so internet stays on Wi-Fi).
- One console per router you will shut by hand: LIB-R1 (T1/T4 measured end, T2 far end) and TCH-R2 (T3 measured end).
- Install and test (from the repository root). `paramiko` is pinned to 3.5.1, because the lab's IOS 15.0 only offers SHA-1 key exchange:

```powershell
pip install -r requirements.txt
python -m pytest
```

Credentials default to the lab configs (`admin` / `Admin@123`, enable secret `class123`); override with `$env:RIP_USER`, `$env:RIP_PASS`, `$env:RIP_SECRET`.

## 2. One-time router preparation

```powershell
python scripts/connect_test.py                                   # 3/3 routers over SSH
python scripts/push_config.py configs/push/timestamps.txt all    # ms timestamps + 64 KB debug buffer
foreach ($r in "LIB-R1","TCH-R2","LAB-R3") {
    python scripts/push_config.py configs/push/rip-$r.txt $r     # RIP pushed from Python (evidence)
    python scripts/capture_rip_debug.py $r --label T0-updates --duration 40   # normal RIP updates
}
python scripts/run_experiment.py T0                              # baseline snapshot
```

## 3. The tests

Every link test shuts **both ends** of the link (the WAN links run through switches, so a router does not see the far end go down). The measured end is always a physical `G0/1`; the far end is a subinterface. `run_experiment.py` refuses to reuse a run number whose files exist; add `--overwrite` only to redo a run on purpose.

| Test | Command (Window A) | On "go" (measured end) | Right after (far end) | Restore |
|---|---|---|---|---|
| T1 | `python scripts/run_experiment.py T1 --run N --duration 120` | LIB-R1 console: `interface GigabitEthernet0/1` → `shutdown` | `python scripts/push_config.py configs/push/t1-far-down.txt TCH-R2 --no-save` | T4 is the restore |
| T4 | `python scripts/run_experiment.py T4 --run N --duration 120` | LIB-R1 console: `no shutdown` on `G0/1` | **before** "go": `python scripts/push_config.py configs/push/t1-far-up.txt TCH-R2 --no-save` | none |
| T2 | `python scripts/run_experiment.py T2 --run N --duration 90` | `python scripts/push_config.py configs/push/t2-measured-down.txt LAB-R3 --no-save` | LIB-R1 console: `interface GigabitEthernet0/0.13` → `shutdown` | LIB-R1 console `no shutdown` on `G0/0.13`, then `t2-measured-up.txt` to LAB-R3 |
| T3 | `python scripts/run_experiment.py T3 --run N --duration 90` | TCH-R2 console: `interface GigabitEthernet0/1` → `shutdown` | `python scripts/push_config.py configs/push/t3-far-down.txt LAB-R3 --no-save` | `t3-far-up.txt` to LAB-R3, then TCH-R2 console `no shutdown` on `G0/1` |
| T5 | `python scripts/run_experiment.py T5 --run N --duration 420` | at ~35 s: `python scripts/push_config.py configs/push/t5-start.txt LAB-R3 --no-save` | none | `python scripts/push_config.py configs/push/t5-stop.txt LAB-R3 --no-save`, wait 60 s |

Order used: T0; T1/T4 in pairs (T1-run1, T4-run1, T1-run2, ...; an extra T1-run4 put the link down for T4-run3); T2 ×3; T3 ×3; T5 ×3. Wait about 45 s after each restore; the runner's precondition check refuses to measure from the wrong starting state.

Ping during each run from a lab PC (Library PC; Teachers' PC for T3), 1 s timeout:

```bash
ping -O -W 1 192.168.20.1 | tee T1-run1_ping.txt     # 192.168.30.1 for T2, T3, T5
grep -cE "no answer yet|Unreachable" T1-run1_ping.txt
traceroute 192.168.20.1                              # before and after; photo of both
```

## 4. Results and charts

```powershell
python scripts/collect_results.py --ping T1-run1=42 T1-run2=22 ...   # data/results.csv + Markdown table
python scripts/visualize.py                                          # data/charts/
```

`collect_results.py` picks up extra runs (T1-run4) and, where a raw capture was lost, the runner's printed figures in `data/debug_logs/runner_debug_lines_T1-T4.txt`. Results and their caveats are written up in [`docs/Section-6a-Link-Failure-Tests-and-Results.md`](docs/Section-6a-Link-Failure-Tests-and-Results.md).

## 5. Single tools (for the demo or a re-check)

```powershell
python scripts/monitor_convergence.py LIB-R1 --network 192.168.20.0/24 --expect-metric 2 --duration 90 --mark-on-enter
python scripts/parse_rip_debug.py data/debug_logs/T1-run1_LIB-R1.txt --network 192.168.20.0/24 --metric 2
python scripts/parse_rip_debug.py data/debug_logs/T5-run1_LIB-R1.txt --network 192.168.30.0/24 --metric 2 --silent-peer 10.0.13.2
python scripts/compare_routes.py T1-run2-before T1-run2-after
```

## 6. Demo steps (Zayed)

1. **Live T1:** start the monitor on LIB-R1 (first command in section 5). A teammate shuts `GigabitEthernet0/1` on the LIB-R1 console and the far end is pushed to TCH-R2 (`t1-far-down.txt`); press Enter to mark it. Point out `route_lost`, then `route_restored ... via 10.0.13.2 ... m2` when LAB-R3's next update arrives.
2. **Restore and charts:** `t1-far-up.txt` to TCH-R2, then `no shutdown` on LIB-R1 `G0/1`. Open `data/charts/convergence_comparison.png` and `data/charts/timeline_T5-run1_LIB-R1.png` to show link failures (5–28 s) against the silent failure (about 257 s).

## 7. Troubleshooting

- **Debug left on after a failed run:** `undebug all` on that router's console, or `python scripts/capture_rip_debug.py <ROUTER> --duration 1`.
- **`No convergence event pair found`:** check the shutdown was on the measured router's physical `G0/1` (a subinterface shutdown logs no `%LINK` line), and for T5 that at least one update from `10.0.13.2` was logged before `t5-start.txt`.
- **`no acceptable kex algorithm` from netmiko:** paramiko is newer than 3.5.1; `pip install "paramiko==3.5.1"`.
