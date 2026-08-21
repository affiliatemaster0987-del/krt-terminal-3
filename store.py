"""
KRT · STORAGE
═════════════
Every file the terminal needs to keep lived in /tmp. On Render /tmp is wiped
on every deploy and every worker restart, so a day's 24 calls vanished the
moment anything was pushed — and the accuracy dashboard could never build a
7-day or 30-day number because there was never more than one session of data.

This picks the best directory available, in order:

  1. $KRT_DATA_DIR        — set it yourself if you want an exact path
  2. /var/data            — where a Render Persistent Disk mounts
  3. ./krt_data           — the project folder (survives restarts, not deploys)
  4. /tmp                 — last resort, wiped constantly

To keep history for a year you need a real disk. On Render:
    Dashboard -> your service -> Disks -> Add Disk
    Mount path: /var/data     Size: 1 GB
That mount point is picked up automatically by the list above. Without a disk
the terminal still runs, it just cannot remember yesterday.
"""

import json
import os

CANDIDATES = [
    os.environ.get("KRT_DATA_DIR"),
    "/var/data",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "krt_data"),
    "/tmp",
]


def _pick_dir():
    for d in CANDIDATES:
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".krt_write_test")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
            return d
        except Exception:
            continue
    return "/tmp"


DATA_DIR = _pick_dir()
PERSISTENT = DATA_DIR not in ("/tmp",)

print(f"[store] data dir: {DATA_DIR} "
      f"({'persistent' if PERSISTENT else 'EPHEMERAL — history will be lost on deploy'})")


def path(name):
    return os.path.join(DATA_DIR, name)


def read_json(name, default=None):
    try:
        with open(path(name)) as f:
            return json.load(f)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[store] read {name} failed:", str(e)[:110])
    return default if default is not None else None


def write_json(name, data):
    """Atomic — a crash mid-write can never leave a half-written file."""
    p = path(name)
    tmp = p + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, p)
        return True
    except Exception as e:
        print(f"[store] write {name} failed:", str(e)[:110])
        return False


def status():
    try:
        n = len(os.listdir(DATA_DIR))
    except Exception:
        n = 0
    return {"dir": DATA_DIR, "persistent": PERSISTENT, "files": n}
