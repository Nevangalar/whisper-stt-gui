"""
tests/test_evdev_keys.py – Diagnose: zeigt alle evdev Key-Events.
Drücke Ctrl+Space um zu sehen welche Codes/Namen erzeugt werden.
Beenden mit Q.
"""
import select
import sys

try:
    import evdev
    from evdev import ecodes
except ImportError:
    print("evdev nicht installiert: pip install evdev")
    sys.exit(1)

all_paths = list(evdev.list_devices())
if not all_paths:
    print("Keine Devices – bist du in der 'input' Gruppe? (groups)")
    sys.exit(1)

kb_devs = []
for path in all_paths:
    try:
        dev = evdev.InputDevice(path)
        caps = dev.capabilities()
        key_caps = caps.get(ecodes.EV_KEY, [])
        if ecodes.EV_KEY in caps and ecodes.KEY_A in key_caps:
            kb_devs.append(dev)
        else:
            dev.close()
    except Exception:
        pass

print(f"Gefundene Tastaturen: {len(kb_devs)}")
for d in kb_devs:
    print(f"  {d.path}: {d.name}")

print("\nDrücke Tasten (Ctrl+Space zum Testen). 'q' zum Beenden.\n")

held = set()
fds  = {d.fd: d for d in kb_devs}

while True:
    try:
        r, _, _ = select.select(list(fds.keys()), [], [], 1.0)
    except KeyboardInterrupt:
        break
    for fd in r:
        dev = fds.get(fd)
        if not dev:
            continue
        try:
            for event in dev.read():
                if event.type != ecodes.EV_KEY:
                    continue
                if event.value == 2:  # key repeat – ignorieren
                    continue
                raw_name = ecodes.KEY.get(event.code, f"code_{event.code}")
                if isinstance(raw_name, list):
                    raw_name = raw_name[0]
                action = "DOWN" if event.value == 1 else "UP  "
                if event.value == 1:
                    held.add(raw_name)
                else:
                    held.discard(raw_name)
                print(f"  code={event.code:3d}  {raw_name:<20s} {action}  |  held={held}")
                if raw_name in ("KEY_Q", "KEY_ESC"):
                    print("Beendet.")
                    sys.exit(0)
        except OSError:
            fds.pop(fd, None)
