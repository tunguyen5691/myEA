"""Loc xu huong MA34 / MA89 cho ban chot: MA34 > MA89 -> chi BUY, MA34 < MA89 -> chi SELL.
Thu EMA va SMA, khung M15 (nen vua dong) va H1 (nen H1 da dong gan nhat).
exit_filtered: tin hieu bi loc van duoc dung de dong ro dang loi (True) hay bo qua han (False)."""
from trendline_filters import ema, sma, both
from trendline_rsi_exit import Feat, SESS, TH, exit_map, f_hours, evaluate

F = Feat()
hours = f_hours(F, SESS["bo 03-07 VN"])
base = dict(L=10, exit_at=exit_map(F, F.m15, 15, 70, 30), rev_mode="profit", rev_open=False,
            orders=[(0, 1), (0.33, 3)], sl_bars=4)
m15c, h1c = F.m15c, F.h1c


def f_ma(fast, slow, on_h1):
    if on_h1:
        return lambda i, b: F.k[i] >= 0 and ((fast[F.k[i]] > slow[F.k[i]]) == b)
    return lambda i, b: (fast[i] > slow[i]) == b


evaluate(F, "ban chot (khong loc MA)", allow=hours, **base)
for kind, fn in (("EMA", ema), ("SMA", sma)):
    for tfn, closes, on_h1 in (("M15", m15c, False), ("H1", h1c, True)):
        f = f_ma(fn(closes, 34), fn(closes, 89), on_h1)
        for ef in (True, False):
            name = f"{kind}34>{kind}89 {tfn}" + ("" if ef else " bo han tin hieu loc")
            evaluate(F, name, allow=both(hours, f), exit_filtered=ef, **base)
