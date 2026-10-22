"""
Thu tat ca to hop them / bot cac yeu to (lot 0.1 cent, von $5k, spread 0.30, swap 40) va xep hang.

Trendline (3 cach, deu chi dung nen H1 DA DONG):
  reg N   : hoi quy tuyen tinh N nen gan nhat, doc > 0 -> chi BUY, doc < 0 -> chi SELL
  swing k : trendline noi 2 dinh/day swing gan nhat (fractal k nen moi ben).
            BUY chi khi 2 day gan nhat di len (higher low) va gia tren duong noi 2 day.
            SELL chi khi 2 dinh gan nhat di xuong (lower high) va gia duoi duong noi 2 dinh.
  brk k   : xac nhan pha trendline nguoc: BUY chi khi gia da vuot len duong noi 2 dinh gan nhat
            (neu 2 dinh do dang di xuong), SELL tuong tu voi 2 day. Khong co trendline nguoc -> cho vao.
"""
import itertools
import sys
from datetime import datetime
from bt_rsi_base_h1_xau import load, run, MULTS

rows = load('../XAUUSD_H1_202201022300_202610220100.csv')
closes = [r[4] for r in rows]
highs = [r[2] for r in rows]
lows = [r[3] for r in rows]
N = len(rows)
D, LOT, SPREAD, SWAP = 5000 * 100, 0.1, 0.30, 40
SPLIT = datetime(2025, 1, 1)


def ema(n):
    out, k, e = [], 2 / (n + 1), closes[0]
    for c in closes:
        e += k * (c - e)
        out.append(e)
    return out


def reg_slope(n):
    """doc hoi quy cua n gia dong cua ket thuc tai moi nen (truot, O(N))."""
    out = [0.0] * N
    xs = sum(range(n)); xx = sum(x * x for x in range(n))
    den = n * xx - xs * xs
    sy = sum(closes[:n]); sxy = sum(x * closes[x] for x in range(n))
    out[n - 1] = (n * sxy - xs * sy) / den
    for i in range(n, N):
        sxy = sxy - (sy - closes[i - n]) + (n - 1) * closes[i]
        sy = sy - closes[i - n] + closes[i]
        out[i] = (n * sxy - xs * sy) / den
    return out


def pivots(k):
    """last2_hi[i] / last2_lo[i]: 2 swing gan nhat da XAC NHAN tai nen i: ((p1, y1), (p2, y2))"""
    hi2, lo2 = [None] * N, [None] * N
    hs, ls = [], []
    for i in range(N):
        p = i - k
        if p >= k:
            if highs[p] == max(highs[p - k:p + k + 1]):
                hs.append((p, highs[p]))
            if lows[p] == min(lows[p - k:p + k + 1]):
                ls.append((p, lows[p]))
        hi2[i] = (hs[-2], hs[-1]) if len(hs) >= 2 else None
        lo2[i] = (ls[-2], ls[-1]) if len(ls) >= 2 else None
    return hi2, lo2


def line_at(two, x):
    (p1, y1), (p2, y2) = two
    return y1 + (y2 - y1) * (x - p1) / (p2 - p1)


E800 = ema(800)
REG = {n: reg_slope(n) for n in (240, 480)}
PIV = {k: pivots(k) for k in (3, 10)}


def f_ema(i, buy):
    return (closes[i - 1] > E800[i - 1]) == buy


def f_reg(n):
    r = REG[n]
    return lambda i, buy: (r[i - 1] > 0) == buy


def f_swing(k):
    hi2, lo2 = PIV[k]

    def f(i, buy):
        j = i - 1
        if buy:
            two = lo2[j]
            return two is not None and two[1][1] > two[0][1] and closes[j] > line_at(two, j)
        two = hi2[j]
        return two is not None and two[1][1] < two[0][1] and closes[j] < line_at(two, j)
    return f


def f_brk(k):
    hi2, lo2 = PIV[k]

    def f(i, buy):
        j = i - 1
        if buy:
            two = hi2[j]   # trendline giam noi 2 dinh
            if two is None or two[1][1] >= two[0][1]:
                return True
            return closes[j] > line_at(two, j)
        two = lo2[j]
        if two is None or two[1][1] <= two[0][1]:
            return True
        return closes[j] < line_at(two, j)
    return f


def both(*fs):
    return lambda i, buy: all(f(i, buy) for f in fs)


TREND = {
    "khong loc": None,
    "EMA800": f_ema,
    "TL hoi quy 240": f_reg(240),
    "TL hoi quy 480": f_reg(480),
    "TL swing 10": f_swing(10),
    "TL pha 3": f_brk(3),
    "EMA800 + TL pha 3": both(f_ema, f_brk(3)),
    "EMA800 + TL hoi quy 480": both(f_ema, f_reg(480)),
}
GRID = {"luoi 1->7 x20": MULTS, "luoi 1->5 x10": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5], "khong luoi": []}
SL = {"SL125": 125, "SL150": 150, "khong SL": None}
EXIT = {"dao chieu": True, "MA50": False}
WEEKEND = {"nghi T7CN": True, "giu qua T7CN": False}
THR = {"60/40": (60, 40), "65/35": (65, 35)}


def evaluate(combo):
    tr, gr, sl, ex, wk, th = combo
    x = run(rows, LOT, SPREAD, deposit=D, swap=SWAP, allow=TREND[tr], mults=GRID[gr], sl=SL[sl],
            reverse=EXIT[ex], weekend=WEEKEND[wk], sig_high=THR[th][0], sig_low=THR[th][1])
    if x['blown']:
        return dict(combo=combo, blown=x['blown'])
    bs = x['baskets']
    p = x['profit'] / D * 100
    a = sum(b['pnl'] for b in bs if b['close_t'] < SPLIT) / D * 100
    yr, prev = [], 0
    for y in range(2022, 2027):
        cur = sum(b['pnl'] for b in bs if b['close_t'] < datetime(y + 1, 1, 1))
        yr.append((cur - prev) / (D + prev) * 100)
        prev = cur
    return dict(combo=combo, blown=None, p=p, dd=x['max_dd_pct'], ratio=p / max(x['max_dd_pct'], 0.5),
                a=a, b=p - a, n=len(bs), nsl=sum(b['why'] == 'SL' for b in bs), yr=yr)


if __name__ == "__main__":
    combos = list(itertools.product(TREND, GRID, SL, EXIT, WEEKEND, THR))
    res = []
    for k, c in enumerate(combos):
        res.append(evaluate(c))
        if k % 50 == 0:
            print(f"{k}/{len(combos)}", file=sys.stderr)
    import pickle
    pickle.dump(res, open("factor_results.pkl", "wb"))
    alive = [r for r in res if not r['blown']]
    print(f"Tong {len(res)} to hop, chay tai khoan {len(res) - len(alive)}")
