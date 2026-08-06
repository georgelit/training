#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает index.html страницы прогресса из данных collect.py."""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─────────────────────────── графики ───────────────────────────

def bars(weeks, W=760, H=190):
    """Недельный объём, столбики с разбивкой по видам спорта."""
    pad_l, pad_b, pad_t = 30, 26, 12
    n = len(weeks)
    top = max([w["h"] for w in weeks] + [1])
    top = max(top, 1)
    bw = (W - pad_l - 8) / n
    o = []
    # горизонтальная сетка
    for frac in (0.25, 0.5, 0.75, 1.0):
        y = pad_t + (H - pad_t - pad_b) * (1 - frac)
        o.append('<line class="grid" x1="%.1f" y1="%.1f" x2="%d" y2="%.1f"/>' % (pad_l, y, W - 4, y))
        o.append('<text class="ax" x="%.1f" y="%.1f" text-anchor="end">%.0f</text>'
                 % (pad_l - 6, y + 3.5, top * frac))
    for i, w in enumerate(weeks):
        x = pad_l + i * bw + bw * 0.16
        bwi = bw * 0.68
        y0 = H - pad_b
        for key, cls in (("swim", "sw"), ("bike", "bk"), ("run", "rn")):
            v = w.get(key) or 0
            if v <= 0:
                continue
            hh = (H - pad_t - pad_b) * v / top
            y0 -= hh
            o.append('<rect class="b %s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"><title>'
                     '%s · %s %.1f ч</title></rect>'
                     % (cls, x, y0, bwi, hh, w["label"], key, v))
        if i % max(1, n // 8) == 0 or i == n - 1:
            o.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                     % (x + bwi / 2, H - 8, w["label"]))
    return '<svg viewBox="0 0 %d %d" role="img" aria-label="Недельный объём">%s</svg>' % (W, H, "".join(o))


