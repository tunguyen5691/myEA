"""Do on dinh cua loc MA nhanh > MA cham (M15) quanh cap 34/89, cho ca SMA va EMA (ban chot)."""
from trendline_filters import ema, sma, both
from trendline_rsi_exit import Feat, SESS, exit_map, f_hours, evaluate

F = Feat()
hours = f_hours(F, SESS["bo 03-07 VN"])
base = dict(L=10, exit_at=exit_map(F, F.m15, 15, 70, 30), rev_mode="profit", rev_open=False,
            orders=[(0, 1), (0.33, 3)], sl_bars=4)
PAIRS = [(21, 55), (30, 80), (34, 89), (40, 100), (50, 120), (34, 144)]
res = {}
for kind, fn in (("SMA", sma), ("EMA", ema)):
    cache = {}
    for a, b in PAIRS:
        fa = cache.setdefault(a, fn(F.m15c, a))
        fb = cache.setdefault(b, fn(F.m15c, b))
        f = (lambda x, y: (lambda i, buy: (x[i] > y[i]) == buy))(fa, fb)
        r, s, pos = evaluate(F, f"{kind}{a}>{kind}{b} M15", allow=both(hours, f), **base)
        res[(kind, a, b)] = (r["pnl"], r["dd"], pos)
print()
for kind in ("SMA", "EMA"):
    xs = [v for k, v in res.items() if k[0] == kind]
    print(f"{kind}: TB loi {sum(x[0] for x in xs)/len(xs)/30/4.8:5.1f}%/nam  TB DD {sum(x[1] for x in xs)/len(xs):5.0f}  "
          f"te nhat loi {min(x[0] for x in xs)/30/4.8:5.1f}%/nam  DD cao nhat {max(x[1] for x in xs):5.0f}")
