"""
Tim them phuong an cho xau_trendline BAN CAI TIEN (SL toi da 100, bo thu 4, nua lot sau ro thang).
  python tl_all.py mc      -> 1) Monte Carlo DD
  python tl_all.py btc     -> 2) trendline tren BTC M15 + danh muc vang + BTC
  python tl_all.py entry   -> 3) vao lenh: dong pha H1, tick volume, vao bang limit hoi nhe
  python tl_all.py exit    -> 4) thoat lenh: dung theo gio, hoa von o RSI 60/40, cau truc limit
  python tl_all.py wf      -> 5) swap + walk-forward
"""
import bisect
import csv
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import bt_trendline as T
from tl_ideas import F, A, U, B, run, wd, last_win
from trendline_filters import both, sma
from trendline_rsi_exit import exit_map

noWed = both(A, lambda i, b: wd(i) != 2)
CW = lambda i, d, bs, bal: U * (0.5 if last_win(bs) else 1.0)
NEW = dict(allow=noWed, ctx=CW, th=(3.0, 10.0, 100.0))


def new(name, **kw):
    return run(name, **dict(NEW, **kw))


# ------------------------------------------------------------------ 1) Monte Carlo
def max_dd(seq):
    eq = peak = dd = 0.0
    for pnl, worst in seq:
        dd = max(dd, peak - (eq + worst))
        eq += pnl
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def mc():
    for name, kw in (("EA hien tai", {}), ("BAN CAI TIEN", NEW)):
        r, *_ = run(name, **kw)
        seq = [(b[2], b[6]) for b in r["baskets"]]
        base = max_dd(seq)
        rnd = random.Random(1)
        res = {"xao tron": [], "boc lai (co lap)": [], "boc theo khoi 20 ro": []}
        n = len(seq)
        for _ in range(3000):
            s = seq[:]
            rnd.shuffle(s)
            res["xao tron"].append(max_dd(s))
            res["boc lai (co lap)"].append(max_dd([seq[rnd.randrange(n)] for _ in range(n)]))
            blk = []
            while len(blk) < n:
                k = rnd.randrange(n - 20)
                blk.extend(seq[k:k + 20])
            res["boc theo khoi 20 ro"].append(max_dd(blk[:n]))
        print(f"   DD lich su (theo ro, gom lo noi) {base:.0f} USD")
        for k, v in res.items():
            v.sort()
            q = lambda p: v[int(p * (len(v) - 1))]
            print(f"   {k:<22} DD trung vi {q(.5):5.0f} | 90% {q(.9):5.0f} | 95% {q(.95):5.0f} | 99% {q(.99):5.0f} USD")


# ------------------------------------------------------------------ 2) BTC + danh muc
class FB:
    pass