def line_chart(series, W=760, H=170, band=None, fmt="%.0f", label=""):
    """Линия по времени. series = [(подпись, значение)], band = (низ, верх) для полосы базы."""
    pts = [(i, v) for i, (_, v) in enumerate(series) if isinstance(v, (int, float))]
    if len(pts) < 2:
        return '<p class="muted">данных мало</p>'
    pad_l, pad_b, pad_t = 34, 22, 12
    vs = [v for _, v in pts]
    lo, hi = min(vs), max(vs)
    if band:
        lo, hi = min(lo, band[0]), max(hi, band[1])
    if hi == lo:
        hi = lo + 1
    rng = hi - lo
    lo -= rng * 0.12
    hi += rng * 0.12
    n = len(series)
    X = lambda i: pad_l + (W - pad_l - 8) * (i / max(n - 1, 1))
    Y = lambda v: pad_t + (H - pad_t - pad_b) * (1 - (v - lo) / (hi - lo))
    o = []
    if band:
        o.append('<rect class="band" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                 % (pad_l, Y(band[1]), W - pad_l - 8, max(Y(band[0]) - Y(band[1]), 1)))
    for frac in (0, 0.5, 1.0):
        v = lo + (hi - lo) * frac
        y = Y(v)
        o.append('<line class="grid" x1="%.1f" y1="%.1f" x2="%d" y2="%.1f"/>' % (pad_l, y, W - 4, y))
        o.append('<text class="ax" x="%.1f" y="%.1f" text-anchor="end">%s</text>'
                 % (pad_l - 6, y + 3.5, fmt % v))
    d = "M" + " L".join("%.1f %.1f" % (X(i), Y(v)) for i, v in pts)
    o.append('<path class="ln" d="%s"/>' % d)
    li, lv = pts[-1]
    o.append('<circle class="dot" cx="%.1f" cy="%.1f" r="4"/>' % (X(li), Y(lv)))
    for i in (0, n // 2, n - 1):
        if 0 <= i < n:
            o.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                     % (X(i), H - 6, esc(series[i][0])))
    return '<svg viewBox="0 0 %d %d" role="img" aria-label="%s">%s</svg>' % (W, H, esc(label), "".join(o))


def scatter(points, W=760, H=190, ylab="", better="ниже"):
    """Точки по времени с линией тренда. points = [(дата, значение, подпись)]"""
    if len(points) < 3:
        return '<p class="muted">данных мало</p>'
    pad_l, pad_b, pad_t = 40, 24, 12
    vs = [p[1] for p in points]
    lo, hi = min(vs), max(vs)
    rng = (hi - lo) or 1
    lo -= rng * 0.15
    hi += rng * 0.15
    n = len(points)
    X = lambda i: pad_l + (W - pad_l - 8) * (i / max(n - 1, 1))
    Y = lambda v: pad_t + (H - pad_t - pad_b) * (1 - (v - lo) / (hi - lo))
    o = []
    for frac in (0, 0.5, 1.0):
        v = lo + (hi - lo) * frac
        y = Y(v)
        o.append('<line class="grid" x1="%.1f" y1="%.1f" x2="%d" y2="%.1f"/>' % (pad_l, y, W - 4, y))
        o.append('<text class="ax" x="%.1f" y="%.1f" text-anchor="end">%s</text>'
                 % (pad_l - 6, y + 3.5, ylab % v if "%" in ylab else "%.0f" % v))
    # линия тренда, метод наименьших квадратов
    mx = sum(range(n)) / n
    my = sum(vs) / n
    den = sum((i - mx) ** 2 for i in range(n)) or 1
    k = sum((i - mx) * (vs[i] - my) for i in range(n)) / den
    o.append('<line class="trend" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
             % (X(0), Y(my + k * (0 - mx)), X(n - 1), Y(my + k * (n - 1 - mx))))
    for i, (d, v, lbl) in enumerate(points):
        o.append('<circle class="pt" cx="%.1f" cy="%.1f" r="3.4"><title>%s · %s</title></circle>'
                 % (X(i), Y(v), esc(d), esc(lbl)))
    for i in (0, n // 2, n - 1):
        o.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                 % (X(i), H - 6, points[i][0][5:].replace("-", ".")))
    return '<svg viewBox="0 0 %d %d" role="img">%s</svg>' % (W, H, "".join(o))


# ─────────────────────────── страница ───────────────────────────

CSS = """
:root{
  --bg:#f4f5f7; --card:#ffffff; --ink:#12161c; --soft:#5a6472; --faint:#9aa4b2;
  --rule:#dfe3e9; --band:#e8ecf2;
  --sw:#1b9aaa; --bk:#e08a1e; --rn:#c8386f; --ok:#2f9e5f; --warn:#d98324; --bad:#c0392b;
  --serif:ui-serif,"Iowan Old Style",Palatino,Georgia,serif;
  --sans:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
  --shadow:0 1px 2px rgba(18,22,28,.05),0 8px 24px rgba(18,22,28,.06);
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0e1116; --card:#161b22; --ink:#e6edf3; --soft:#9aa6b4; --faint:#5c6773;
  --rule:#252c36; --band:#1c232c;
  --sw:#3fc2d4; --bk:#f0a63a; --rn:#ef6b9b; --ok:#4fc281; --warn:#e9a13b; --bad:#e56a5a;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 28px rgba(0,0,0,.35);
}}
:root[data-theme="dark"]{
  --bg:#0e1116; --card:#161b22; --ink:#e6edf3; --soft:#9aa6b4; --faint:#5c6773;
  --rule:#252c36; --band:#1c232c;
  --sw:#3fc2d4; --bk:#f0a63a; --rn:#ef6b9b; --ok:#4fc281; --warn:#e9a13b; --bad:#e56a5a;
}
:root[data-theme="light"]{
  --bg:#f4f5f7; --card:#ffffff; --ink:#12161c; --soft:#5a6472; --faint:#9aa4b2;
  --rule:#dfe3e9; --band:#e8ecf2;
  --sw:#1b9aaa; --bk:#e08a1e; --rn:#c8386f; --ok:#2f9e5f; --warn:#d98324; --bad:#c0392b;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;
  padding:0 max(18px,env(safe-area-inset-left)) 64px max(18px,env(safe-area-inset-right))}
header{padding:40px 0 20px;border-bottom:1px solid var(--rule)}
.eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--faint);margin:0 0 10px}
h1{font-family:var(--serif);font-weight:600;letter-spacing:-.02em;
  font-size:clamp(30px,6vw,46px);line-height:1.05;margin:0 0 10px}
.lede{color:var(--soft);margin:0;max-width:58ch}
h2{font-family:var(--serif);font-size:clamp(21px,3vw,27px);font-weight:600;
  letter-spacing:-.015em;margin:44px 0 4px}
.note{color:var(--soft);margin:0 0 16px;max-width:62ch;font-size:15px}
.card{background:var(--card);border:1px solid var(--rule);border-radius:4px;
  padding:16px 18px;box-shadow:var(--shadow)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:20px}
.tile strong{display:block;font-family:var(--mono);font-size:27px;font-variant-numeric:tabular-nums;
  letter-spacing:-.02em;line-height:1.1}
.tile span{display:block;margin-top:5px;font-size:11.5px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--faint)}
.tile em{font-style:normal;font-family:var(--mono);font-size:12px}
.up{color:var(--ok)} .down{color:var(--bad)} .flat{color:var(--faint)}
svg{display:block;width:100%;height:auto;overflow:visible}
.grid{stroke:var(--rule);stroke-width:1}
.ax{font:400 10.5px var(--mono);fill:var(--faint)}
.b{rx:1.5} .b.sw{fill:var(--sw)} .b.bk{fill:var(--bk)} .b.rn{fill:var(--rn)}
.ln{fill:none;stroke:var(--sw);stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
.dot{fill:var(--sw)}
.band{fill:var(--band)}
.pt{fill:var(--rn);opacity:.75}
.trend{stroke:var(--ink);stroke-width:1.4;stroke-dasharray:5 4;opacity:.5}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:10px;font-size:12.5px;color:var(--soft)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
table{width:100%;border-collapse:collapse;font-size:14.5px}
th{text-align:left;font:500 10.5px var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--faint);padding:0 10px 8px 0;border-bottom:1px solid var(--rule)}
td{padding:9px 10px 9px 0;border-bottom:1px solid var(--rule);vertical-align:top}
tr:last-child td{border-bottom:0}
td.n{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.muted{color:var(--faint);font-size:14px}
.tblwrap{overflow-x:auto}
.verdict{display:flex;gap:12px;align-items:flex-start;margin-top:18px;
  padding:14px 16px;border-radius:4px;border:1px solid var(--rule);background:var(--card);
  box-shadow:var(--shadow)}
.verdict b{font-size:17px;white-space:nowrap}
.verdict p{margin:2px 0 0;color:var(--soft);font-size:14.5px}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--rule);
  font-family:var(--mono);font-size:11.5px;color:var(--faint);
  display:flex;flex-wrap:wrap;gap:6px 16px;justify-content:space-between}
@media (max-width:560px){
  header{padding:26px 0 16px}
  h1{font-size:29px}
  .tiles{grid-template-columns:1fr 1fr;gap:8px}
  .tile strong{font-size:23px}
  .card{padding:13px 14px}
  h2{margin:34px 0 4px}
  table{font-size:13.5px}
  td,th{padding-right:6px}
}
"""


def tile(value, label, sub=""):
    return ('<div class="card tile"><strong>%s</strong>%s<span>%s</span></div>'
            % (value, (' <em class="%s">%s</em>' % sub) if sub else "", label))


def build():
    d = collect.build(weeks=16)
    t, b = d["today"], d["base"]
    o = []

    def delta_cls(cur, base, higher_better=True):
        if cur is None or base is None:
            return "flat", ""
        diff = cur - base
        good = (diff > 0) if higher_better else (diff < 0)
        cls = "up" if good else ("down" if abs(diff) > 0.01 else "flat")
        return cls, "%+.0f" % diff if abs(diff) >= 1 else "%+.1f" % diff

    o.append('<div class="wrap"><header>')
    o.append('<p class="eyebrow">Тренировки и восстановление · обновлено %s</p>' % d["generated"])
    o.append('<h1>До Эркнера <em style="font-style:italic;color:var(--rn)">%d дней</em></h1>' % d["days_to_race"])
    o.append('<p class="lede">IRONMAN 70.3 Erkner, %s. Страница собирается из данных Garmin '
             'и плана в TrainingPeaks, обновляется автоматически.</p>'
             % dt.date.fromisoformat(d["race"]).strftime("%d.%m.%Y"))

    # плитки
    o.append('<div class="tiles">')
    c, v = delta_cls(t["hrv"], b["hrv"], True)
    o.append(tile(t["hrv"] or "—", "HRV, мс", (c, "%s к базе" % v) if v else ""))
    c, v = delta_cls(t["rhr"], b["rhr"], False)
    o.append(tile(t["rhr"] or "—", "Пульс покоя", (c, "%s к базе" % v) if v else ""))
    o.append(tile("%.1f" % t["sleep"] if t["sleep"] else "—", "Сон, ч"))
    o.append(tile(t["rd"] or "—", "Готовность"))
    o.append('</div>')

    # сегодняшний светофор тем же движком, что и утренняя сводка в телеграме
    v = d.get("verdict")
    if v and v.get("verdict") in ("hard", "easy", "rest"):
        vv = v["verdict"]
        head = {"hard": "Можно жёстко", "easy": "Сегодня легко", "rest": "Сегодня отдых"}[vv]
        dot = {"hard": "🟢", "easy": "🟡", "rest": "🔴"}[vv]
        why = v.get("why") or ""
        o.append('<div class="verdict"><span style="font-size:19px">%s</span>'
                 '<div><b>%s</b><p>%s</p></div></div>' % (dot, head, esc(why)))
    o.append('</header>')

    # объём
    wk = d["weeks"]
    o.append('<h2>Объём по неделям</h2>')
    o.append('<p class="note">Шестнадцать недель, часы в неделю с разбивкой по видам спорта. '
             'Наведи на столбик, чтобы увидеть цифры.</p>')
    o.append('<div class="card">%s' % bars(wk))
    o.append('<div class="legend">'
             '<span><i style="background:var(--sw)"></i>плавание</span>'
             '<span><i style="background:var(--bk)"></i>велосипед</span>'
             '<span><i style="background:var(--rn)"></i>бег</span></div></div>')

    last4 = [w for w in wk[-4:]]
    o.append('<div class="tiles">')
    o.append(tile("%.1f" % (sum(w["h"] for w in last4) / 4), "Средняя неделя, ч"))
    o.append(tile(sum(w["hard"] for w in wk[-4:]), "Тяжёлых за 4 нед."))
    o.append(tile("%d" % sum(w["vert"] for w in wk[-4:]), "Набор за 4 нед., м"))
    o.append(tile("%.1f" % wk[-1]["h"], "Текущая неделя, ч"))
    o.append('</div>')

    # восстановление
    rec = d["recovery"]
    o.append('<h2>Восстановление</h2>')
    o.append('<p class="note">Девяносто дней. Серая полоса это коридор базы, '
             'по которому движок решает, каким будет сегодняшний день.</p>')
    o.append('<div class="card"><p class="note" style="margin:0 0 6px">HRV, мс</p>%s</div>'
             % line_chart([(r["d"][5:].replace("-", "."), r["hrv"]) for r in rec],
                          band=(b["hrv"] * 0.92, b["hrv"] * 1.08) if b["hrv"] else None,
                          label="HRV за 90 дней"))
    o.append('<div class="card" style="margin-top:10px">'
             '<p class="note" style="margin:0 0 6px">Пульс покоя</p>%s</div>'
             % line_chart([(r["d"][5:].replace("-", "."), r["rhr"]) for r in rec],
                          label="Пульс покоя за 90 дней"))

    # бег
    runs = d["runs"]
    if len(runs) >= 4:
        o.append('<h2>Бег: скорость на удар пульса</h2>')
        o.append('<p class="note">Главный показатель аэробного прогресса: сколько километров в час '
                 'приходится на один удар сердца. Чем выше точка, тем экономичнее бег. '
                 'Пунктир это тренд.</p>')
        o.append('<div class="card">%s</div>'
                 % scatter([(r["d"], r["eff"] * 1000, "%s, темп %d:%02d, пульс %d"
                             % (r["name"], r["pace"] // 60, r["pace"] % 60, r["hr"]))
                            for r in runs], ylab="%.1f"))
        f5, l5 = runs[:5], runs[-5:]
        o.append('<div class="tiles">')
        o.append(tile("%d:%02d" % (sum(r["pace"] for r in l5) // 5 // 60,
                                   sum(r["pace"] for r in l5) // 5 % 60), "Темп, последние 5"))
        o.append(tile("%d" % (sum(r["hr"] for r in l5) / 5), "При пульсе"))
        gain = (sum(r["eff"] for r in l5) / 5) / (sum(r["eff"] for r in f5) / 5) - 1
        o.append(tile("%+.0f%%" % (gain * 100), "Экономичность к началу"))
        o.append('</div>')

    # плавание
    sw = d["swims"]
    if len(sw) >= 4:
        o.append('<h2>Плавание: гребков на 50 метров</h2>')
        o.append('<p class="note">Цель тренера на сезон. Чем ниже, тем длиннее гребок. '
                 'Считается отдельно для 25 и 50 метров: в разных бассейнах цифры несопоставимы.</p>')
        for pool in (50, 25):
            g = [s for s in sw if s["pool"] == pool]
            if len(g) < 3:
                continue
            avg = sum(s["per50"] for s in g) / len(g)
            o.append('<div class="card" style="margin-bottom:10px">'
                     '<p class="note" style="margin:0 0 6px">Бассейн %d м · среднее %.1f гребка</p>%s</div>'
                     % (pool, avg, scatter([(s["d"], s["per50"], "%d м" % s["m"]) for s in g],
                                           ylab="%.0f")))

    # план
    if d["plan"]:
        o.append('<h2>Что дальше</h2>')
        o.append('<div class="card tblwrap"><table><thead><tr><th>Дата</th><th>Сессия</th><th>План</th></tr></thead><tbody>')
        for p in d["plan"]:
            day = dt.date.fromisoformat(p["d"])
            wd = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"][day.weekday()]
            o.append('<tr><td class="n">%s %d.%02d</td><td>%s</td><td class="n">%s</td></tr>'
                     % (wd, day.day, day.month, esc(p["s"]), esc(p["t"] or "—")))
        o.append('</tbody></table></div>')

    # год
    y = d["year"]
    o.append('<h2>За последние 12 месяцев</h2>')
    o.append('<div class="tiles">')
    for key, name in (("swim", "Плавание"), ("bike", "Велосипед"), ("run", "Бег")):
        if key in y:
            o.append(tile("%d ч" % y[key]["h"], name, ("flat", "%d трен." % y[key]["n"])))
    o.append(tile("%d ч" % sum(v["h"] for v in y.values()), "Всего"))
    o.append('</div>')

    o.append('<footer><span>Данные Garmin Connect и TrainingPeaks</span>'
             '<span>обновлено %s</span></footer></div>' % d["generated"])
    return "".join(o)


def main():
    body = build()
    html = ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            '<meta name="robots" content="noindex, nofollow">\n'
            '<title>Тренировки и восстановление</title>\n'
            '<meta name="theme-color" content="#f4f5f7" media="(prefers-color-scheme: light)">\n'
            '<meta name="theme-color" content="#0e1116" media="(prefers-color-scheme: dark)">\n'
            '<style>%s</style>\n</head>\n<body>\n%s\n</body>\n</html>\n' % (CSS, body))
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html: %d байт" % len(html))


if __name__ == "__main__":
    main()
