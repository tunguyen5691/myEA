"""Kiem tra ngoai mau (2021H2 + 22/10-04/11/2026) bang M5/M15/H1 dung tu file M1 07/2021-11/2026."""
import os
import tempfile
from datetime import date, datetime
import bt_trendline as T
from bt_rsi_base_h1_xau import load

SCR = os.path.join(tempfile.gettempdir(), "xau_from_m1")   # M5/M15/H1 dung tu M1 (cache)
os.makedirs(SCR, exist_ok=True)
M1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "XAUUSD_M1_202011040000_202611040749.csv")


def build():
    rows = [r for r in load(M1) if r[0] >= datetime(2021, 6, 1)]
    for name, m in (("M5", 5), ("M15", 15), ("H1", 60)):
        p = os.path.join(SCR, f"xau_{name}_from_m1.csv")
        T.FILES[name] = p
        if os.path.exists(p):
            continue
        out = []
        for t, o, h, l, c in rows:
            k = t.replace(minute=(t.minute // m) * m) if m < 60 else t.replace(minute=0)
            if out and out[-1][0] == k:
                _, o0, h0, l0, _ = out[-1]
                out[-1] = (k, o0, max(h0, h), min(l0, l), c)
            else:
                out.append((k, o, h, l, c))
        with open(p, "w") as f:
            f.write("<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n")
            for t, o, h, l, c in out:
                f.write(f"{t:%Y.%m.%d}\t{t:%H:%M:%S}\t{o:.3f}\t{h:.3f}\t{l:.3f}\t{c:.3f}\t0\t0\t0\n")


build()
T.HOLIDAYS[:0] = [date(2021, 11, 25), date(2021, 12, 24), date(2021, 12, 25)]
from tl_ideas import A, U, run, wd, last_win   # noqa: E402  (Feat dung FILES moi)
from trendline_filters import both            # noqa: E402

noWed = both(A, lambda i, b: wd(i) != 2)
cw = lambda i, d, bs, bal: U * (0.5 if last_win(bs) else 1.0)
for name, kw in (("EA hien tai", {}),
                 ("SL100", dict(th=(3.0, 10.0, 100.0))),
                 ("bo thu 4", dict(allow=noWed)),
                 ("sau thang x0.5", dict(ctx=cw)),
                 ("SL100 + bo thu 4 + sau thang x0.5", dict(allow=noWed, ctx=cw, th=(3.0, 10.0, 100.0)))):
    r, *_ = run(name, **kw)
    bs = r["baskets"]
    h21 = sum(b[2] for b in bs if b[0] < datetime(2022, 1, 1))
    late = sum(b[2] for b in bs if b[0] >= datetime(2026, 10, 22))
    print(f"     -> NGOAI MAU: 2021H2 {h21:+.0f}  |  22/10-04/11/2026 {late:+.0f}")