def btc():
    path = T.ROOT + "BTCUSD_M15_202301010000_202610230400.csv"
    rows = T.load(path)
    G = FB()
    G.m5 = G.m15 = rows
    G.m15c = [r[4] for r in rows]
    hours = [(r[0] + timedelta(hours=7, minutes=15)).hour for r in rows]
    s34, s89 = sma(G.m15c, 34), sma(G.m15c, 89)
    wdb = [(r[0] + timedelta(hours=7, minutes=15)).weekday() for r in rows]
    allow = lambda i, b: hours[i] not in (3, 4, 5, 6, 7) and (s34[i] > s89[i]) == b and wdb[i] != 2
    ex = exit_map(G, rows, 15, 70, 30)
    sig = T.signals(rows, 10)
    out = {}
    print("BTC M15 2023-01 -> 2026-10, lot 0.01 BTC, spread 20, nguong d theo % gia (x20 so voi vang)")
    for k in (15, 20, 30):
        th = (3.0 * k, 10.0 * k, 100.0 * k)
        r = T.run("M15", rows, rows, *th, sl_bars=4, spread=20.0, lot=0.00001, sig=sig, allow=allow, L=10,
                  exit_at=ex, rev_mode="profit", rev_open=False, orders=[(0, 1), (0.33, 3)],
                  lot_ctx=lambda i, d, bs, bal: 10.0 * (0.5 if last_win(bs) else 1.0))
        ys = r["years"]
        print(f"  nguong x{k:<3} PnL {r['pnl']:+7.0f}  DD {r['dd']:6.0f}  PnL/DD {r['pnl'] / max(r['dd'], 1):5.2f}  "
              f"ro {r['n']}  win {r['win']:.0f}% | " + " ".join(f"{y % 100}:{ys.get(y, 0):+6.0f}" for y in sorted(ys)))
        out[k] = r
    # danh muc: vang ban cai tien + BTC (nguong x20), tu 2023
    g, *_ = new("vang ban cai tien")
    best = out[20]

    def daily(curve, t0):
        d = {}
        for t, eq in curve:
            if t >= t0:
                d[t.date()] = eq
        return d
    t0 = datetime(2023, 1, 3)
    gd, bd = daily(g["curve"], t0), daily(best["curve"], t0)
    g0 = next(iter(gd.values()))
    b0 = next(iter(bd.values()))
    days = sorted(set(gd) | set(bd))
    lg = lb = 0.0
    port, gs, bs_ = [], [], []
    for d in days:
        lg = gd.get(d, lg + g0) - g0 if d in gd else lg
        lb = bd.get(d, lb + b0) - b0 if d in bd else lb
        gs.append(lg); bs_.append(lb)
    # ty trong: BTC sao cho DD rieng bang DD vang
    w = (max_dd_curve(gs) / max(max_dd_curve(bs_), 1))
    port = [a + w * b for a, b in zip(gs, bs_)]
    rets_g = monthly(days, gs)
    rets_b = monthly(days, [w * x for x in bs_])
    ks = sorted(set(rets_g) & set(rets_b))
    corr = pearson([rets_g[k] for k in ks], [rets_b[k] for k in ks])
    print(f"\nDanh muc tu 2023 (BTC lot x{w:.2f} de DD rieng = DD vang), tuong quan thang = {corr:+.2f}")
    for name, s in (("chi vang", gs), ("chi BTC", [w * x for x in bs_]), ("vang + BTC", port)):
        dd = max_dd_curve(s)
        print(f"  {name:<12} lai {s[-1]:+7.0f}  DD {dd:6.0f}  lai/DD {s[-1] / max(dd, 1):5.2f}")


def max_dd_curve(s):
    peak = dd = 0.0
    for x in s:
        peak = max(peak, x)
        dd = max(dd, peak - x)
    return dd


def monthly(days, s):
    m, last = {}, 0.0
    for d, x in zip(days, s):
        m[(d.year, d.month)] = x
    out, prev = {}, 0.0
    for k in sorted(m):
        out[k] = m[k] - prev
        prev = m[k]
    return out


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


# ------------------------------------------------------------------ 3) vao lenh
def entry():
    new("BAN CAI TIEN")
    # dong pha H1: huong tin hieu trendline H1 gan nhat (da dong) cung chieu
    hb, hs, _ = T.signals(F.h1, 10)
    h1t = [r[0] + timedelta(hours=1) for r in F.h1]
    last_dir, d = [], None
    for i in range(len(F.h1)):
        if hb[i]:
            d = True
        elif hs[i]:
            d = False
        last_dir.append(d)
    def h1ok(i, b):
        te = F.m15[i][0] + timedelta(minutes=15)
        k = bisect.bisect_right(h1t, te) - 1
        return k >= 0 and last_dir[k] == b
    new("+ tin hieu trendline H1 gan nhat cung chieu", allow=both(noWed, h1ok))
    # tick volume nen pha
    tv = []
    with open(T.FILES["M15"]) as f:
        r = csv.reader(f, delimiter="\t")
        next(r)
        for row in r:
            tv.append(float(row[6]))
    tva = sma(tv, 20)
    for k in (1.0, 1.3, 1.6):
        new(f"+ tick volume nen pha >= {k} x TB20", allow=both(noWed, (lambda k: lambda i, b: tv[i] >= k * tva[i - 1])(k)))
    # vao bang limit hoi nhe thay vi market
    for p in (0.1, 0.2):
        new(f"vao bang limit hoi {int(p * 100)}% d (bo market)", orders=[(p, 1), (0.33, 3)])


