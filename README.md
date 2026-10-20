# ccen356-rip-project

CCEN 356 Course Project 1: RIPv2 dynamic routing in a three-room school network (Library, Teachers' room, Laboratory) on Cisco 2901 routers, with Python (netmiko) automation for configuration, routing-table snapshots and convergence measurement.

## Layout

```
configs/source/     paste-in configs for the 3 routers and 3 switches (Saif)
configs/exports/    show running-config exports from the built devices (Saif)
configs/push/       config snippets for push_config.py (RIP block, timestamps, T5)
topology/           school-rip.pkt, topology.png (Saif)
scripts/            inventory.py, connect_test.py, push_config.py,
                    get_routes.py, compare_routes.py, parse_rip_debug.py (Mouhamed)
                    capture_rip_debug.py, monitor_convergence.py, visualize.py (Zayed)
tests/              parser tests, run against the expected tables in Saif's doc
data/snapshots/     JSON routing-table snapshots, one per router set per label
data/routes.csv     every snapshot, one row per route
data/debug_logs/    raw debug ip rip captures
data/monitor_logs/  monitor_convergence.py CSV logs
data/charts/        visualize.py output
docs/               final report PDF
```

## Setup

Python 3.10+, run from AUTO-PC (192.168.30.20) or any laptop that can reach the routers.

```
pip install -r requirements.txt
```

The scripts log in with the credentials from Saif's configs, so nothing needs setting. If the lab routers use different credentials, override them with environment variables instead of editing the code:

| Variable | Default |
|---|---|
| `RIP_USER` | `admin` |
| `RIP_PASS` | `Admin@123` |
| `RIP_SECRET` | `class123` |

```powershell
$env:RIP_PASS = "other-password"   # PowerShell, lasts for this terminal only
```

## Running the scripts

Run everything from the repo root.

```
python scripts/connect_test.py                        # can we SSH into all 3 routers?
python scripts/get_routes.py T0-baseline              # snapshot -> data/snapshots/*.json + data/routes.csv
python scripts/compare_routes.py T1-before T1-after   # what changed between two snapshots (labels or file paths)
python scripts/push_config.py configs/push/timestamps.txt all
python scripts/push_config.py configs/push/t5-start.txt LAB-R3 --no-save
python -m pytest                                      # parser tests, no routers needed
```

`configs/push/` holds the files `push_config.py` applies: the RIP block for each router, the timestamp lines to push before testing, and the T5 start/stop changes. They contain config-mode lines only (no `configure terminal` or `end`).
