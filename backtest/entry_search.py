"""Do bo loc vao lenh cho che do dao chieu + SL 125, lot 0.1, von $5k, swap 40."""
from datetime import datetime
from bt_rsi_base_h1_xau import load, run

rows = load('../XAUUSD_H1_202201022300_202610220100.csv')
closes = [r[4] for r in rows]
D, LOT, SPREAD, SWAP = 5000 * 100, 0.1, 0.30, 40
BASE = dict(reverse=True, sl=125, swap=SWAP)
SPLIT = datetime(2025, 1, 1)


def ema(n):
    out, k, e = [], 2 / (n + 1), closes[0]
    for c in closes:
        e = e + k * (c - e)
        out.append(e)
    return out


def atr(n):
    tr = [rows[0][2] - rows[0][3]] + [max(rows[i][2], rows[i - 1][4]) - min(rows[i][3], rows[i - 1][4]) for i in range(1, len(rows))]
    out, a = [], tr[0]
    for x in tr:
        a = a + (x - a) / n
        out.append(a)
    return out


def sma(arr, n):
    out, s = [], 0.0
    for i, x in enumerate(arr):
        s += x - (arr[i - n] if i >= n else 0)
        out.append(s / min(i + 1, n))
    return out


EMA = {n: ema(n) for n in (200, 800, 1100)}
ATR = atr(14)
ATR_AVG = sma(ATR, 500)


def trend(n):      # chi BUY khi gia (nen vua dong) tren EMA n, SELL khi duoi
    e = EMA[n]
    return lambda i, buy: (closes[i - 1] > e[i - 1]) == buy


def slope(n, back=24):   # EMA n dang doc len -> chi BUY
    e = EMA[n]
    return lambda i, buy: (e[i - 1] > e[i - 1 - back]) == buy


def calm(k):       # ATR khong qua k lan trung binh 500 nen
    return lambda i, buy: ATR[i - 1] <= k * ATR_AVG[i - 1]


def both(*fs):
    return lambda i, buy: all(f(i, buy) for f in fs)


def report(name, **kw):
    x = run(rows, LOT, SPREAD, deposit=D, **BASE, **kw)
    if x['blown']:
        print(f"{name:34} | CHAY {x['blown']:%Y-%m-%d}")
        return
    bs = x['baskets']
    p = x['profit'] / D * 100
    a = sum(b['pnl'] for b in bs if b['close_t'] < SPLIT) / D * 100
    g = run(rows, LOT, SPREAD, mults=[], **{**BASE, 'sl': None}, **kw)['profit'] / D * 100
    print(f"{name:34} | {p:+5.0f}% | DD {x['max_dd_pct']:4.1f}% | loi/DD {p / x['max_dd_pct']:4.2f} | 22-24 {a:+4.0f}% | 25-26 {p - a:+4.0f}% | ro {len(bs):3} | khong luoi {g:+4.1f}%")


if __name__ == "__main__":
    report("goc (60/40, khong loc)")
    for hi, lo in ((65, 35), (70, 30), (55, 45)):
        report(f"nguong {hi}/{lo}", sig_high=hi, sig_low=lo)
    for n in (200, 800, 1100):
        report(f"thuan xu huong EMA{n} H1", allow=trend(n))
        report(f"doc EMA{n} H1 (24 nen)", allow=slope(n))
    for k in (1.5, 2.0, 2.5):
        report(f"ATR <= {k} x TB", allow=calm(k))