# ------------------------------------------------------------------ 4) thoat lenh
def exits():
    new("BAN CAI TIEN")
    for h in (4, 8, 24):
        new(f"dung ro dang lo sau {h}h", time_stop=h * 60)
    for hi, lo in ((60, 40), (65, 35)):
        new(f"RSI cham {hi}/{lo} -> SL ve hoa von", be_map=exit_map(F, F.m15, 15, hi, lo))
    for name, od in (("M + L50 x3", [(0, 1), (0.5, 3)]), ("M + L33 x2", [(0, 1), (0.33, 2)]),
                     ("M + L25 x2 + L50 x2", [(0, 1), (0.25, 2), (0.5, 2)]), ("M + L33 x3 + L66 x1", [(0, 1), (0.33, 3), (0.66, 1)]),
                     ("M x2 + L33 x2", [(0, 2), (0.33, 2)])):
        new(f"cau truc {name}", orders=od)


# ------------------------------------------------------------------ 5) swap + walk-forward
def wf():
    for s in (0.0, 0.03, 0.06):
        new(f"BAN CUOI (L50 x3), swap {int(s * 100)}%/nam", swap_year=s, orders=[(0, 1), (0.5, 3)])
    print("\nWalk-forward: chi xet 2022-2024 de quyet dinh, roi xem 2025-2026")
    r0, *_ = run("goc (EA hien tai)")
    variants = {"bo thu 4": dict(allow=noWed), "nua lot sau thang": dict(ctx=CW), "SL toi da 100": dict(th=(3.0, 10.0, 100.0)), "limit 50% x3": dict(orders=[(0, 1), (0.5, 3)])}
    split = datetime(2025, 1, 1)
    def part(r):
        bs = r["baskets"]
        tr = [(b[2], b[6]) for b in bs if b[0] < split]
        te = [(b[2], b[6]) for b in bs if b[0] >= split]
        return sum(x for x, _ in tr), max_dd(tr), sum(x for x, _ in te), max_dd(te)
    p0 = part(r0)
    print(f"  goc: train lai {p0[0]:+.0f} DD {p0[1]:.0f} (lai/DD {p0[0] / p0[1]:.2f}) | test lai {p0[2]:+.0f} DD {p0[3]:.0f} (lai/DD {p0[2] / p0[3]:.2f})")
    chosen = {}
    for k, kw in variants.items():
        r, *_ = run(k, **kw)
        p = part(r)
        keep = p[0] / p[1] > p0[0] / p0[1]
        if keep:
            chosen.update(kw)
        print(f"  {k:<18}: train lai/DD {p[0] / p[1]:.2f} -> {'GIU' if keep else 'bo'} | test lai {p[2]:+.0f} DD {p[3]:.0f} (lai/DD {p[2] / p[3]:.2f})")
    r, *_ = run("bo chon tu train", **chosen)
    p = part(r)
    print(f"  => bo chon tu 2022-24 {list(k for k in variants if all(chosen.get(a) is v for a, v in variants[k].items()))}: "
          f"test 2025-26 lai {p[2]:+.0f} DD {p[3]:.0f} (lai/DD {p[2] / p[3]:.2f}) vs goc {p0[2] / p0[3]:.2f}")


if __name__ == "__main__":
    {"mc": mc, "btc": btc, "entry": entry, "exit": exits, "wf": wf}[sys.argv[1]]()
