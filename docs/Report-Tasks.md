# Report Tasks: Who Writes What

The remaining report work after the lab session on 6 Nov 2026. Every file path is relative to the repository root. Which figures go in the report is decided in [`Report-Evidence-Guide.md`](Report-Evidence-Guide.md); the design itself is in [`Design-Change-All-Ethernet.md`](Design-Change-All-Ethernet.md).

The build is all-Ethernet: the lab's 2901s have no serial modules, and the brief requires serial links only "where applicable". The team plan's versions of these sections describe the serial design and are to be updated, not copied.

The demo is planned separately and is not covered here.

---

## Saif: topology diagram, sections 2–4, Appendix A (configs)

1. **Topology diagram:** done, saved as `topology/topology.png`. One fix remains: the legend is to list the WAN line colours per link (orange VLAN 12, purple VLAN 13, teal VLAN 23), not orange only. `school-rip.pkt` is to be updated only if it is still to be submitted.
2. **Section 2, Network design:**
   - The diagram is to be included.
   - An IP plan table is to be included: LANs, WAN /30s, gateways .1, switch management .2.
   - A cabling table is to be included.
   - One rack photo is to be included from `topology/photos/`. `routers_rear_and_switches.jpg` is recommended.
   - One sentence is to be added on the absence of serial links: the 2901s have no serial modules, and the brief requires serial only "where applicable".
3. **Section 3, RIP configuration:**
   - Each router's RIP block is to be shown: `version 2`, the `network` statements, `no auto-summary`, and `passive-interface` on the LAN subinterfaces.
   - A short excerpt of the subinterface and trunk config is to be added.
   - These are to be taken from `configs/exports/`, not `configs/source/`.
   - The Python push is to be cited, with `data/verification/push_rip_*.txt` as evidence.
4. **Section 4, Verification:**
   - `data/verification/screenshots/LIB-R1_show-commands.png` is to be included for the routes and the RIP timers.
   - `data/verification/screenshots/SW-LIB_show-commands.png` is to be included for the VLANs, the trunk and CDP.
   - The TCH-R2 and LAB-R3 routes are to be given as one small table, from `data/verification/TCH-R2.txt` and `LAB-R3.txt`.
   - A few `debug ip rip` lines are to be quoted from `data/debug_logs/T0-updates_*`.
   - A short excerpt of `data/snapshots/20261106T161729_T0-baseline.json` is to be shown as the routing table retrieved by Python.
5. **Appendix A, configs:** the six files in `configs/exports/` are to be included, or a repo link given if the appendix is too long.

---

## Zayed: section 6a review, Appendix A (script listings), chart check

1. **Section 6a review:**
   - `docs/Section-6a-Link-Failure-Tests-and-Results.md` is to be reviewed.
   - Its numbers are to be checked against `data/results.csv`.
   - The section is to be moved into the report template.
2. **Appendix A, script listings:** listings are to be provided for `capture_rip_debug.py`, `monitor_convergence.py`, `parse_rip_debug.py`, `run_experiment.py`, `collect_results.py` and `visualize.py`. Excerpts or a repo link are to be used rather than full dumps.
3. **Chart check:**
   - The five charts in `data/charts/` are to be checked. They come from the measured results, not simulated ones.
   - The selection given in `docs/Report-Evidence-Guide.md` is to be followed.
   - No T1 timeline exists, because that monitor log was lost, so the T2–T5 timelines are to be used.

---

## Abdulrahman: sections 1, 6b, 7, 8

1. **Section 1, Introduction and objectives:** the design change is to be mentioned: no serial modules, so all links are Ethernet (see `docs/Design-Change-All-Ethernet.md`).
2. **Section 6b, Convergence analysis:** the numbers are to be taken from Section 6a, not from the team plan's predictions. These points are to be covered:
   - **T1–T3 averaged 8.6, 20.9 and 12.5 s.** This is to be explained by the 0–30 s wait for the neighbour's next update.
   - **T4 averaged 22.0 s with 0 pings lost.** The old path kept forwarding until the better route returned.
   - **T5 averaged 257 s.** This is to be compared with the expected 240 s flush plus up to 30 s for the next update.
   - **The T5 timer steps** are to be noted: invalid at about 182–189 s, flush at about 242–249 s, so hold-down was cut short by the flush.
   - **Disagreement between the debug, monitor and ping methods** is to be explained, using 6a §6a.7.
   - **Asymmetric routing after T5** is to be shown with `data/ping_logs/photos/T5-run1_after.jpg`: a detour traceroute, but `ttl=254`.
3. **Section 7, Limitations of RIP:**
   - The team plan's "Ethernet vs 64 kbps serial" bullet is to be replaced with a theoretical hop-count/bandwidth example, since the build has no serial links.
   - The count-to-infinity incident is to be used as the real example. The file is `data/verification/incident_TCH-R2_G0-0_down_count-to-infinity.txt`: TCH-R2 learned its own LAN back from LAB-R3 at [120/3].
   - Split horizon and the "backup route advertised but ignored" observation from 6a are to be included.
   - The section is to close with a one-paragraph comparison with OSPF.
4. **Section 8, Conclusion:** to be written last, from the final results.
