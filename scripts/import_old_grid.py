#!/usr/bin/env python3
"""One-off import of the old planner app's grid into dashboard-v2.

The old app stores tasks per (area, working-day-index) cell. Day N maps to a
real date by walking from the plan's start date and skipping Sundays plus the
old app's fixed holiday list. Rollover in the old app left duplicate copies of
unfinished tasks on multiple days; we keep only the latest copy (that's where
rollover last pushed it) and keep completed copies as history.

Usage:
    python scripts/import_old_grid.py                # dry run (prints summary, writes dump)
    python scripts/import_old_grid.py --apply        # wipe new-app tasks and import

Config (env vars or flags):
    OLD_API_BASE   e.g. https://web-production-xxxx.up.railway.app
    OLD_PLAN_ID    default: "default"
    NEW_API_BASE   default: https://dashboard-v2-backend-production.up.railway.app
    NEW_EMAIL / NEW_PASSWORD   contractor login for the new app (needed for --apply)
"""

import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import date, timedelta

# The OLD app's holiday list (MM-DD). Required to decode day indices exactly as
# the old app did — do NOT sync this with app/workdays.py (which is now
# Sundays-only going forward).
OLD_HOLIDAYS = {
    (12, 24), (12, 25), (12, 26), (12, 31), (1, 1),
    (3, 3), (3, 20), (4, 3), (4, 15), (5, 1), (5, 27),
}

# role -> new trade, replicating the old app's roleKey (grid.js) and the old
# backend's _norm_role alias map (remodel-backend/app.py).
ROLE_MAP = {
    "demolition": "Demolition",
    "civil work": "Civil",
    "civil": "Civil",
    "plumbing": "Plumbing",
    "plumber": "Plumbing",
    "plumbing work": "Plumbing",
    "electrical": "Electrical",
    "electric work": "Electrical",
    "electical": "Electrical",
    "carpentry": "Carpentry",
    "tiling": "Tiling",
    "tiler": "Tiling",
    "painting": "Painting",
    "painter": "Painting",
    "cleaning": "Cleaning",
    "other": "Other",
    "glass work": "Other",
    "metal work": "Other",
    "metal and roofing work": "Other",
}


def http_json(url, method="GET", body=None, token=None):
    headers = {}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as res:
        raw = res.read()
        return json.loads(raw) if raw else None


def date_for_day(start: date, day: int) -> date:
    """Replicates the old app's dateForDay(): day 1 == start date; each further
    day advances past Sundays and OLD_HOLIDAYS."""
    dt = start
    remain = max(0, day - 1)
    while remain > 0:
        dt = dt + timedelta(days=1)
        if dt.weekday() == 6:  # Sunday
            continue
        if (dt.month, dt.day) in OLD_HOLIDAYS:
            continue
        remain -= 1
    return dt


def normalize_task(raw):
    """Replicates _normalizeTaskObject in the old app's state.js — accepts the
    full format and the compact n/r/w/h/x/p format."""
    if isinstance(raw, str):
        try:
            t = json.loads(raw)
        except (ValueError, TypeError):
            t = {"name": raw}
        if not isinstance(t, dict):
            t = {"name": str(t)}
    elif isinstance(raw, dict):
        t = raw
    else:
        t = {"name": str(raw or "")}

    def num(*keys, default=0.0):
        for k in keys:
            v = t.get(k)
            try:
                if v is not None and v != "":
                    return float(v)
            except (TypeError, ValueError):
                continue
        return default

    name = str(t.get("name") or t.get("task") or t.get("n") or "").strip()
    role = str(t.get("role") or t.get("r") or "").strip()
    done = bool(t.get("done") or t.get("d") is True or t.get("x") is True or t.get("dd") is True)
    progress = num("progress", "p", default=0.0)
    progress = max(0, min(100, int(round(progress))))
    return {
        "name": name,
        "role": role,
        "workers": int(num("workers", "w")),
        "hours": num("hours", "h"),
        "done": done,
        "progress": 100 if done else progress,
    }


def trade_for_role(role: str) -> str:
    return ROLE_MAP.get(role.strip().lower(), "Other")


