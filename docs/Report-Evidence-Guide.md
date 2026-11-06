# Which evidence goes in the report

For the whole team, for writing the progress report and the final report. Lab session: 6 Nov 2026.

## The rule

Put **one representative example of each kind of evidence** in the report and keep everything else in the repository. The graders will not read 16 runs of near-identical photos; they will read one clear example and the summary table.

- The report shows each kind of evidence once: a routing table, a switch check, a reroute, a timeline, the results.
- The repository holds all of it: debug captures, monitor logs, before/after snapshots, 32 photos, 6 device screenshots, console logs.
- The report says once, near the start of the results, where the full evidence is (wording below).

## Progress report: four items

The progress report needs only enough to show the network works and the tests produced results. Point to the final report and the repository for the rest.

1. **Topology diagram** of the all-Ethernet design (3 routers, 3 switches, VLANs 12/13/23 as the WAN links). To be drawn from [`Design-Change-All-Ethernet.md`](Design-Change-All-Ethernet.md).
2. **One baseline routing table:** `data/verification/screenshots/LIB-R1_show-commands.png` (`show ip route rip` with both remote LANs at [120/1]).
3. **The results table** (last section of this file), as a table, not an image.
4. **The convergence comparison chart:** `data/charts/convergence_comparison.png`.

## Final report: about 9 figures

Each figure earns its place by showing something no other figure shows.

| Section | Figure | File | Why this one |
|---|---|---|---|
| 2 Network design | Topology diagram | to draw (see the design-change doc) | Shows the triangle and the VLAN trick at a glance |
| 2 Network design | One rack/cabling photo | team phone, then `topology/` | Proves the physical build |
| 4 Verification | `show ip route rip` + `show ip protocols`, LIB-R1 | `data/verification/screenshots/LIB-R1_show-commands.png` | Baseline routes and RIP timers (30/180/180/240); give TCH-R2 and LAB-R3 as a small table instead |
| 4 Verification | SW-LIB VLANs, trunk and CDP neighbours | `data/verification/screenshots/SW-LIB_show-commands.png` | Proves the VLAN design and the cross-room cabling |
| 6a Results | Results table | `data/results.csv` | The main result, as a table |
| 6a Results | Convergence comparison chart | `data/charts/convergence_comparison.png` | Average and min–max per test |
| 6a Results | T1 run 1 traceroute, before and after | `data/ping_logs/photos/T1-run1_before.jpg`, `T1-run1_after.jpg` | Shows the reroute (10.0.12.2 → 10.0.13.2, 10.0.23.1) |
| 6a / 6b | T5 timeline chart | `data/charts/timeline_T5-run1_LIB-R1.png` | Shows the 180 s invalid and 240 s flush timers |
| 6b Analysis | T5 run 1 after photo | `data/ping_logs/photos/T5-run1_after.jpg` | Detour traceroute but `ttl=254`: asymmetric routing in one image |

Not in the list on purpose: photos for runs 2–4, screenshots of the other routers and switches, and anything that repeats a figure above.

## Text excerpts instead of photos

Where the point is a few log lines, copy them from the saved logs into a monospace listing. It reads better than a phone photo and can be quoted.

**T1 run 1, LIB-R1** (`data/debug_logs/T1-run1_LIB-R1.txt`): the route is deleted the moment `shutdown` is entered, the `%LINK` message comes 2 s later, and the new route arrives with LAB-R3's next update, 7.104 s after the delete.

```
Nov  6 16:25:28.223: RT: del 192.168.20.0 via 10.0.12.2, rip metric [120/1]
Nov  6 16:25:30.219: %LINK-5-CHANGED: Interface GigabitEthernet0/1, changed state to administratively down
Nov  6 16:25:35.327: RT: add 192.168.20.0/24 via 10.0.13.2, rip metric [120/2]
```

**T5 run 1, LIB-R1** (`data/debug_logs/T5-run1_LIB-R1.txt`): each step lines up with a RIP timer, 260.26 s in total.

