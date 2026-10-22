"""
Mo phong nhieu khung: dieu kien tren H1, tim entry tren khung nho (M15 / M5).
Chay theo tung nen khung nho -> duong gia trong nen H1 sat thuc te hon ban H1.

mode:
  "h1sig"  : tin hieu goc (MA do H1 tao dinh > 60 / day < 40), vao lenh o nen khung nho dau tien cua nen H1 moi
  "setup"  : H1 chi la dieu kien chuan bi (MA do nen H1 vua dong < 40 -> cho BUY, > 60 -> cho SELL),
             trigger tren khung nho moi vao lenh
trigger (khung nho, xet nen vua dong):
  "rsi"    : RSI14 cat len 30 (BUY) / cat xuong 70 (SELL)
  "ma"     : MA do (SMA14 cua RSI14) khung nho tao day < 40 (BUY) / dinh > 60 (SELL)
  "break"  : gia dong cua vuot dinh (BUY) / thung day (SELL) cua 5 nen truoc
Dong ro: tin hieu NGUOC chieu cua chinh he thong (dong ro cu roi vao lenh moi), SL ca ro, nghi cuoi tuan.
P/L tinh bang USC (tai khoan cent, 1 lot = 100 oz).
"""
from datetime import timedelta
from bt_rsi_base_h1_xau import load, indicators, paused, MULTS, CONTRACT

STEP = 5.0


def ema(closes, n):
    out, k, e = [], 2 / (n + 1), closes[0]
    for c in closes:
        e += k * (c - e)
        out.append(e)
    return out


class Data:
    def __init__(self, h1_path, ltf_path):
        self.h1 = load(h1_path)
        self.ltf = load(ltf_path)
        h1c = [r[4] for r in self.h1]
        _, _, _, self.h1_ma = indicators(h1c)
        self.h1_close = h1c
        self.h1_ema = {n: ema(h1c, n) for n in (800,)}
        self.h1_idx = {r[0]: i for i, r in enumerate(self.h1)}
        lc = [r[4] for r in self.ltf]
        _, _, self.l_rsi, self.l_ma = indicators(lc)
        self.l_close = lc
        # nen H1 chua nen khung nho j
        self.map = []
        for t, *_ in self.ltf:
            hk = t.replace(minute=0, second=0)
            self.map.append(self.h1_idx.get(hk))