def convert(grid, start: date):
    """Old grid -> deduped list of new-app TaskInput dicts + stats."""
    stats = {
        "cells": len(grid.get("cells") or []),
        "source_strings": 0,
        "skipped_empty": 0,
        "collapsed_same_cell": 0,
        "rollover_dupes_dropped": 0,
    }
    # (area_lower, name_lower, trade) -> {day: task}
    groups = defaultdict(dict)
    for cell in grid.get("cells") or []:
        area = str(cell.get("area") or "").strip()
        day = int(cell.get("day") or 0)
        for s in cell.get("activities") or []:
            stats["source_strings"] += 1
            t = normalize_task(s)
            if not t["name"]:
                stats["skipped_empty"] += 1
                continue
            key = (area.lower(), t["name"].lower(), trade_for_role(t["role"]))
            existing = groups[key].get(day)
            if existing is not None:
                # exact same task in the same cell: keep the most-progressed copy
                stats["collapsed_same_cell"] += 1
                if t["progress"] > existing["task"]["progress"]:
                    groups[key][day] = {"area": area, "task": t}
                continue
            groups[key][day] = {"area": area, "task": t}

    tasks = []
    dupe_report = []
    for key, by_day in groups.items():
        days = sorted(by_day)
        # rollover duplicates: unfinished copies on multiple days -> keep latest
        undone_days = [d for d in days if not by_day[d]["task"]["done"]]
        keep_days = set(d for d in days if by_day[d]["task"]["done"])
        if undone_days:
            keep_days.add(undone_days[-1])
            dropped = undone_days[:-1]
            if dropped:
                stats["rollover_dupes_dropped"] += len(dropped)
                dupe_report.append(
                    f"  {by_day[undone_days[-1]]['area']} / {key[1]} [{key[2]}]: "
                    f"kept day {undone_days[-1]}, dropped days {dropped}"
                )
        for d in sorted(keep_days):
            entry = by_day[d]
            t = entry["task"]
            tasks.append({
                "name": t["name"],
                "area": entry["area"],
                "trade": trade_for_role(t["role"]),
                "workers": t["workers"],
                "hours": t["hours"],
                "start_date": date_for_day(start, d).isoformat(),
                "end_date": None,
                "progress": t["progress"],
                "_old_day": d,
            })

    tasks.sort(key=lambda t: (t["start_date"], t["area"], t["name"]))
    return tasks, stats, dupe_report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="wipe new-app tasks and import (default: dry run)")
    ap.add_argument("--old-base", default=os.getenv("OLD_API_BASE", ""))
    ap.add_argument("--plan", default=os.getenv("OLD_PLAN_ID", "default"))
    ap.add_argument("--new-base", default=os.getenv("NEW_API_BASE", "https://dashboard-v2-backend-production.up.railway.app"))
    ap.add_argument("--input", default="", help="read old grid from a JSON file instead of the old API")
    ap.add_argument("--start-date", default="", help="override project start date (YYYY-MM-DD); required with --input if the file lacks start_date")
    ap.add_argument("--dump", default="old_grid_converted.json", help="dry-run output file")
    args = ap.parse_args()

    # ---- fetch ----
    if args.input:
        with open(args.input) as f:
            grid = json.load(f)
    else:
        if not args.old_base:
            sys.exit("Need --old-base (or OLD_API_BASE), or --input <file>")
        url = f"{args.old_base.rstrip('/')}/plans/{args.plan}/grid"
        print(f"Fetching {url}")
        grid = http_json(url)

    start_raw = args.start_date or grid.get("start_date")
    if not start_raw:
        sys.exit("No start_date in the grid data — pass --start-date YYYY-MM-DD")
    start = date.fromisoformat(start_raw)

    # ---- convert ----
    tasks, stats, dupe_report = convert(grid, start)
    done = sum(1 for t in tasks if t["progress"] >= 100)
    prog = sum(1 for t in tasks if 0 < t["progress"] < 100)
    todo = len(tasks) - done - prog

    print(f"\nProject start date : {start}")
    print(f"Cells              : {stats['cells']}")
    print(f"Source strings     : {stats['source_strings']}")
    print(f"  skipped (empty)  : {stats['skipped_empty']}")
    print(f"  same-cell dupes  : {stats['collapsed_same_cell']}")
    print(f"  rollover dupes   : {stats['rollover_dupes_dropped']}")
    print(f"Tasks to import    : {len(tasks)}  (done {done} / in-progress {prog} / todo {todo})")
    if tasks:
        print(f"Date range         : {tasks[0]['start_date']} → {tasks[-1]['start_date']}")
    if dupe_report:
        print(f"\nRollover duplicates resolved ({len(dupe_report)} groups):")
        print("\n".join(dupe_report))

    # sanity: every source string is accounted for
    accounted = (len(tasks) + stats["skipped_empty"] + stats["collapsed_same_cell"]
                 + stats["rollover_dupes_dropped"])
    assert accounted == stats["source_strings"], (
        f"reconciliation failed: {accounted} != {stats['source_strings']}")

    if not args.apply:
        with open(args.dump, "w") as f:
            json.dump(tasks, f, indent=2)
        print(f"\nDRY RUN — converted tasks written to {args.dump}. Re-run with --apply to import.")
        return

    # ---- apply ----
    email = os.getenv("NEW_EMAIL") or input("New-app contractor email: ")
    password = os.getenv("NEW_PASSWORD") or input("New-app password: ")
    base = args.new_base.rstrip("/")
    token = http_json(f"{base}/auth/login", "POST", {"email": email, "password": password})["access_token"]

    existing = http_json(f"{base}/tasks", token=token)
    print(f"\nDeleting {len(existing)} existing task(s)…")
    for t in existing:
        http_json(f"{base}/tasks/{t['id']}", "DELETE", token=token)

    print(f"Setting project start_date to {start}…")
    http_json(f"{base}/project", "PATCH", {"start_date": start.isoformat()}, token=token)

    print(f"Importing {len(tasks)} task(s)…")
    for i, t in enumerate(tasks, 1):
        body = {k: v for k, v in t.items() if not k.startswith("_")}
        http_json(f"{base}/tasks", "POST", body, token=token)
        if i % 25 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}")

    final = http_json(f"{base}/tasks", token=token)
    print(f"\nDone. New app now has {len(final)} tasks.")
    assert len(final) == len(tasks), "post-import count mismatch!"


if __name__ == "__main__":
    main()
