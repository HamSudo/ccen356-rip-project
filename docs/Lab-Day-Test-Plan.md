# Lab Day Test Plan: build, verify and run T0 to T5 on the physical 2901s

This plan is for the whole team on lab day. It goes from "devices just powered on" to "results committed", one small step at a time. Each step says what to type, what you should see, and what to do if you don't.

[`ZAYED_RUNBOOK.md`](../ZAYED_RUNBOOK.md) explains the measurement scripts in more depth. Saif's [Part 1 design doc](Part1-Network-Design-and-RIP-Configuration.pdf) has the IP plan and the expected routing tables.

**Hardware:** 3 × Cisco 2901 routers (onboard G0/0 and G0/1 only, no serial modules), 3 × Cisco Catalyst 3560-8PC switches (Fa0/1 to Fa0/8 used; their one Gi0/1 uplink is not needed), the lab PCs, and Mouhamed's laptop for the scripts.

**This plan uses the all-Ethernet design** in [`Design-Change-All-Ethernet.md`](Design-Change-All-Ethernet.md). The lab routers have no HWIC-2T, so each router's G0/0 is a VLAN trunk (LAN + one WAN link) and G0/1 goes to the next room's switch. Read its "What changes in the tests" section before the session.

**Time:** about **3 hours** in total.

| Phase | What | Time |
|---|---|---|
| A | Hardware check and wipe | 20 min |
| B | Cabling | 15 min |
| C | Paste the configs | 25 min |
| D | Verify the network (go / no-go) | 15 min |
| E | Laptop setup | 10 min |
| F | Router preparation from Python | 15 min |
| G | Tests T0 to T5 | 75 min |
| H | Collect, commit, clean up | 10 min |

Everything in the report and the repo must come from the real routers. The files in `data/simulated/` and the `SIMULATED_*.png` charts only tested the scripts; none of them go in the report.

---

## Roles