```
Nov  6 18:31:10.779: RIP: received v2 update from 10.0.13.2 on GigabitEthernet0/0.13    (last update, t = 0)
Nov  6 18:34:19.499: RT: delete route to 192.168.30.0 via 10.0.13.2, rip metric [120/1]  (invalid, t = 188.7 s)
Nov  6 18:35:19.535: RT: delete network route to 192.168.30.0/24                          (flush, t = 248.8 s)
Nov  6 18:35:31.039: RT: add 192.168.30.0/24 via 10.0.12.2, rip metric [120/2]            (new route, t = 260.3 s)
```

**Count to infinity, TCH-R2** (`data/verification/incident_TCH-R2_G0-0_down_count-to-infinity.txt`): after a loose cable cut TCH-R2's LAN, it learned a route to its own LAN back from LAB-R3. Use it in section 7 (Limitations of RIP).

```
R     192.168.20.0/24 [120/3] via 10.0.23.2, 00:00:16, GigabitEthernet0/1    <- its own LAN, via LAB-R3
```

## What stays in the repository only

Everything below backs the report but does not go in it. One sentence in the report points to it.

| Evidence | Location | Count |
|---|---|---|
| Before/after traceroute and ping photos, all runs | `data/ping_logs/photos/` | 32 |
| Debug captures (raw lines, parsed CSV, metadata) | `data/debug_logs/` | 16 runs |
| Route monitor logs (1 s polling) | `data/monitor_logs/` | 16 runs |
| Before/after routing snapshots | `data/snapshots/`, `data/routes.csv` | 37 files |
| Device screenshots (other 5 devices) | `data/verification/screenshots/` | 5 |
| Verification outputs and RIP push outputs | `data/verification/` | 3 + 3 |
| Running-config exports | `configs/exports/` | 6 |
| Console session logs | `data/console_logs/` | 20 |

**Sentence for the report** (start of section 6a, and once in the progress report):

> Each test was run three times (T1 four times). The report shows one representative run per test; all raw evidence for every run (debug captures, 1-second route monitor logs, before/after routing snapshots and photos of every ping and traceroute) is in the project repository under `data/`.

In the appendix, a short index table (test, run, file names) is enough; do not paste the files.

## Results at a glance

Link failures (T1–T3) converged in 5–27 s; the silent failure (T5) took 257 s on average, set by RIP's 180 s invalid and 240 s flush timers. Convergence is measured on the router's own clock, from the route delete (or, for T5, the last update heard) to the new route's install.

| Test | Run 1 (s) | Run 2 (s) | Run 3 (s) | Average (s) | Pings lost (avg) |
|---|---|---|---|---|---|
| T1 Library–Teachers link down | 7.10 | 5.64 | 4.65 | 8.56 (4 runs; run 4: 16.85) | 32 |
| T2 Library–Lab link down | 16.47 | 19.12 | 27.04 | 20.87 | 29 |
| T3 Teachers–Lab link down | 9.20 | 16.93 | 11.36 | 12.50 | 33 |
| T4 Recovery (T1 link back up) | 17.56 | 20.41 | 27.96 | 21.98 | 0 |
| T5 Silent failure (no updates) | 260.26 | 248.65 | 262.35 | 257.09 | 24 |

Ping counts come from `grep -c` on the ping output and may count a packet twice where ping printed both `Unreachable` and `no answer yet` for it; treat them as approximate.

**Notes to state openly in the report** (one or two sentences in section 6a):

- The laptop's `data/debug_logs/` folder was deleted mid-session. Raw debug lines for T1, T3 and T4 were recovered from the console session logs (all 10 runs recompute to the same figures); T2's figures come from the test runner's printed output; T5 run 1 keeps its four key lines.
- T1 was run four times: the extra cut put the link down again so the last T4 run could start.
- The separate 40 s "normal RIP updates" captures were lost with that folder; every test run's debug capture also records the periodic updates sent and received, so those cover the brief's "capture RIP updates" item.
