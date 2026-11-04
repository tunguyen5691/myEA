import tl_oos  # dung FILES tu M1 (07/2021-11/2026) va in 5 cau hinh cu
from datetime import datetime
from tl_ideas import run, last_win, U
from tl_oos import noWed
r, *_ = run("BAN CUOI (du lieu M1)", allow=noWed, ctx=lambda i, d, bs, bal: U * (0.5 if last_win(bs) else 1.0),
            th=(3.0, 10.0, 100.0), orders=[(0, 1), (0.5, 3)])
bs = r["baskets"]
print("     -> NGOAI MAU: 2021H2 %+.0f | 22/10-04/11/2026 %+.0f" % (
    sum(b[2] for b in bs if b[0] < datetime(2022, 1, 1)), sum(b[2] for b in bs if b[0] >= datetime(2026, 10, 22))))
print("     theo nam:", {y: round(v) for y, v in sorted(r["years"].items())})