| Person | Job |
|---|---|
| Saif | Builds and configures the devices (phases A to D); during the tests, types the measured-end `shutdown` / `no shutdown` on the console (LIB-R1 for T1/T4, LAB-R3 for T2, TCH-R2 for T3) |
| Zayed | Runs `run_experiment.py` on the laptop and presses **Enter** at each failure |
| Mouhamed | Laptop setup (phase E); far-end shutdowns: `push_config.py` in a second terminal for T1, T3, T4 and T5, and the LIB-R1 console for T2; fixes script problems |
| Abdulrahman | Runs the ping on every run (Library PC; Teachers' PC for T3) and writes the lost count on the results sheet; takes the photos |

---

## What we learned from earlier labs (Expts 2, 4 and 5: same lab, same routers)

- **The lab PCs run Ubuntu** (Dell OptiPlex 5490 AIO, user `dslab`, wired NIC `eno1`). The password is `P@ssword`. Open a console with `sudo screen /dev/ttyUSB0 9600`. To leave `screen`, press **Ctrl+A**, then **K**, then **y**. Wireshark is installed; capture on `eno1`.
- **Show commands don't work in config mode.** In Expt 4, `show ip nat translations` typed at `Router(config)#` gave `% Invalid input`. Either `end` first, or prefix the command with `do`, for example `do show ip route rip`.
- **TTL tells you the path, for free.** In Expt 4, a router two hops away answered with `ttl=254`. A router replies with TTL 255, and each router on the way back takes off 1. So when the Library PC pings 192.168.20.1, `ttl=254` means the direct link and `ttl=253` means the detour through the third router. Section G4 uses this.
- **Expect switch noise in Wireshark.** Expt 4 captures were full of `LOOP` and `CDP` frames from the Cisco switch. Use the display filter `icmp` (or `rip` for routing updates).
- **The routers and switches may still hold other groups' configs.** Wipe them first (steps A4 and A5).
- **The 2901s have only G0/0 and G0/1, with no serial modules** (checked on LIB-R1 on 5 Nov). Hence the all-Ethernet VLAN design.
- **Shutting a subinterface logs no `%LINK` line** (also tested on LIB-R1). So in every test, the measured router's end of the link is a physical G0/1 port.
- **The lab PCs may still have static IPs from Expt 5** (172.168.x.x). Switch them back to DHCP (step D4).
- **These routers run the default RIP timers.** Expt 5's `show ip protocols` showed: update 30, invalid 180, hold down 180, flushed 240.
- **Our route parser already handles real output from these routers.** We tested `get_routes.parse_routes` on the Expt 5 `show ip route rip` output, including the variably-subnetted header and the equal-cost second-path lines.
- **Reference value:** Expt 5 measured RIP convergence at **11.28 s** (ping + Wireshark, different topology). Our T1 to T3 results should land in the same 0 to 30 s range. Abdulrahman can cite this in 6b.

---

## Phase A: Hardware check and wipe (20 min, Saif)

### A1. Label the devices

1. Put tape labels on the routers: **LIB-R1**, **TCH-R2**, **LAB-R3**.
2. Put tape labels on the switches: **SW-LIB**, **SW-TCH**, **SW-LAB**.
3. Place each switch next to its router.

### A2. Count cables and consoles

1. You need **9 straight-through Ethernet cables** (see phase B).
2. You need **one console cable per router, plugged in for the whole session**, because the tests need two consoles at once:

   | Router | Console on | Used for |
   |---|---|---|
   | LIB-R1 | Mouhamed's laptop (USB console, COM7 in PuTTY) | T1/T4 measured end, T2 far end |
   | TCH-R2 | a lab PC (`sudo screen /dev/ttyUSB0 9600`) | T3 measured end |
   | LAB-R3 | a lab PC | T2 measured end |

   The PC that runs the Library ping can also hold a console. Use two terminal windows.

### A3. Open a console to a device

Do this for each of the 6 devices, one at a time.

**From an Ubuntu lab PC:**
1. Plug the console cable into the device's **CONSOLE** port (light blue cable) and into the PC's USB port.
2. Open a terminal and type:
   ```
   sudo screen /dev/ttyUSB0 9600
   ```
3. Type the password `P@ssword` if asked. Press **Enter** a few times until you see a prompt.

**From Mouhamed's Windows laptop (already set up):**
1. Plug the console cable into the router's CONSOLE port and the laptop's USB port. It shows up as **USB-SERIAL CH340 (COM7)** in Device Manager → Ports (COM & LPT).
2. Open **PuTTY**, click the saved session **`LIB-R1-console`**, then click **Load** → **Open**. It's preset to COM7, 9600 baud, 8 data bits, no parity, 1 stop bit, no flow control, with 20,000 lines of scrollback.
3. Press **Enter** a few times. You should see `Router>` (or `LIB-R1>` once configured).
4. Everything shown in the window is also saved to `data/console_logs/console-<date>-<time>.log`, which is useful evidence and a backup of what was pasted.

If the cable is plugged into a different USB port and Windows gives it another COM number, change **Serial line** in the session and click **Save**. Only one program can use COM7 at a time, so close PuTTY before any script uses the console.

**From another Windows machine:** install PuTTY, find the COM number in Device Manager, then in PuTTY set **Connection type: Serial**, **Serial line: COMx**, **Speed: 9600** and click **Open**.

If you see `Would you like to enter the initial configuration dialog? [yes/no]:`, type `no` and press Enter.

### A4. Wipe each router

On the console, type:

```
enable
erase startup-config
```
Press **Enter** to confirm. Then:
```
reload
```
- If it asks `System configuration has been modified. Save? [yes/no]:`, type `no`.
- At `Proceed with reload? [confirm]`, press **Enter**.

The router takes about 2 minutes to reboot. When it asks about the initial configuration dialog, type `no`. You should end at a plain `Router>` prompt.

### A5. Wipe each switch

```
enable
erase startup-config
```
Press **Enter** to confirm. Then:
```
delete flash:vlan.dat
```
Press **Enter** twice to confirm. If it says the file doesn't exist, that's fine. Then:
```
reload
```
Answer `no` to "Save?" and press **Enter** to confirm. You should end at a `Switch>` prompt.

> **If a device asks for a password you don't know** (left by another group), ask the lab technician to do a password recovery. Don't guess.

---

## Phase B: Cabling (15 min, Saif)

All cables are **straight-through** Ethernet. Cabling with the power on is fine.

The rule to remember: **each router's G0/0 goes to its own switch's Fa0/7, and each router's G0/1 goes to the *next* room's switch, Fa0/8** (Library → Teachers → Lab → Library).

### B1. Router links

| # | From | To | What it carries |
|---|---|---|---|
| 1 | LIB-R1 **G0/0** | SW-LIB **Fa0/7** | Trunk: Library LAN (VLAN 10) + WAN to LAB-R3 (VLAN 13) |
| 2 | TCH-R2 **G0/0** | SW-TCH **Fa0/7** | Trunk: Teachers' LAN (VLAN 20) + WAN to LIB-R1 (VLAN 12) |
| 3 | LAB-R3 **G0/0** | SW-LAB **Fa0/7** | Trunk: Lab LAN (VLAN 30) + WAN to TCH-R2 (VLAN 23) |
| 4 | LIB-R1 **G0/1** | **SW-TCH Fa0/8** | WAN Library–Teachers (VLAN 12) |
| 5 | TCH-R2 **G0/1** | **SW-LAB Fa0/8** | WAN Teachers–Lab (VLAN 23) |
| 6 | LAB-R3 **G0/1** | **SW-LIB Fa0/8** | WAN Library–Lab (VLAN 13) |

Do **not** connect the switches to each other. Each WAN link lives on one switch only.

### B2. End devices

| # | Device | To | Role |
|---|---|---|---|
| 7 | Library PC (Ubuntu) | SW-LIB **Fa0/1** | Ping source for T1, T2, T4, T5 |
| 8 | Teachers' PC (Ubuntu) | SW-TCH **Fa0/1** | Ping source for T3; cross-room check |
| 9 | AUTO-PC (the machine running the scripts) | SW-LAB **Fa0/5** | Runs all the Python scripts at 192.168.30.20 |

Any other PC can go in **Fa0/1 to Fa0/6** (keep Fa0/5 on SW-LAB free for AUTO-PC). **Never plug a PC into Fa0/7 or Fa0/8**: those are the router ports.

### B3. Photos

1. Take photos of the rack: one wide shot, plus close-ups showing which cable goes into which port. The G0/1 → Fa0/8 cables crossing between rooms are the important ones.
2. Abdulrahman keeps them for `topology/` and the topology section of the report.

---

## Phase C: Paste the configs (25 min, Saif)

The configs are in [`configs/source/`](../configs/source/). Open each file on the laptop and copy from the line `enable` to the end. The `!` lines are comments, so it is safe to paste them too.

### C1. How to paste safely at 9600 baud

The console is slow. If you paste a whole file at once, characters can be dropped. Paste **one block at a time**, using the `! ----------` comment lines as the breaks. After each block:
1. Wait until the prompt comes back.
2. Scroll up and check for `% Invalid input`. If you see one, retype that line by hand.

In PuTTY, right-click pastes. In `screen`, use **Ctrl+Shift+V**.

### C2. Switches first

The switch VLANs must exist before the router trunks can carry traffic.

1. **SW-LIB** ← [`configs/source/SW-LIB.txt`](../configs/source/SW-LIB.txt)
2. **SW-TCH** ← [`configs/source/SW-TCH.txt`](../configs/source/SW-TCH.txt)
3. **SW-LAB** ← [`configs/source/SW-LAB.txt`](../configs/source/SW-LAB.txt)

`spanning-tree portfast` prints a warning about connecting hosts. That's expected; it's needed so ports come up without a 30 s delay.

### C3. Routers

4. **LIB-R1** ← [`configs/source/LIB-R1.txt`](../configs/source/LIB-R1.txt)
5. **TCH-R2** ← [`configs/source/TCH-R2.txt`](../configs/source/TCH-R2.txt)
6. **LAB-R3** ← [`configs/source/LAB-R3.txt`](../configs/source/LAB-R3.txt)

What to expect while pasting:
- The prompt changes from `Router(config)#` to `LIB-R1(config)#` once the `hostname` line runs.
- `interface GigabitEthernet0/0.10` puts you at a `(config-subif)#` prompt. That's a subinterface, and it is normal.
- `crypto key generate rsa ... modulus 1024` takes a few seconds and prints `[OK]`. If it asks `How many bits in the modulus`, type `1024`.
- The last line is `write memory`, which prints `[OK]`.
- After the paste, logging in again asks for the console password `cisco`, and `enable` asks for `class123`.

### C4. Quick check on each device

```
show running-config | include hostname
```
It should print the right name, for example `hostname LIB-R1`.

---

## Phase D: Verify the network: go / no-go (15 min, Saif)

**All five checks must pass before phase F.** Wait about **60 s** after the last router config so RIP can exchange updates.

### D1. Switch VLANs and trunks

On each switch:
```
show vlan brief
show interfaces trunk
```

| Switch | `show vlan brief` | `show interfaces trunk` |
|---|---|---|
| SW-LIB | VLAN 10 has Fa0/1–6; VLAN 13 has Fa0/8 | Fa0/7 trunking, VLANs allowed **10,13** |
| SW-TCH | VLAN 20 has Fa0/1–6; VLAN 12 has Fa0/8 | Fa0/7 trunking, VLANs allowed **12,20** |
| SW-LAB | VLAN 30 has Fa0/1–6; VLAN 23 has Fa0/8 | Fa0/7 trunking, VLANs allowed **23,30** |

If Fa0/7 is missing from `show interfaces trunk`, the cable to the router is out or the router's G0/0 is shut.

### D2. Every router interface is up

On each router:
```
show ip interface brief
```
All 5 lines must be `up` / `up`: G0/0, the two subinterfaces (for example G0/0.10 and G0/0.13 on LIB-R1), and G0/1.

| You see | Meaning | Fix |
|---|---|---|
| `administratively down` | Missing `no shutdown` | `conf t` → `interface X` → `no shutdown` → `end` |
| G0/1 `down` / `down` | No cable, or it's in the wrong switch | Check B1 rows 4–6: G0/1 goes to the **next** room's switch, Fa0/8 |
| G0/0 and its subinterfaces `down` | Trunk cable problem | Check B1 rows 1–3 |

Then check each WAN link on its own. From each router, ping both neighbours:

| On | Ping | Path tested |
|---|---|---|
| LIB-R1 | `ping 10.0.12.2` and `ping 10.0.13.2` | Library–Teachers, Library–Lab |
| TCH-R2 | `ping 10.0.23.2` | Teachers–Lab |

All must get `!!!!!` (the first `.` is ARP; that's fine). If one fails, that link's VLAN, cable or subinterface is wrong. Compare with the table in the design-change doc.

### D3. RIP has learned the other rooms

On each router:
```
show ip route rip
```

| Router | Must see |
|---|---|
| LIB-R1 | `192.168.20.0/24 [120/1] via 10.0.12.2, GigabitEthernet0/1` and `192.168.30.0/24 [120/1] via 10.0.13.2, GigabitEthernet0/0.13` |
| TCH-R2 | `192.168.10.0/24 [120/1] via 10.0.12.1, GigabitEthernet0/0.12` and `192.168.30.0/24 [120/1] via 10.0.23.2, GigabitEthernet0/1` |
| LAB-R3 | `192.168.10.0/24 [120/1] via 10.0.13.1, GigabitEthernet0/1` and `192.168.20.0/24 [120/1] via 10.0.23.1, GigabitEthernet0/0.23` |

Each router also shows the far WAN link with **two** `[120/1]` paths. That's normal (equal-cost paths, as in Expt 5).

Then run:
```
show ip protocols
```
Check that it shows:
- `Sending updates every 30 seconds`, `Invalid after 180 seconds, hold down 180, flushed after 240`
- `version 2`
- `Automatic network summarization is not in effect`
- the LAN subinterface (`GigabitEthernet0/0.10`, `.20` or `.30`) under `Passive Interface(s)`

**Write the timers down.** Section 6b compares the results against them.

### D4. PCs get an address and can reach other rooms

On the **Library PC** (Ubuntu):
1. Open **Settings → Network → Wired → ⚙ → IPv4**. Set **Automatic (DHCP)** and click **Apply**. Then turn the wired connection off and on again.
2. In a terminal:
   ```
   ip -4 addr
   ```
   You should see `192.168.10.21` or higher.
3. Ping across rooms:
   ```
   ping -c 4 192.168.20.1
   ping -c 4 192.168.30.1
   ```
   Both should get 4 replies.
4. Trace the route:
   ```
   traceroute 192.168.20.1
   ```
   You should see three lines: `192.168.10.1` (LIB-R1), `10.0.12.2`, then `192.168.20.1`. Both of the last two are TCH-R2. IOS answers the expired probe from the interface it arrived on, then the next probe from the address you traced. **`10.0.12.2` at hop 2 is the proof the path is the direct Library–Teachers link.** `10.0.13.2` there would mean a detour through LAB-R3. After T1, the same command should show `192.168.10.1 → 10.0.13.2 → 10.0.23.1 → 192.168.20.1`. Screenshot it before and after T1 run 1, as in Expt 5.
5. Note the TTL in the step 3 replies: it should be `ttl=254` for both. That's the baseline for G4.

Do the same on the **Teachers' PC**. It should get 192.168.20.21 or higher. Ping 192.168.10.1 and 192.168.30.1.

### D5. The script machine can reach all three routers

Do phase E1 first (the AUTO-PC address), then:
```powershell
ping 192.168.10.1
ping 192.168.20.1
ping 192.168.30.1
```
All three must reply.

> **If D1 to D5 do not all pass, do not start the tests.** Fix the build first. Partial results from a broken network are worse than none.

---

## Phase E: Laptop setup (10 min, Mouhamed)

### E1. Give the laptop the AUTO-PC address

0. **The machine running the scripts must be cabled to SW-LAB Fa0/5.** The scripts reach the routers over SSH, not over the console or Wi-Fi. Mouhamed's laptop has only Wi-Fi, so either:
   - bring a **USB-to-Ethernet adapter** and follow steps 1 to 4 below; or
   - run the scripts from an **Ubuntu lab PC** on SW-LAB Fa0/5:
     1. `git clone` the repo and `git checkout zayed/measurement-testing-visualisation`.
     2. `pip3 install --user -r requirements.txt`. This needs internet. The lab PCs look like Ubuntu 24.04 (Expt 2's Apache 2.4.58 is that release's version), where pip refuses with `externally-managed-environment`. If you see that, add `--break-system-packages` to the command.
     3. Set its wired IPv4 to manual: 192.168.30.20 / 255.255.255.0, gateway 192.168.30.1.
     4. Use `python3` instead of `python` in every command.

     The PowerShell-only snippets (F2, F4, F5) need small changes: drop `@'...'@ | python -` and run the Python part with `python3 - <<'EOF' ... EOF`.
1. **Keep Wi-Fi on** (`git push` and anything else online need it). Instead of a default gateway on the lab cable, give it **routes for the lab LANs only**, so internet traffic stays on Wi-Fi and lab traffic goes down the cable.
2. Find the wired adapter name:
   ```powershell
   Get-NetAdapter
   ```
   On Mouhamed's laptop the USB adapter is **`Ethernet 4`** (Realtek USB 2.5GbE).
3. Open PowerShell **as Administrator** (right-click → Run as administrator) and run:
   ```powershell
   netsh interface ipv4 set address name="Ethernet 4" static 192.168.30.20 255.255.255.0
   netsh interface ipv4 add route 192.168.10.0/24 "Ethernet 4" 192.168.30.1
   netsh interface ipv4 add route 192.168.20.0/24 "Ethernet 4" 192.168.30.1
   ```
   There is no gateway on the first line, on purpose. The two routes send only the Library and Teachers' LANs through LAB-R3.
4. Check it:
   ```powershell
   ipconfig
   route print -4 | findstr 192.168
   ```
   You should see `192.168.30.20` on `Ethernet 4`, and routes for 192.168.10.0 and 192.168.20.0 via 192.168.30.1.
5. **At the end of the lab**, put the adapter back to automatic: `netsh interface ipv4 set address name="Ethernet 4" dhcp`. The two routes go away with the static address.

### E2. Repo and Python

```powershell
cd D:\ccen356-rip-project
git status                 # must say: On branch zayed/measurement-testing-visualisation
python -m pytest           # must end with: N passed (no failures)
```
If `pytest` or `netmiko` is missing, run:
```powershell
pip install -r requirements.txt
```

The scripts default to `admin` / `Admin@123` / `class123`, which match the configs. Only if the routers use other credentials, set:
```powershell
$env:RIP_USER = "admin"; $env:RIP_PASS = "..."; $env:RIP_SECRET = "..."
```

### E3. Create the folders the plan writes into

```powershell
mkdir data\verification, data\ping_logs -Force
```

---

## Phase F: Router preparation from Python (15 min, Mouhamed)

Run every command from `D:\ccen356-rip-project`.

### F1. SSH works to all three routers

```powershell
python scripts/connect_test.py
```

You should see:
```
OK    LIB-R1  192.168.10.1  prompt LIB-R1  ...
OK    TCH-R2  192.168.20.1  prompt TCH-R2  ...
OK    LAB-R3  192.168.30.1  prompt LAB-R3  ...

3/3 routers reachable over SSH
```

| You see | Fix |
|---|---|
| `FAIL ... timed out` | Check the laptop IP and the two routes (E1: `route print -4`, look for 192.168.10.0 and 192.168.20.0), and D3 |
| `FAIL ... Authentication` | Check `username admin privilege 15 secret Admin@123` in the router's `show run` |
| `FAIL ... refused` | SSH is not configured. On the router: `conf t` → `crypto key generate rsa general-keys modulus 1024` → `ip ssh version 2` → `end` |

> The Windows `ssh` command may refuse these routers with `no matching host key type found`. That's only a client setting; netmiko still works. To test by hand, use:
> `ssh -o HostKeyAlgorithms=+ssh-rsa -o KexAlgorithms=+diffie-hellman-group14-sha1 admin@192.168.10.1`

### F2. Set every router's clock to the laptop's time

`parse_rip_debug.py` reads the dates on the debug lines, so the clocks must be set.

```powershell
@'
import sys; sys.path.insert(0, "scripts")
from datetime import datetime
from inventory import connect, ROUTERS
for name in ROUTERS:
    with connect(name) as c:
        c.send_command_timing(datetime.now().strftime("clock set %H:%M:%S %d %b %Y"))
        print(name, c.send_command("show clock").strip())
'@ | python -
```
You should see three lines, each showing today's date and the current time.

### F3. Timestamps and the 64 KB debug buffer

```powershell
python scripts/push_config.py configs/push/timestamps.txt all
```
Check that the output has no `% Invalid input` lines and that each router ends with the `copy running-config startup-config` reply.

### F4. Save the verification outputs and running-configs

These files are for Saif's report sections 3 and 4 and for `configs/exports/`.

```powershell
@'
import sys; sys.path.insert(0, "scripts")
from pathlib import Path
from inventory import connect, ROUTERS
out = Path("data/verification"); out.mkdir(parents=True, exist_ok=True)
cmds = ["show ip interface brief", "show ip protocols", "show ip route", "show ip rip database", "show clock"]
for name in ROUTERS:
    with connect(name) as c:
        Path(f"configs/exports/{name}.txt").write_text(c.send_command("show running-config"))
        (out / f"{name}.txt").write_text("\n\n".join(f"{name}# {x}\n{c.send_command(x)}" for x in cmds))
    print("saved", name)
'@ | python -
```

Then check:
1. Open `data/verification/LIB-R1.txt`. `show ip protocols` shows the timers 30 / 180 / 180 / 240.
2. Open `configs/exports/LIB-R1.txt`. It contains `service timestamps debug datetime msec` and `logging buffered 64000 debugging`.

**Switch exports:** on each switch console, type `terminal length 0`, then `show running-config`. Copy the output into `configs/exports/SW-LIB.txt`, `SW-TCH.txt` and `SW-LAB.txt`.

### F5. Push the RIP configuration from Python

This is brief item C: "push configuration commands, e.g. enabling RIP, adding networks". The blocks match Saif's config, so re-applying them changes nothing. The saved output is the evidence for section 5.

```powershell
foreach ($r in "LIB-R1", "TCH-R2", "LAB-R3") {
    python scripts/push_config.py configs/push/rip-$r.txt $r | Out-File -Encoding utf8 data/verification/push_rip_$r.txt
    Get-Content data/verification/push_rip_$r.txt
}
```
Check: no `% Invalid input`, and each ends with the save reply.

### F6. Capture normal RIP updates (and the parser's first look at real debug output)

This is brief item B: "capture RIP updates using debug ip rip and Python scripts". Each capture records 40 s, which covers at least one 30 s update cycle.

```powershell
foreach ($r in "LIB-R1", "TCH-R2", "LAB-R3") {
    python scripts/capture_rip_debug.py $r --label T0-updates --duration 40
}
python scripts/parse_rip_debug.py data/debug_logs/T0-updates_LIB-R1.txt --all
```

The last command must list **sent** and **received** updates with their routes. For example:
`<- 10.0.13.2 on GigabitEthernet0/1 periodic: 192.168.30.0/24 m1, ...`

> **If it lists nothing:** open `data/debug_logs/T0-updates_LIB-R1.txt` and send its first 30 lines to Mouhamed. The format in `scripts/parse_rip_debug.py` gets fixed now, before T1. The route parser is already confirmed on real output from these routers; the debug parser is not yet.

---

## Phase G: The tests (75 min)

### G0. Rules for every run

**Always pass `--duration`.** The monitor only counts a run as converged after the route has held its new state for 35 s. Shorter runs can end before that.

| Tests | `--duration` |
|---|---|
| T1, T2, T3, T4 | `120` |
| T5 | `420` |

**Run filenames:** each run saves to `data/debug_logs/Tn-runN_<router>.txt`. Never reuse a run number; a repeat overwrites the earlier file. If a run goes wrong, re-run the **same** number, and write "redone" in the Notes column of the results sheet.

**The countdown:** at the failure moment, Zayed counts out loud: "3, 2, 1, **go**". On "go", the person at the **measured router's console** presses Enter on `shutdown` (or `no shutdown`) and Zayed presses Enter on the runner window together. A late Enter makes the monitor's numbers wrong. If it was late, write it in Notes.

**Both ends of the link go down.** The WAN links run through switches, so a router doesn't notice when the router at the other end shuts its port. Every link test therefore shuts the **measured end** (a physical G0/1, on the console, on "go") and then the **far end** (a subinterface, a few seconds later). [`Design-Change-All-Ethernet.md`](Design-Change-All-Ethernet.md) explains why.

### G1. The same steps for every run (T1 to T4)

| # | Who | Does | Sees |
|---|---|---|---|
| 1 | Console person | Opens the **measured router's** console (from the test table) and logs in (`cisco`, then `enable`, then `class123`). Types `configure terminal` and `interface GigabitEthernet0/1`, but **not** `shutdown` yet | `LIB-R1(config-if)#` |
| 2 | Far-end person | Gets the far-end command ready **without pressing Enter**: the `push_config.py` line in a second PowerShell window, or the console commands on the far-end router | |
| 3 | Zayed | Types the run command from the test table and presses Enter | `[1/6] Taking before-snapshot...` |
| 4 | Zayed | Reads the `Precondition:` line | `... (ready)` |
| 5 | Zayed | If it says *Precondition not met*: answer `N`, wait 30 s, then start again from step 3 with the **same** run number | |
| 6 | Zayed | Waits for `[4/6] Starting route monitor`, then says "ping" | |
| 7 | Ping person | Starts the ping (section G4) | One reply per second |
| 8 | Zayed | About 5 to 10 s later, counts "3, 2, 1, go" | |
| 9 | Console person + Zayed | On "go", the console person presses Enter on `shutdown` and Zayed presses Enter on the laptop | The console shows `%LINK-5-CHANGED: Interface GigabitEthernet0/1, changed state to administratively down` |
| 10 | Far-end person | Immediately after "go", presses Enter on the far-end command | `push_config.py` prints the config lines with no `% Invalid` |
| 11 | Zayed | Waits for the run to finish (about 2 min), then reads out the `Debug convergence: X s` line, the monitor's first-change and converged times, and the route diff | `[6/6] ...` and `Before the next test, restore the network:` |
| 12 | Ping person | Presses Ctrl+C on the ping, counts the lost pings, and fills in one row of the results sheet (G5) | |
| 13 | Everyone | Does the **restore** from the test table, then waits as it says | |

### G2. The order of runs

**1. T0: baseline (2 min)**
```powershell
python scripts/run_experiment.py T0
```
Nothing to do on the routers. You should see `Saved baseline snapshot: data/snapshots/..._T0-baseline.json`. Open the file and check that every remote LAN is at metric 1 on every router.

**2. T1 and T4 pairs (20 min)**

T4 measures the recovery of the link T1 cuts, so always run them as a pair: T1-run1, T4-run1, T1-run2, T4-run2, T1-run3, T4-run3.

| | T1 run N (link down) | T4 run N (link back up) |
|---|---|---|
| Command | `python scripts/run_experiment.py T1 --run N --duration 120` | `python scripts/run_experiment.py T4 --run N --duration 120` |
| Measured router | LIB-R1 | LIB-R1 |
| **Before** "go" | nothing | Mouhamed: `python scripts/push_config.py configs/push/t1-far-up.txt TCH-R2 --no-save` and wait for it to finish |
| On "go" (**LIB-R1 console**) | `interface GigabitEthernet0/1` → **`shutdown`** | `interface GigabitEthernet0/1` → **`no shutdown`** |
| Right after "go" | Mouhamed: `python scripts/push_config.py configs/push/t1-far-down.txt TCH-R2 --no-save` | nothing |
| Expected | LIB-R1: `192.168.20.0/24 [120/2] via 10.0.13.2` | LIB-R1: `192.168.20.0/24 [120/1] via 10.0.12.2` |
| Ping (Library PC) | `192.168.20.1` | `192.168.20.1` |
| After the run | go straight to T4 | wait **30 s**, then the next T1 |

In T4, the far end (TCH-R2) comes up first, so T4 only measures LIB-R1's port coming back.

> **T1 run 1 is the real check.** It is the first time the convergence parser sees a real failure.
> - If it prints a `Debug convergence: X s` line: carry on.
> - If it prints `No convergence event pair found`: open `data/debug_logs/T1-run1_LIB-R1.txt` and search for `%LINK` and `RT:`.
>   - **No `%LINK` line:** the shut was on the wrong interface. It must be the physical G0/1, not a subinterface.
>   - **No `RT:` lines:** `debug ip routing` didn't stick. On LIB-R1, run `show debugging`.
>   - **`RT:` lines in a different format** from `RT: add 192.168.20.0/24 via 10.0.13.2, rip metric [120/2]`: the regex needs adjusting. Keep going with the tests, since the raw logs are saved, and re-parse later with `collect_results.py`.

**3. T2: Library–Lab link down (12 min), 3 runs, measured on LAB-R3**

| Step | What |
|---|---|
| Command | `python scripts/run_experiment.py T2 --run N --duration 120` |
| On "go" (**LAB-R3 console**) | `interface GigabitEthernet0/1` → **`shutdown`** |
| Right after "go" (**LIB-R1 console**) | `configure terminal` → `interface GigabitEthernet0/0.13` → **`shutdown`** → `end`. Use the console here: SSH to LIB-R1 runs over this link |
| Expected | LAB-R3: `192.168.10.0/24 [120/2] via 10.0.23.1` |
| Restore after the run | LIB-R1 console: `interface GigabitEthernet0/0.13` → `no shutdown`. Then LAB-R3 console: `interface GigabitEthernet0/1` → `no shutdown` |
| Before the next run | Wait **45 s**. On LAB-R3, `show ip route rip` shows `192.168.10.0/24 [120/1] via 10.0.13.1` |
| Ping (Library PC) | `192.168.30.1` |

The laptop's SSH session to LAB-R3 (the measured router) stays up in T2.

**4. T3: Teachers–Lab link down (12 min), 3 runs, measured on TCH-R2**

| Step | What |
|---|---|
| Command | `python scripts/run_experiment.py T3 --run N --duration 120` |
| On "go" (**TCH-R2 console**) | `interface GigabitEthernet0/1` → **`shutdown`** |
| Right after "go" | Mouhamed: `python scripts/push_config.py configs/push/t3-far-down.txt LAB-R3 --no-save` |
| Expected | TCH-R2: `192.168.30.0/24 [120/2] via 10.0.12.1` |
| Restore after the run | Mouhamed: `python scripts/push_config.py configs/push/t3-far-up.txt LAB-R3 --no-save`. Then TCH-R2 console: `interface GigabitEthernet0/1` → `no shutdown` |
| Before the next run | Wait **45 s**. On TCH-R2, `show ip route rip` shows `192.168.30.0/24 [120/1] via 10.0.23.2` |
| Ping (**Teachers' PC**) | `192.168.30.1`. The Library→Lab path doesn't use this link |

During T3 the laptop prints `session_lost`, then reconnects. **That is expected.** The SSH path to TCH-R2 runs over the link being cut. The debug output survives in the router's log buffer, and the script reads it back at step [5/6].

**5. T5: silent failure (25 min), 3 runs, about 7 min each**

Nothing goes down here, so RIP has to wait for its timers. The runner records for 420 s.

| # | Who | Does |
|---|---|---|
| 1 | Zayed | Runs `python scripts/run_experiment.py T5 --run N --duration 420` |
| 2 | Zayed | When `[4/6] Starting route monitor` appears, starts a stopwatch on a phone and says "ping" |
| 3 | Abdulrahman | Starts the ping to `192.168.30.1` from the Library PC |
| 4 | Mouhamed | At about **35 s** on the stopwatch, in a **second PowerShell window**, runs `python scripts/push_config.py configs/push/t5-start.txt LAB-R3 --no-save` |
| 5 | Zayed | Presses **Enter** in the runner window the moment the push command returns |
| 6 | Everyone | Waits. LIB-R1's route to 192.168.30.0/24 should go `possibly down` at around 180 s, then switch to `[120/2] via 10.0.12.2` at around 240 to 270 s |
| 7 | Mouhamed | After the runner finishes, runs `python scripts/push_config.py configs/push/t5-stop.txt LAB-R3 --no-save` |
| 8 | Zayed | Waits **60 s**, then checks that LIB-R1 shows `192.168.30.0/24 [120/1] via 10.0.13.2` again |

Expect very few lost pings in T5, because traffic keeps flowing on the stale route while it is in hold-down.

### G3. If you are short on time

Run the tests in this priority order, and do run 1 of everything before any run 2:
1. T0
2. T1-run1 and T4-run1
3. T5-run1 (the key result)
4. T2-run1
5. T3-run1
6. Then runs 2 and 3 of each

### G4. The ping method

Ping the far router's LAN gateway. It always answers, unlike a printer or a PC that may be asleep.

| Tests | From | Target |
|---|---|---|
| T1, T4 | Library PC | `192.168.20.1` |
| T2, T5 | Library PC | `192.168.30.1` |
| T3 | **Teachers' PC** | `192.168.30.1` |

**Ubuntu (the lab PCs):**
```bash
mkdir -p ~/ping_logs && cd ~/ping_logs
ping -O -W 1 192.168.20.1 | tee T1-run1_ping.txt
# Ctrl+C when Zayed says the runner has finished, then count the losses:
grep -cE "no answer yet|Unreachable" T1-run1_ping.txt
```
- `-O` prints a `no answer yet for icmp_seq=N` line for each lost reply.
- `-W 1` makes each loss worth about 1 s.

**Windows:**
```powershell
ping -t -w 1000 192.168.20.1 | ForEach-Object { $_; $_ | Out-File -Append -Encoding utf8 T1-run1_ping.txt }
# Ctrl+C at the end, then:
(Select-String -Path T1-run1_ping.txt -Pattern "timed out|unreachable|General failure").Count
```

Count `Destination Host Unreachable` lines as lost too. They come from a router that has no route at that moment.

**Watch the TTL; it shows the reroute.** A router answers a ping with TTL 255, and each router on the return path takes off 1.

| Test | Before the failure | After it converges | Why |
|---|---|---|---|
| T1 | `ttl=254` | `ttl=253` | TCH-R2's reply now comes back through LAB-R3 |
| T2 | `ttl=254` | `ttl=253` | LAB-R3's reply now comes back through TCH-R2 |
| T3 (Teachers' PC) | `ttl=254` | `ttl=253` | LAB-R3's reply now comes back through LIB-R1 |
| T4 | `ttl=253` | `ttl=254` | the direct link is back |
| T5 | `ttl=254` | **stays `ttl=254`** | LAB-R3 still hears LIB-R1, so its replies keep using the direct link even after LIB-R1 sends via TCH-R2: asymmetric routing |

The first reply with the new TTL marks when the return path changed, a fourth timing source alongside the debug log, the monitor and the ping loss. The T5 row is direct evidence of the asymmetric routing that section 6b discusses.

**Name each file after its run** (`T1-run1_ping.txt`, `T4-run1_ping.txt`, ...). At the end, copy them to the repo's `data/ping_logs/` with a USB stick. If that isn't possible, photograph the counts and write them on the sheet.

**Optional third method (the Expt 5 way), if there's time:** on the ping PC, run Wireshark with the filter `icmp` during one T1 run. Record T1 as the time of the frame after the last reply before the outage, and T2 as the time of the frame after the last `Host unreachable`. T2 − T1 is the outage as the PC saw it. Save the `.pcapng` to `data/ping_logs/`.

### G5. Results sheet (fill in as you go)

| Run | Debug conv. (s) | Monitor first change (s) | Monitor converged (s) | Session gap (s) | Pings lost | Notes |
|---|---|---|---|---|---|---|
| T1-run1 | | | | | | |
| T4-run1 | | | | | | |
| T1-run2 | | | | | | |
| T4-run2 | | | | | | |
| T1-run3 | | | | | | |
| T4-run3 | | | | | | |
| T2-run1 | | | | | | |
| T2-run2 | | | | | | |
| T2-run3 | | | | | | |
| T3-run1 | | | | | | |
| T3-run2 | | | | | | |
| T3-run3 | | | | | | |
| T5-run1 | | | | | | |
| T5-run2 | | | | | | |
| T5-run3 | | | | | | |

The scripts save everything except the ping counts. This sheet is the backup if a file goes missing, and the place to note anything unusual: a route that flapped, a late Enter, a slow far-end shut, a redone run.

---

## Phase H: Before leaving the lab (10 min)

### H1. Check the network is back to normal

```powershell
python scripts/get_routes.py T-end
```
Check:
- Every remote LAN is back at **metric 1** on every router.
- On the LAB-R3 console, `show run | include passive` shows **only** `passive-interface GigabitEthernet0/0.30`. That confirms `t5-stop` was pushed.
- On each router, `show ip interface brief` has every interface `up` / `up`. No far-end subinterface (G0/0.12, G0/0.13, G0/0.23) is still shut.
- On each router console, `show debugging` shows nothing turned on. If something is, run `undebug all`.

### H2. Build the results table and the charts

Replace each `0` with the real count from the sheet:
```powershell
python scripts/collect_results.py --ping T1-run1=0 T1-run2=0 T1-run3=0 T2-run1=0 T2-run2=0 T2-run3=0 T3-run1=0 T3-run2=0 T3-run3=0 T4-run1=0 T4-run2=0 T4-run3=0 T5-run1=0 T5-run2=0 T5-run3=0
python scripts/visualize.py
```
Check that `data/charts/convergence_comparison.png` exists and has 5 bars.

### H3. Commit and push before unplugging

The lab laptop may be wiped, so don't leave without pushing.
1. Wi-Fi stayed on all session, so `git push` works straight away.
2. Optionally, set the Ethernet adapter back to DHCP.
3. Commit and push:
```powershell
git add data configs/exports topology
git commit -m "Lab results: T0 to T5, 3 runs each"
git push
```

### H4. Leave the bench as you found it

1. Disconnect the cables.
2. Put the console cables back.
3. Power off the devices if the lab rules say so.

---

## What must exist at the end

| What | Where | Count |
|---|---|---|
| Running-configs (3 routers, 3 switches) | `configs/exports/*.txt` | 6 |
| Verification outputs | `data/verification/<router>.txt` | 3 |
| RIP push outputs | `data/verification/push_rip_<router>.txt` | 3 |
| Normal-state RIP update captures | `data/debug_logs/T0-updates_<router>.txt` / `.meta.json` | 3 |
| Photos of the rack and cabling | `topology/` | a few |
| Before/after snapshots | `data/snapshots/*.json` + `data/routes.csv` | 1 (T0) + 30 + T-end |
| Debug captures and parsed CSVs | `data/debug_logs/Tn-runN_<router>.txt` / `.csv` / `.meta.json` | 15 of each |
| Monitor logs | `data/monitor_logs/Tn-runN_<router>.csv` / `_polls.csv` / `_summary.json` | 15 of each |
| Ping logs | `data/ping_logs/Tn-runN_ping.txt` | 15 |
| Results table | `data/results.csv` + the Markdown table printed by `collect_results.py` | 1 |
| Charts | `data/charts/convergence_comparison.png`, `timeline_*.png` | 1 + timelines |
| Filled-in results sheet | photo, or this file | 1 |

With these, Section 6a's `[LAB_VALUE]` placeholders can be filled in, and Abdulrahman can write 6b.

## Course brief → evidence from this session

| Brief requirement | Comes from |
|---|---|
| Verify routing tables (`show ip route`) | F4 `data/verification/`, T0 snapshot |
| Capture RIP updates with `debug ip rip` and Python | F6 `T0-updates_*`, every `Tn-runN` debug capture |
| Connect to routers using SSH (netmiko) | F1 `connect_test.py` |
| Push configuration commands (enabling RIP, adding networks) | F5 `push_rip_*.txt`, F3 `timestamps.txt`, T5 |
| Retrieve routing tables, store as JSON / CSV | `data/snapshots/*.json`, `data/routes.csv` |
| Analyse routing changes after link failures | T1 to T5 diffs from `compare_routes.py`, `data/results.csv` |
| Report: routing table snapshots, convergence time, route changes | phases D, G and H |
| Repo: configuration files (.txt exports from routers) | F4 `configs/exports/` |
| Visualise routing behaviour | `data/charts/` from `visualize.py` |

This session does not cover the topology diagram (Saif), "Limitations of RIP" (Abdulrahman, no lab data needed) or the demo. If time is left at the end, do one rehearsal of the demo run-sheet on the real routers.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `% Invalid input` on a `show` command | You're still in config mode (`(config)#` prompt). Type `end` first, or use `do show ...` |
| Debug output is flooding a console and you can't type | Type `undebug all` blind and press Enter; `logging synchronous` keeps your typed line intact |
| A runner crashed mid-run and left debugs on | On that router's console: `undebug all`. Or run `python scripts/capture_rip_debug.py <ROUTER> --duration 1` |
| `Precondition not met` keeps repeating | The previous restore didn't happen or hasn't converged. Check `show ip route rip` on the measured router against the "Expected" line of the previous test's restore |
| `Could not reconnect to <router>` | The path to it is still down. Restore the link from the console, wait 45 s, then run `undebug all` on the console |
| A WAN ping in D2 fails but both interfaces are `up` | Wrong VLAN or a cable in the wrong switch. Check that the G0/1 cable is in the **next** room's switch, Fa0/8, and that `show vlan brief` puts Fa0/8 in the right WAN VLAN (12, 13 or 23) |
| A port takes ~30 s to pass traffic after `no shutdown` | `spanning-tree portfast` is missing on that switch port. Re-paste the "Router ports" block of the switch config |
| `Debug convergence` is missing on a run | Check the shutdown was on the measured router's **physical G0/1**. A subinterface shutdown logs no `%LINK` line |
| Far-end `push_config.py` times out | The path to that router went over the link you just cut. Do the far end on that router's console instead |
| A PC has a `169.254.x.x` address | DHCP failed. Check that the switch port is green and that `show ip dhcp binding` on the router lists the PC. Unplug and replug the PC |
| T5 never converges in 420 s | Check that `t5-start` actually applied: `show run \| section rip` on LAB-R3 must show `passive-interface GigabitEthernet0/1` |
