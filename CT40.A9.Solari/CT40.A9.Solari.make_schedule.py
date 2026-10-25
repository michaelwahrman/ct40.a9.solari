#!/usr/bin/env python3
"""CT40.A9.Solari.make_schedule.py

Generates CT40.A9.Solari.schedule.json: the column labels plus an explicit,
time-stamped list of "row R shows these field values from time T" events.

You can hand-edit the JSON directly instead; this script is only a convenient
way to produce a believable half-hour of Penn Station traffic (trains arrive,
board, depart, get delayed, change gates, and the board ripples up when a
train is removed).

Run (Linux / WSL):   python3 CT40.A9.Solari.make_schedule.py
Then:                python3 CT40.A9.Solari.build_embedded.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = 10
START = "9:58:00 AM"
END = "10:28:00 AM"
STATION = "NEW YORK"

def secs(s):
    """'10:01 AM' or '9:58:05 AM' -> seconds after midnight."""
    t, ap = s.strip().split()
    parts = [int(p) for p in t.split(":")]
    while len(parts) < 3:
        parts.append(0)
    h, m, sec = parts
    h = h % 12 + (12 if ap.upper() == "PM" else 0)
    return h * 3600 + m * 60 + sec

def clock(n, with_seconds=True):
    n = int(round(n)) % 86400
    h, m, s = n // 3600, (n // 60) % 60, n % 60
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}:{s:02d} {ap}" if with_seconds else f"{h12}:{m:02d} {ap}"

T0 = secs(START)

# name, kind (dep = leaving New York, arr = arriving), other city, scheduled, gate
TRAINS = [
    ("NORTH CAROLINA SPECIAL",     "dep", "RALEIGH",      "9:59 AM",  "7"),
    ("MERCHANTS LIMITED",          "arr", "BOSTON",       "10:00 AM", "12"),
    ("SILVER METEOR",              "dep", "MIAMI",        "10:03 AM", "4"),
    ("CONGRESSIONAL",              "arr", "WASHINGTON",   "10:05 AM", "9"),
    ("LAKE SHORE LIMITED",         "dep", "CHICAGO",      "10:07 AM", "15"),
    ("PALMETTO",                   "dep", "SAVANNAH",     "10:10 AM", "3"),
    ("MAPLE LEAF",                 "arr", "TORONTO",      "10:12 AM", "11"),
    ("CRESCENT",                   "dep", "NEW ORLEANS",  "10:14 AM", "6"),
    ("YANKEE CLIPPER",             "arr", "BOSTON",       "10:16 AM", "13"),
    ("BROADWAY LIMITED",           "dep", "CHICAGO",      "10:18 AM", "10"),
    ("PENNSYLVANIAN",              "dep", "PITTSBURGH",   "10:20 AM", "2"),
    ("ADIRONDACK",                 "arr", "MONTREAL",     "10:22 AM", "14"),
    ("SPIRIT OF ST. LOUIS",        "dep", "ST. LOUIS",    "10:24 AM", "5"),
    ("CAROLINIAN",                 "dep", "CHARLOTTE",    "10:26 AM", "8"),
    ("SENATOR",                    "arr", "WASHINGTON",   "10:28 AM", "12"),
    ("TWENTIETH CENTURY LIMITED",  "dep", "CHICAGO",      "10:30 AM", "1"),
    ("VERMONTER",                  "arr", "ST. ALBANS",   "10:32 AM", "16"),
    ("SOUTHERNER",                 "dep", "NEW ORLEANS",  "10:35 AM", "4"),
    ("GEORGE WASHINGTON",          "arr", "RICHMOND",     "10:38 AM", "9"),
    ("FLORIDA SPECIAL",            "dep", "TAMPA",        "10:41 AM", "7"),
    ("ETHAN ALLEN EXPRESS",        "arr", "RUTLAND",      "10:44 AM", "11"),
    ("CARDINAL",                   "dep", "CINCINNATI",   "10:47 AM", "3"),
]

# Scripted surprises, seconds after START -> (train name, changes).
# The first few land within seconds of pressing Forward "just for fun".
SURPRISES = [
    (4,   "NORTH CAROLINA SPECIAL", {"status": "DELAYED", "time": "10:01 AM"}),
    (9,   "PALMETTO",               {"gate": "17"}),
    (14,  "MAPLE LEAF",             {"status": "DELAYED", "time": "10:21 AM"}),
    (20,  "CRESCENT",               {"gate": "2"}),
    (27,  "YANKEE CLIPPER",         {"status": "CANCELLED"}),
    (35,  "BROADWAY LIMITED",       {"status": "DELAYED", "time": "10:25 AM"}),
    (300, "SENATOR",                {"status": "DELAYED", "time": "10:37 AM"}),
    (420, "SOUTHERNER",             {"gate": "18"}),
    (610, "FLORIDA SPECIAL",        {"status": "DELAYED", "time": "10:52 AM"}),
    (900, "CARDINAL",               {"gate": "12"}),
]

def build_timelines():
    """For each train: list of (t, changes) and a removal time."""
    tl = {}
    for name, kind, city, sched, gate in TRAINS:
        tl[name] = {
            "kind": kind, "sort": secs(sched),
            "base": {"train": name, "from": city if kind == "arr" else STATION,
                     "to": STATION if kind == "arr" else city,
                     "time": sched, "gate": gate, "status": "ON TIME"},
            "changes": [], "remove": None,
        }
    for dt, name, ch in SURPRISES:
        tl[name]["changes"].append((T0 + dt, dict(ch)))

    for name, t in tl.items():
        # Effective time = last scheduled 'time' change that happens before the train runs.
        eff = t["sort"]
        for when, ch in t["changes"]:
            if "time" in ch:
                eff = secs(ch["time"])
        cancelled = any(ch.get("status") == "CANCELLED" for _, ch in t["changes"])
        if cancelled:
            when = [w for w, ch in t["changes"] if ch.get("status") == "CANCELLED"][0]
            t["remove"] = when + 150
            continue
        delayed = any(ch.get("status") == "DELAYED" for _, ch in t["changes"])
        steps = []
        if t["kind"] == "dep":
            steps += [(eff - 300, "BOARDING"), (eff - 60, "ALL ABOARD"), (eff, "DEPARTED")]
            t["remove"] = eff + 60
        else:
            steps += [(eff - 90, "ARRIVING"), (eff, "ARRIVED")]
            t["remove"] = eff + 75
        for when, st in steps:
            # a delayed train keeps saying DELAYED until it is actually boarding/arriving
            t["changes"].append((max(when, T0), {"status": st}))
        t["changes"].sort(key=lambda c: c[0])
        # If a train was delayed at time d, drop any normal step scheduled before d.
        if delayed:
            dtime = min(w for w, ch in t["changes"] if ch.get("status") == "DELAYED")
            t["changes"] = [(w, ch) for w, ch in t["changes"]
                            if not ("status" in ch and ch["status"] != "DELAYED" and w <= dtime and w <= T0)]
    return tl

def state_at(tl, now):
    rows = []
    for name, t in tl.items():
        if t["remove"] is not None and now >= t["remove"]:
            continue
        cur = dict(t["base"])
        for when, ch in t["changes"]:
            if when <= now:
                cur.update(ch)
        rows.append((t["sort"], cur))
    rows.sort(key=lambda r: r[0])
    out = [r[1] for r in rows[:ROWS]]
    blank = {k: "" for k in ("train", "status", "from", "to", "time", "gate")}
    while len(out) < ROWS:
        out.append(dict(blank))
    return out

def main():
    tl = build_timelines()
    t_end = secs(END)
    times = {T0}
    for t in tl.values():
        for when, _ in t["changes"]:
            times.add(when)
        if t["remove"] is not None:
            times.add(t["remove"])
    times = sorted(x for x in times if T0 <= x < t_end)

    events, prev = [], None
    for now in times:
        cur = state_at(tl, now)
        for r, row in enumerate(cur):
            if prev is None:
                events.append({"t": clock(now), "row": r, "set": row})
            else:
                diff = {k: v for k, v in row.items() if prev[r].get(k) != v}
                if diff:
                    events.append({"t": clock(now), "row": r, "set": diff})
        prev = cur

    doc = {
        "_about": "CT40.A9.Solari schedule. 'labels' are the column headings shown above the board (one per field id in CT40.A9.Solari.fields.json). 'events' say: from master-clock time t, row 'row' (0 = top) shows these field values. Fields not mentioned keep what they had. The board state at any time = all events with t <= clock, applied in order. Times are h:mm:ss AM/PM. When the clock reaches endTime and loop is true, it jumps back to startTime.",
        "version": "CT40.A9.Solari",
        "title": "TRAINS",
        "labels": {"train": "TRAIN", "status": "STATUS", "from": "FROM",
                   "to": "TO", "time": "TIME", "gate": "GATE"},
        "startTime": START,
        "endTime": END,
        "loop": True,
        "events": events,
    }
    path = os.path.join(HERE, "CT40.A9.Solari.schedule.json")
    with open(path, "w") as f:
        # one event per line keeps the file easy to read and hand-edit
        f.write("{\n")
        keys = [k for k in doc if k != "events"]
        for k in keys:
            f.write(f"  {json.dumps(k)}: {json.dumps(doc[k])},\n")
        f.write('  "events": [\n')
        f.write(",\n".join("    " + json.dumps(e) for e in events))
        f.write("\n  ]\n}\n")
    print(f"wrote {path}: {len(events)} events, {len(times)} change times")

if __name__ == "__main__":
    main()
