"""
Y tuong MOI de tang lai / giam DD cho xau_trendline (ban EA hien tai, co loc tin My).
Lot goc 0.001 x 10 = 0.01 de chia nho lot (0.5x, 1.5x...).
Muc tieu: tang PnL/DD (DD 20% von = 600 USD tren 3000).
"""
from datetime import timedelta
from five_ideas import F, BASE, ALLOW, ev, news_block
from trendline_filters import both

A = both(ALLOW, news_block(30, fomc=True))
B = dict(BASE, lot=0.001)
U = 10.0          # 10 x 0.001 = 0.01


def wd(i):
    return (F.m15[i][0] + timedelta(hours=7, minutes=15)).weekday()


def hr(i):
    return (F.m15[i][0] + timedelta(hours=7, minutes=15)).hour


def last_win(bs):
    return bool(bs) and bs[-1][2] > 0


def run(name, allow=A, ctx=None, **kw):
    return ev(name, allow=allow, lot_ctx=ctx or (lambda i, d, bs, bal: U), **dict(B, **kw))


if __name__ == "__main__":
    print("=== goc ===")
    run("EA hien tai (lot 0.001x10)")
    print("=== 1) sau ro THANG giam lot / bo qua ===")
    for f in (0.0, 0.25, 0.5, 0.75):
        run(f"sau thang lot x{f}", ctx=(lambda f: lambda i, d, bs, bal: U * (f if last_win(bs) else 1.0))(f))
    for f in (1.5, 2.0):
        run(f"sau thua lot x{f}", ctx=(lambda f: lambda i, d, bs, bal: U * (1.0 if last_win(bs) else f))(f))
    print("=== 2) theo d ===")
    for x in (5, 8, 10):
        run(f"bo ro d < {x}", th=(x, 10.0, 50.0))
    for f in (0.5, 0.25):
        run(f"d < 10 lot x{f}", ctx=(lambda f: lambda i, d, bs, bal: U * (f if d < 10 else 1.0))(f))
    for m in (60.0, 80.0):
        run(f"keo SL toi da {m:.0f} (thay 50)", th=(3.0, 10.0, m))
    run("lot ti le d/20 (kep 0.5..2)", ctx=lambda i, d, bs, bal: U * min(2.0, max(0.5, d / 20)))
    run("lot rui ro deu 1/d (TB ~ goc)", ctx=lambda i, d, bs, bal: U * min(3.0, max(0.25, 10.0 / max(d, 3.0))))
    print("=== 3) thu / gio ===")
    run("bo thu 4", allow=both(A, lambda i, b: wd(i) != 2))
    run("bo 19-20h + 22h VN", allow=both(A, lambda i, b: hr(i) not in (19, 20, 22)))
    print("=== 4) kiem soat sut von (theo lai/lo da chot) ===")
    for dd_cut, f in ((300, 0.5), (500, 0.5), (300, 0.0)):
        def mk(dd_cut, f):
            st = {"peak": 0.0}
            def c(i, d, bs, bal):
                st["peak"] = max(st["peak"], bal)
                return U * (f if st["peak"] - bal >= dd_cut else 1.0)
            return c
        run(f"sut >= {dd_cut} tu dinh -> lot x{f}", ctx=mk(dd_cut, f))
    print("=== 5) ket hop ===")
    c_win = lambda i, d, bs, bal: U * (0.5 if last_win(bs) else 1.0)
    run("sau thang x0.5 + bo thu 4", allow=both(A, lambda i, b: wd(i) != 2), ctx=c_win)
    run("sau thang x0.5 + d<10 x0.5", ctx=lambda i, d, bs, bal: U * (0.5 if last_win(bs) else 1.0) * (0.5 if d < 10 else 1.0))
    run("sau thang x0.5 + d<10 x0.5 + bo thu 4", allow=both(A, lambda i, b: wd(i) != 2),
        ctx=lambda i, d, bs, bal: U * (0.5 if last_win(bs) else 1.0) * (0.5 if d < 10 else 1.0))
