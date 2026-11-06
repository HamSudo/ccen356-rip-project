"""
experiments.py - the T0 to T5 test definitions in one place.

Every value here comes from the team plan (v3), "Test plan" and "Handoff
from Mouhamed": which router is measured, which route is watched, the
metric it should end up with, and what the operator does to cause the
failure. capture_rip_debug.py, monitor_convergence.py, run_experiment.py
and collect_results.py all read this file, so a change is made once.

    from experiments import EXPERIMENTS, get_experiment
    t1 = get_experiment("T1")
    t1.router, t1.network, t1.metric   # 'LIB-R1', '192.168.20.0/24', 2

Nothing in this file talks to a router.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Experiment:
    test: str                 # 'T1'
    title: str                # short name for tables and charts
    router: str               # router whose clock/log/routing table is measured
    network: str = ""         # route that changes ('' for T0)
    metric: int = 0           # its metric once converged
    next_hop: str = ""        # its next hop once converged
    before_metric: int = 0    # its metric before the action (precondition check)
    silent_peer: str = ""     # T5 only: neighbour that stops sending updates
    duration: int = 120       # seconds to record; the lab used 120 (T1/T4), 90 (T2/T3), 420 (T5)
    pre_roll: int = 5         # seconds to record before the action
    action: tuple = ()        # what the operator does, line by line
    restore: tuple = ()       # how to undo it before the next run
    notes: tuple = field(default_factory=tuple)


EXPERIMENTS = {
    "T0": Experiment(
        test="T0", title="Baseline", router="LIB-R1",
        duration=35, pre_roll=0,
        action=("Nothing to do: all links up. Snapshot every router.",),
        notes=("Every remote LAN should be at metric 1 on every router.",),
    ),
    # All-Ethernet design (docs/Design-Change-All-Ethernet.md): each WAN link
    # runs through a switch, so one end is a physical port and the other a
    # subinterface. The measured router's end is always the physical port,
    # because only a physical port logs the %LINK line the debug parser
    # starts from. The far end is shut too, so both routers drop the link
    # like a cut cable.
    "T1": Experiment(
        test="T1", title="Library-Teachers link down", router="LIB-R1",
        network="192.168.20.0/24", metric=2, next_hop="10.0.13.2", before_metric=1,
        action=("On the LIB-R1 console, on 'go':", "  configure terminal", "  interface GigabitEthernet0/1",
                "  shutdown", "  end",
                "Right after, far end (second terminal):",
                "  python scripts/push_config.py configs/push/t1-far-down.txt TCH-R2 --no-save"),
        restore=("Run T4 now: T4 IS this restore, measured. Unmeasured restore:",
                 "  python scripts/push_config.py configs/push/t1-far-up.txt TCH-R2 --no-save",
                 "  then on LIB-R1: interface GigabitEthernet0/1 > no shutdown"),
        notes=("SSH from the LAB LAN to LIB-R1 runs over LAB-R3 G0/1, so the session stays up.",),
    ),
    "T2": Experiment(
        test="T2", title="Library-Lab link down", router="LAB-R3",
        network="192.168.10.0/24", metric=2, next_hop="10.0.23.1", before_metric=1,
        action=("On 'go', measured end (second terminal; or LAB-R3 console: interface G0/1 > shutdown):",
                "  python scripts/push_config.py configs/push/t2-measured-down.txt LAB-R3 --no-save",
                "Right after it returns, far end on the LIB-R1 CONSOLE (SSH to LIB-R1 uses this link):",
                "  configure terminal", "  interface GigabitEthernet0/0.13", "  shutdown", "  end"),
        restore=("On the LIB-R1 console: interface GigabitEthernet0/0.13 > no shutdown",
                 "Then: python scripts/push_config.py configs/push/t2-measured-up.txt LAB-R3 --no-save",
                 "Wait ~45 s: LAB-R3 back to 192.168.10.0/24 metric 1 via 10.0.13.1."),
        notes=("Measured on LAB-R3 (its end of the link is the physical port). AUTO-PC is on "
               "LAB-R3's LAN, so this SSH session stays up; the one to LIB-R1 drops until RIP "
               "converges via TCH-R2.",),
    ),
    "T3": Experiment(
        test="T3", title="Teachers-Lab link down", router="TCH-R2",
        network="192.168.30.0/24", metric=2, next_hop="10.0.12.1", before_metric=1,
        action=("On the TCH-R2 CONSOLE, on 'go':", "  configure terminal", "  interface GigabitEthernet0/1",
                "  shutdown", "  end",
                "Right after, far end (second terminal):",
                "  python scripts/push_config.py configs/push/t3-far-down.txt LAB-R3 --no-save"),
        restore=("  python scripts/push_config.py configs/push/t3-far-up.txt LAB-R3 --no-save",
                 "Then on the TCH-R2 console: interface GigabitEthernet0/1 > no shutdown",
                 "Wait ~45 s: TCH-R2 back to 192.168.30.0/24 metric 1 via 10.0.23.2."),
        notes=("A laptop on the LAB LAN reaches TCH-R2 over LAB-R3 G0/0.23 -> TCH-R2 G0/1, the "
               "link being shut: the SSH session to TCH-R2 drops until RIP converges. The monitor "
               "reconnects and logs the gap; the debug capture is read back from the log buffer.",),
    ),
    "T4": Experiment(
        test="T4", title="Recovery (T1 link back up)", router="LIB-R1",
        network="192.168.20.0/24", metric=1, next_hop="10.0.12.2", before_metric=2,
        action=("Precondition: the T1 link is DOWN and has converged.",
                "BEFORE 'go', far end first (second terminal):",
                "  python scripts/push_config.py configs/push/t1-far-up.txt TCH-R2 --no-save",
                "Then on the LIB-R1 console, on 'go':", "  configure terminal",
                "  interface GigabitEthernet0/1", "  no shutdown", "  end"),
        restore=("Nothing: the network is back to normal.",),
        notes=("Run it straight after each T1 run: T1-run1, T4-run1, T1-run2, T4-run2, ...",),
    ),
    "T5": Experiment(
        test="T5", title="Silent failure (passive G0/1)", router="LIB-R1",
        network="192.168.30.0/24", metric=2, next_hop="10.0.12.2", before_metric=1,
        silent_peer="10.0.13.2", duration=420, pre_roll=35,
        action=("Push the T5 change to LAB-R3 (does NOT save it):",
                "  python scripts/push_config.py configs/push/t5-start.txt LAB-R3 --no-save"),
        restore=("  python scripts/push_config.py configs/push/t5-stop.txt LAB-R3 --no-save",
                 "Then wait ~60 s and check LIB-R1 is back to metric 1 via 10.0.13.2 (G0/0.13)."),
        notes=("Pre-roll is 35 s so at least one update from LAB-R3 (10.0.13.2) is in the log: "
               "parse_rip_debug.py measures T5 from the last update heard from it.",
               "Plan expects about 240-270 s (flush timer + TCH-R2's next update). Some IOS "
               "versions may install the metric-2 route earlier, after the 180 s invalid timer; "
               "record what actually happens.",),
    ),
}

FAILURE_TESTS = ("T1", "T2", "T3", "T4", "T5")


def get_experiment(test):
    """Return the Experiment for 'T1' (case-insensitive), or raise ValueError."""
    key = str(test).strip().upper()
    if key not in EXPERIMENTS:
        raise ValueError(f"unknown test {test!r}; expected one of {', '.join(EXPERIMENTS)}")
    return EXPERIMENTS[key]


def run_label(test, run):
    """'T1', 1 -> 'T1-run1', the naming the plan uses for captures."""
    return f"{get_experiment(test).test}-run{int(run)}"
