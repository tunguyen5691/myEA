"""
Tim bo loc cho xau_trendline khung M15 (bt_trendline.run).
Moi bo loc chi chan lenh MOI; tin hieu nguoc bi loc van dong ro cu (exit_filtered=True).
Chay:  python trendline_filters.py single   -> tung bo loc rieng le
       python trendline_filters.py combo    -> ghep cac bo loc tot
"""
import bisect
import math
import sys
from datetime import timedelta

from bt_trendline import FILES, GMT_OFFSET, load, run, signals

TH = (3.0, 10.0, 50.0)          # nguong d mac dinh EA
NO_LIM = (3.0, 1e9, 50.0)       # chi 1 lenh market


def ema(xs, n):
    out, k, e = [], 2 / (n + 1), xs[0]
    for x in xs:
        e += k * (x - e)
        out.append(e)
    return out


def reg_slope(xs, n):
    """Do doc hoi quy tuyen tinh n gia tri gan nhat (gia / nen)."""
    out = [0.0] * len(xs)
    sx = n * (n - 1) / 2
    sxx = (n - 1) * n * (2 * n - 1) / 6
    den = n * sxx - sx * sx
    sy = 0.0
    swy = 0.0                       # sum (j * y_j) theo chi so tuyet doi
    for i, y in enumerate(xs):
        sy += y
        swy += i * y
        if i >= n:
            sy -= xs[i - n]
            swy -= (i - n) * xs[i - n]
        if i >= n - 1:
            base = i - n + 1
            sxy_rel = swy - base * sy      # sum ((j-base) * y_j), x = 0..n-1
            out[i] = (n * sxy_rel - sx * sy) / den
    return out


def atr_rma(rows, n=14):
    out, a = [0.0] * len(rows), 0.0
    for i, (_, o, h, l, c) in enumerate(rows):
        tr = h - l if i == 0 else max(h - l, abs(h - rows[i - 1][4]), abs(l - rows[i - 1][4]))
        a = a + tr / n if i < n else (a * (n - 1) + tr) / n
        out[i] = a
    return out


def sma(xs, n):
    out, s = [0.0] * len(xs), 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        out[i] = s / min(i + 1, n)
    return out


def adx(rows, n=14):
    out = [0.0] * len(rows)
    tr_s = pdm_s = ndm_s = 0.0
    dx_s = 0.0
    for i in range(1, len(rows)):
        _, _, h, l, c = rows[i]
        _, _, ph, pl, pc = rows[i - 1]
        up, dn = h - ph, pl - l
        pdm = up if up > dn and up > 0 else 0.0
        ndm = dn if dn > up and dn > 0 else 0.0
        tr = max(h - l, abs(h - pc), abs(l - pc))
        tr_s = tr_s - tr_s / n + tr
        pdm_s = pdm_s - pdm_s / n + pdm
        ndm_s = ndm_s - ndm_s / n + ndm
        if tr_s <= 0:
            continue
        pdi, ndi = 100 * pdm_s / tr_s, 100 * ndm_s / tr_s
        dx = 100 * abs(pdi - ndi) / (pdi + ndi) if pdi + ndi else 0.0
        dx_s = dx_s + (dx - dx_s) / n
        out[i] = dx_s
    return out


class Feat:
    def __init__(self):
        self.m5 = load(FILES["M5"])
        self.m15 = load(FILES["M15"])
        self.h1 = load(FILES["H1"])
        self.sig = {}
        m15c = [r[4] for r in self.m15]
        h1c = [r[4] for r in self.h1]
        h1t = [r[0] for r in self.h1]
        # nen H1 da dong gan nhat tai luc nen M15 i dong
        self.k = []
        for r in self.m15:
            te = r[0] + timedelta(minutes=15)
            self.k.append(bisect.bisect_right(h1t, te - timedelta(hours=1)) - 1)
        self.h1c = h1c
        self.h1_ema = {n: ema(h1c, n) for n in (200, 400, 800)}
        self.h1_reg = {n: reg_slope(h1c, n) for n in (120, 240, 480)}
        self.m15c = m15c
        self.m15_ema = {n: ema(m15c, n) for n in (50, 200, 800)}
        a = atr_rma(self.m15)
        self.atr_ratio = [x / m if m else 1.0 for x, m in zip(a, sma(a, 960))]
        self.adx = adx(self.m15)
        self.hour = [(r[0] + timedelta(hours=GMT_OFFSET, minutes=15)).hour for r in self.m15]

    def signals(self, L=14, mult=1.0):
        key = (L, mult)
        if key not in self.sig:
            self.sig[key] = signals(self.m15, L, mult)
        return self.sig[key]


# --- cac bo loc: tra ve allow(i, is_buy)
def f_h1_ema(F, n):
    def ok(i, b):
        k = F.k[i]
        return k >= 0 and ((F.h1c[k] > F.h1_ema[n][k]) == b)
    return ok


def f_h1_reg(F, n):
    def ok(i, b):
        k = F.k[i]
        return k >= 0 and ((F.h1_reg[n][k] > 0) == b)
    return ok


def f_m15_ema(F, n):
    return lambda i, b: (F.m15c[i] > F.m15_ema[n][i]) == b


def f_m15_cross(F):
    return lambda i, b: (F.m15_ema[50][i] > F.m15_ema[200][i]) == b


