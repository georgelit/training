#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает данные для страницы прогресса из локальной выгрузки Garmin.

Только чтение: ходит в garmin-ai/garmin/history.json и trainingpeaks/,
которые наполняют sync_garmin.py и tp_sync.py. В Garmin ничего не пишет.
"""
import datetime as dt
import json
import os
import statistics as st
import sys
from collections import defaultdict

GA = os.path.expanduser("~/Documents/Treaning + Claude/garmin-ai")
RACE = "2026-09-13"
HARD_KEYS = ["vo2", "interval", "intervalo", "umbral", "threshold", "series",
             "fuerte", "sprint", "tempo", "pot.", "potencia", "test ftp"]


def sport(t):
    t = (t or "").lower()
    if "swim" in t: return "swim"
    if "cycl" in t or "bik" in t or t == "virtual_ride": return "bike"
    if "run" in t: return "run"
    return "other"


def is_hard(a):
    if any(k in (a.get("name") or "").lower() for k in HARD_KEYS): return True
    return (a.get("aerobic_te") or 0) >= 3.5


def mean(xs, nd=1):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), nd) if xs else None


def monday(d): return d - dt.timedelta(days=d.weekday())


def build(weeks=16):
    h = json.load(open(os.path.join(GA, "garmin/history.json")))
    acts = [a for a in h["activities"] if a.get("date")]
    well = [w for w in h["wellness"] if w.get("date")]
    today = dt.date.today()

    # ── недели ──
    this_mon = monday(today)
    starts = [this_mon - dt.timedelta(days=7 * i) for i in range(weeks - 1, -1, -1)]
    wk = []
    for ms in starts:
        me = ms + dt.timedelta(days=6)
        aa = [a for a in acts if ms.isoformat() <= a["date"] <= me.isoformat()]
        ww = [w for w in well if ms.isoformat() <= w["date"] <= me.isoformat()]
        by = defaultdict(float)
        for a in aa:
            by[sport(a["type"])] += (a.get("duration_min") or 0) / 60
        wk.append({
            "start": ms.isoformat(),
            "label": "%d.%02d" % (ms.day, ms.month),
            "h": round(sum(by.values()), 1),
            "swim": round(by["swim"], 1), "bike": round(by["bike"], 1), "run": round(by["run"], 1),
            "vert": round(sum((a.get("elevation_gain_m") or 0) for a in aa)),
            "hard": sum(1 for a in aa if is_hard(a)),
            "n": len(aa),
            "hrv": mean([w.get("hrv_ms") for w in ww]),
            "rhr": mean([w.get("resting_hr") for w in ww]),
            "sleep": mean([w.get("sleep_hours") for w in ww]),
            "readiness": mean([w.get("training_readiness") for w in ww]),
        })

    # ── бег: темп при пульсе ──
    runs = []
    for a in sorted(acts, key=lambda x: x["date"]):
        if sport(a["type"]) != "run": continue
        km, mn, hr = a.get("distance_km") or 0, a.get("duration_min") or 0, a.get("avg_hr")
        if km < 3 or not hr: continue
        pace = mn / km * 60                      # сек на км
        runs.append({"d": a["date"], "km": round(km, 1), "pace": round(pace),
                     "hr": round(hr), "eff": round((60 / (pace / 60)) / hr, 4),
                     "name": (a.get("name") or "")[:40]})

    # ── плавание: гребков на 50 м ──
    swims = []
    sp = os.path.join(GA, "garmin/all_recent.json")
    if os.path.exists(sp):
        for a in sorted(json.load(open(sp)), key=lambda x: x.get("startTimeLocal", "")):
            if "swim" not in str(a.get("activityType", {}).get("typeKey", "")).lower(): continue
            pl, u = a.get("poolLength"), (a.get("unitOfPoolLength") or {})
            f = u.get("factor") or 1
            if not pl or not a.get("avgStrokes"): continue
            plm = pl / f
            swims.append({"d": a["startTimeLocal"][:10], "pool": round(plm),
                          "per50": round(a["avgStrokes"] * (50.0 / plm), 1),
                          "m": round(a.get("distance") or 0)})

    # ── восстановление, последние 90 дней ──
    rec = [{"d": w["date"], "hrv": w.get("hrv_ms"), "rhr": w.get("resting_hr"),
            "sleep": w.get("sleep_hours"), "rd": w.get("training_readiness")}
           for w in well[-90:]]

    # ── база и сегодня ──
    hrv90 = [w.get("hrv_ms") for w in well[-30:] if w.get("hrv_ms")]
    rhr90 = [w.get("resting_hr") for w in well[-30:] if w.get("resting_hr")]
    last = well[-1]

    # ── план ──
    plan = []
    tp = os.path.join(GA, "trainingpeaks/tp_data.json")
    if os.path.exists(tp):
        t = json.load(open(tp))
        for e in t.get("events", []):
            if e.get("date", "") >= today.isoformat() and e.get("type") not in ("", None):
                plan.append({"d": e["date"], "s": e.get("summary", ""),
                             "t": (e.get("metrics") or {}).get("Planned Time", "")})
        plan = plan[:8]

    # ── итоги года ──
    y0 = (today - dt.timedelta(days=365)).isoformat()
    ya = [a for a in acts if a["date"] >= y0]
    yby = defaultdict(lambda: {"h": 0.0, "km": 0.0, "n": 0})
    for a in ya:
        s = sport(a["type"])
        yby[s]["h"] += (a.get("duration_min") or 0) / 60
        yby[s]["km"] += a.get("distance_km") or 0
        yby[s]["n"] += 1
    year = {k: {"h": round(v["h"]), "km": round(v["km"]), "n": v["n"]} for k, v in yby.items()}

    # сегодняшний вердикт тем же движком, что и утренняя сводка
    verdict = None
    try:
        sys.path.insert(0, GA)
        import coach_signals
        sg = coach_signals.compute()
        if sg.get("verdict") in ("hard", "easy", "rest"):
            bits = []
            if sg["today"].get("hrv") and sg["baselines"].get("hrv_ratio"):
                bits.append("HRV %s, это %d%% от базы" % (sg["today"]["hrv"], round(sg["baselines"]["hrv_ratio"] * 100)))
            if sg["today"].get("readiness") is not None:
                bits.append("готовность %s" % sg["today"]["readiness"])
            if sg["today"].get("sleep_h") is not None:
                bits.append("сон %s ч" % sg["today"]["sleep_h"])
            if sg.get("load_triggers"):
                bits.append("по нагрузке: " + ", ".join(sg["load_triggers"]))
            verdict = {"verdict": sg["verdict"], "why": " · ".join(bits)}
    except Exception as e:
        print("вердикт недоступен: %s" % type(e).__name__, file=sys.stderr)

    return {
        "verdict": verdict,
        "generated": dt.datetime.now().strftime("%d.%m.%Y %H:%M"),
        "days_to_race": (dt.date.fromisoformat(RACE) - today).days,
        "race": RACE,
        "weeks": wk, "runs": runs, "swims": swims, "recovery": rec,
        "plan": plan, "year": year,
        "today": {"hrv": last.get("hrv_ms"), "rhr": last.get("resting_hr"),
                  "sleep": last.get("sleep_hours"), "rd": last.get("training_readiness"),
                  "date": last["date"]},
        "base": {"hrv": mean(hrv90), "rhr": mean(rhr90)},
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