def run(d, base_lot=0.1, spread=0.30, deposit=500000, sl=125, swap=40, mode="setup", trigger="rsi",
        trend=None, step=STEP, mults=MULTS, sig_high=60.0, sig_low=40.0, start=None, end=None,
        exit_h1=False):
    """exit_h1: dong ro theo tin hieu NGUOC cua H1 goc (dinh/day MA do), khong theo trigger khung nho."""
    pnl = lambda lot, diff: lot * CONTRACT * diff
    bal, pos, pend, side, basket = 0.0, [], [], None, None
    baskets = []
    peak = max_dd_pct = 0.0
    min_eq = 0.0
    blown = None
    blocked = {True: False, False: False}   # sau SL: chan cung chieu den khi setup ket thuc
    last_h = None
    L, H1 = d.ltf, d.h1
    last_j = 30

    def floating(bid):
        return sum(pnl(lot, (bid - p) if b else (p - bid - spread)) for b, lot, p in pos)

    def close_all(bid, t, why):
        nonlocal bal, pos, pend, side, basket
        r = floating(bid)
        bal += r
        if basket:
            basket.update(close_t=t, pnl=basket["pnl"] + r, why=why)
            baskets.append(basket)
        pos, pend, side, basket = [], [], None, None

    def mark(bid, t):
        nonlocal peak, max_dd_pct, min_eq, blown
        fl = floating(bid)
        eq = bal + fl
        if basket and fl < basket["worst"]:
            basket["worst"] = fl
        peak = max(peak, eq)
        min_eq = min(min_eq, eq)
        max_dd_pct = max(max_dd_pct, (peak - eq) / (deposit + peak) * 100)
        if pos and deposit + eq <= 0:
            close_all(bid, t, "STOP OUT")
            blown = t

    def open_basket(is_buy, o, t):
        nonlocal pos, pend, side, basket
        entry = o + spread if is_buy else o
        side = is_buy
        pos = [[is_buy, base_lot, entry]]
        pend = [[entry - step * k if is_buy else entry + step * k, base_lot * m] for k, m in enumerate(mults, 1)]
        basket = dict(open_t=t, buy=is_buy, entry=entry, worst=0.0, filled=0, pnl=0.0)

    def trend_ok(h, is_buy):
        if trend is None:
            return True
        return (d.h1_close[h - 1] > d.h1_ema[trend][h - 1]) == is_buy

    for j in range(30, len(L)):
        t, o, hi, lo, c = L[j]
        if (start and t < start) or (end and t >= end):
            continue
        if blown:
            break
        last_j = j
        h = d.map[j]
        if h is None or h < 40:
            continue

        if t.minute == 0 and t.hour == 0 and pos and swap:
            fee = swap * sum(lot for _, lot, _ in pos) * (3 if t.weekday() == 3 else 1)
            bal -= fee
            basket["pnl"] -= fee

        if paused(t):
            if pos or pend:
                close_all(o, t, "cuoi tuan")
            continue

        # --- tin hieu
        sig_buy = sig_sell = False
        h1_buy = h1_sell = False
        if h != last_h:
            v0, v1, v2 = d.h1_ma[h - 1], d.h1_ma[h - 2], d.h1_ma[h - 3]
            h1_sell = v1 > v0 and v1 > v2 and v1 > sig_high
            h1_buy = v1 < v0 and v1 < v2 and v1 < sig_low
        if mode == "h1sig":
            if h != last_h:
                v0, v1, v2 = d.h1_ma[h - 1], d.h1_ma[h - 2], d.h1_ma[h - 3]
                sig_sell = v1 > v0 and v1 > v2 and v1 > sig_high
                sig_buy = v1 < v0 and v1 < v2 and v1 < sig_low
        else:
            m = d.h1_ma[h - 1]
            setup_buy, setup_sell = m < sig_low, m > sig_high
            if not setup_buy:
                blocked[True] = False
            if not setup_sell:
                blocked[False] = False
            if setup_buy or setup_sell:
                if trigger == "rsi":
                    r0, r1 = d.l_rsi[j - 1], d.l_rsi[j - 2]
                    tb, ts = r1 <= 30 < r0, r1 >= 70 > r0
                elif trigger == "ma":
                    v0, v1, v2 = d.l_ma[j - 1], d.l_ma[j - 2], d.l_ma[j - 3]
                    tb = v1 < v0 and v1 < v2 and v1 < 40
                    ts = v1 > v0 and v1 > v2 and v1 > 60
                else:  # break
                    tb = d.l_close[j - 1] > max(L[k][2] for k in range(j - 6, j - 1))
                    ts = d.l_close[j - 1] < min(L[k][3] for k in range(j - 6, j - 1))
                sig_buy, sig_sell = setup_buy and tb, setup_sell and ts
        last_h = h

        ex_buy, ex_sell = (h1_buy, h1_sell) if exit_h1 else (sig_buy, sig_sell)
        if side is not None and ((side and ex_sell) or (not side and ex_buy)):
            close_all(o, t, "dao chieu")
        if side is None and (sig_buy or sig_sell):
            is_buy = sig_buy
            if trend_ok(h, is_buy) and not blocked[is_buy]:
                open_basket(is_buy, o, t)

        # --- duong gia trong nen khung nho
        path = [o, lo, hi, c] if c >= o else [o, hi, lo, c]
        mark(o, t)
        for a, b in zip(path, path[1:]):
            if blown or side is None:
                break
            adverse = (b < a) if side else (b > a)
            if not adverse:
                mark(b, t)
                continue
            sl_px = None
            if sl is not None:
                sl_px = basket["entry"] - sl if side else basket["entry"] + sl - spread
                if (side and a <= sl_px) or (not side and a >= sl_px):
                    sl_px = a
                if (side and b > sl_px) or (not side and b < sl_px):
                    sl_px = None
                else:
                    b = sl_px
            still = []
            for lvl, lot in pend:
                if side and b + spread <= lvl:
                    pos.append([True, lot, min(lvl, a + spread)])
                    basket["filled"] += 1
                elif not side and b >= lvl:
                    pos.append([False, lot, max(lvl, a)])
                    basket["filled"] += 1
                else:
                    still.append([lvl, lot])
            pend = still
            mark(b, t)
            if sl_px is not None and pos:
                blocked[side] = mode != "h1sig"
                close_all(sl_px, t, "SL")
                break

    if pos:
        close_all(L[last_j][4], L[last_j][0], "con mo")
    return dict(profit=bal, max_dd_pct=max_dd_pct, min_eq=min_eq, blown=blown, baskets=baskets)