def f_atr(F, x):
    return lambda i, b: F.atr_ratio[i] >= x


def f_adx(F, x):
    return lambda i, b: F.adx[i] >= x


def f_hours(F, hours):
    s = set(hours)
    return lambda i, b: F.hour[i] in s


def f_brk(F, x, L=14, mult=1.0):
    brk = F.signals(L, mult)[2]
    return lambda i, b: brk[i] >= x


def both(*fs):
    return lambda i, b: all(f(i, b) for f in fs)


def evaluate(F, name, allow=None, th=TH, L=14, mult=1.0, **kw):
    r = run("M15", F.m15, F.m5, *th, sig=F.signals(L, mult), allow=allow, L=L, mult=mult, **kw)
    ys = r["years"]
    pos = sum(1 for y in range(2022, 2027) if ys.get(y, 0) > 0)
    score = r["pnl"] / r["dd"] if r["dd"] else 0.0
    line = (f"{name:<34} PnL {r['pnl']:+6.0f} ({r['ret']:+5.0f}%)  DD {r['dd']:5.0f} ({r['dd_pct']:4.0f}%)  "
            f"PnL/DD {score:5.2f}  ro/th {r['per_month']:4.1f}  win {r['win']:3.0f}%  nam+ {pos}/5  | "
            + " ".join(f"{y % 100}:{ys.get(y, 0):+5.0f}" for y in range(2022, 2027)))
    print(line, flush=True)
    return r, score, pos


SESS = {
    "gio 14-23 VN": range(14, 24),
    "gio 14-02 VN": list(range(14, 24)) + [0, 1, 2],
    "gio 08-23 VN": range(8, 24),
    "bo 03-07 VN": [h for h in range(24) if h not in (3, 4, 5, 6, 7)],
}


def single(F):
    print("--- goc ---")
    evaluate(F, "goc (2 limit)")
    evaluate(F, "goc khong limit", th=NO_LIM)
    print("--- xu huong H1 ---")
    for n in (200, 400, 800):
        evaluate(F, f"H1 gia > EMA{n}", f_h1_ema(F, n))
    for n in (120, 240, 480):
        evaluate(F, f"H1 doc hoi quy {n}", f_h1_reg(F, n))
    print("--- xu huong M15 ---")
    for n in (200, 800):
        evaluate(F, f"M15 gia > EMA{n}", f_m15_ema(F, n))
    evaluate(F, "M15 EMA50 > EMA200", f_m15_cross(F))
    print("--- bien dong / suc manh ---")
    for x in (0.8, 1.0, 1.2):
        evaluate(F, f"ATR/ATR10ngay >= {x}", f_atr(F, x))
    for x in (20, 25, 30):
        evaluate(F, f"ADX >= {x}", f_adx(F, x))
    for x in (0.1, 0.25, 0.5):
        evaluate(F, f"pha >= {x} ATR", f_brk(F, x))
    print("--- gio ---")
    for k, hs in SESS.items():
        evaluate(F, k, f_hours(F, hs))
    print("--- tham so trendline ---")
    for L, m in ((10, 1.0), (20, 1.0), (14, 0.5), (14, 1.5)):
        evaluate(F, f"L={L} mult={m}", L=L, mult=m)


def combo(F):
    """Bo loc tot o vong single x kieu thoat lenh x co/khong limit x L."""
    no37 = SESS["bo 03-07 VN"]
    exits = {"-": {}, "BE1": {"be_r": 1.0}, "TR1": {"trail_r": 1.0}, "TR1.5": {"trail_r": 1.5},
             "TP2": {"tp_r": 2.0}, "TP3": {"tp_r": 3.0}}
    res = []
    for L in (10, 14):
        filt = {"-": None, "bo03-07": f_hours(F, no37), "ATR1.2": f_atr(F, 1.2),
                "pha0.5": f_brk(F, 0.5, L), "bo03-07+pha0.5": both(f_hours(F, no37), f_brk(F, 0.5, L)),
                "bo03-07+ATR1.0": both(f_hours(F, no37), f_atr(F, 1.0))}
        for fn, fa in filt.items():
            for xn, xk in exits.items():
                for limn, th in (("2lim", TH), ("0lim", NO_LIM)):
                    name = f"L{L} {fn} {xn} {limn}"
                    r, s, pos = evaluate(F, name, fa, th=th, L=L, **xk)
                    res.append((s, pos, r["pnl"], r["dd"], name))
    print("--- top 15 theo PnL/DD ---")
    for s, pos, pnl, dd, name in sorted(res, reverse=True)[:15]:
        print(f"{s:5.2f}  nam+ {pos}/5  PnL {pnl:+5.0f} DD {dd:4.0f}  {name}")
    print("--- top 15 theo so nam loi, roi PnL/DD ---")
    for s, pos, pnl, dd, name in sorted(res, key=lambda x: (x[1], x[0]), reverse=True)[:15]:
        print(f"{s:5.2f}  nam+ {pos}/5  PnL {pnl:+5.0f} DD {dd:4.0f}  {name}")


if __name__ == "__main__":
    F = Feat()
    mode = sys.argv[1] if len(sys.argv) > 1 else "single"
    {"single": single, "combo": combo}[mode](F)
