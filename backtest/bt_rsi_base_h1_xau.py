"""
Backtest mo phong rsi_base_h1_xau.mq5 (chi lenh EA TU VAO theo tin hieu, khong co lenh tay)
tren du lieu nen H1 xuat tu MT5 (gio server = GMT+0).

Gia dinh:
- Gia trong file la BID. ASK = BID + spread co dinh.
- Duong gia trong 1 nen: O -> L -> H -> C neu nen tang, O -> H -> L -> C neu nen giam.
- Dong ro: MA (SMA14 cua RSI14 Wilder) cua nen dang chay cham 50 -> giai nguoc ra gia nguong
  trong nen, dong tai gia nguong (hoac gia mo cua neu gap qua).
- Tai khoan cent: P/L tinh bang USC = lot * 100 oz * chenh gia * 100.
- Khong tinh swap / commission. Chay het von khi equity <= muc stop out.
"""
import csv
import sys
from datetime import datetime, timedelta

RSI_LEN, MA_LEN = 14, 14
CLOSE_LEVEL, SIG_HIGH, SIG_LOW = 50.0, 60.0, 40.0
STEP = 5.0
MULTS = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7]
CONTRACT = 100.0          # oz / lot
GMT_OFFSET, FRI_STOP, MON_START = 7, 17, 6


def load(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.reader(f, delimiter="\t")
        next(r)
        for d, t, o, h, l, c, *_ in r:
            rows.append((datetime.strptime(d + " " + t, "%Y.%m.%d %H:%M:%S"),
                         float(o), float(h), float(l), float(c)))
    return rows


def indicators(closes):
    n = len(closes)
    ag = [None] * n
    al = [None] * n
    rsi = [None] * n
    gains = losses = 0.0
    for i in range(1, RSI_LEN + 1):
        ch = closes[i] - closes[i - 1]
        gains += max(ch, 0.0)
        losses += max(-ch, 0.0)
    ag[RSI_LEN], al[RSI_LEN] = gains / RSI_LEN, losses / RSI_LEN
    for i in range(RSI_LEN + 1, n):
        ch = closes[i] - closes[i - 1]
        ag[i] = (ag[i - 1] * (RSI_LEN - 1) + max(ch, 0.0)) / RSI_LEN
        al[i] = (al[i - 1] * (RSI_LEN - 1) + max(-ch, 0.0)) / RSI_LEN
    for i in range(RSI_LEN, n):
        rsi[i] = 100.0 if al[i] == 0 else 100.0 - 100.0 / (1.0 + ag[i] / al[i])
    ma = [None] * n
    for i in range(RSI_LEN + MA_LEN - 1, n):
        ma[i] = sum(rsi[i - MA_LEN + 1:i + 1]) / MA_LEN
    return ag, al, rsi, ma


def threshold_price(i, closes, ag, al, rsi):
    """Gia BID trong nen i lam MA live = 50. Tra ve (gia, kieu): kieu 'always'/'never'/'price'."""
    need = CLOSE_LEVEL * MA_LEN - sum(rsi[i - MA_LEN + 1:i])   # RSI live can dat
    if need <= 0:
        return None, "always"      # MA luon >= 50 (dong BUY ngay), khong bao gio <= 50
    if need >= 100:
        return None, "never"       # MA luon <= 50
    rs = need / (100.0 - need)
    a0, l0 = ag[i - 1] * (RSI_LEN - 1), al[i - 1] * (RSI_LEN - 1)
    ch = rs * l0 - a0
    if ch < 0:
        ch = l0 - a0 / rs
    return closes[i - 1] + ch, "price"


def paused(t):
    loc = t + timedelta(hours=GMT_OFFSET)
    wd = loc.weekday()   # Mon=0..Sun=6
    return (wd == 4 and loc.hour >= FRI_STOP) or wd in (5, 6) or (wd == 0 and loc.hour < MON_START)


def run(rows, base_lot, spread, deposit=None, stop_out=0.0, start=None, end=None, log=None, step=STEP, sl=None,
        mults=MULTS, swap=0.0, reverse=False,
        sig_high=SIG_HIGH, sig_low=SIG_LOW, allow=None, weekend=True, gap_probe=(),
        vol=None, k_step=None, sl_mult=25.0, atr_ref=None):
    """deposit=None -> von vo han, chi do duong equity. Tra ve dict ket qua.
    sl: cat lo ca ro khi gia di nguoc qua sl gia tinh tu gia vao lenh goc (None = tat).
    swap: USC tru moi lot moi dem (so duong = bi tru), dem thu 4 tinh x3.
    reverse: True -> bo dong ro theo MA 50; chi dong khi co tin hieu NGUOC chieu roi vao lenh moi.
    allow(i, is_buy) -> bool: bo loc vao lenh (chi chan lenh MOI, tin hieu nguoc van dong ro).
    weekend: True = T6 17h dong het + nghi; False = giu nhu ngay thuong;
             ham policy(info) -> "close" | "cutpend" | "keep", goi 1 lan dau moi dot nghi,
             info = dict(side, entry, bid, adverse (gia di nguoc tu lenh goc), filled, floating); sau do chay nhu ngay thuong.
    vol/k_step: buoc luoi = k_step x vol[i-1] (vol = do bien dong, vd ATR TB), SL = sl_mult x buoc.
    atr_ref: lot = base_lot x atr_ref / vol[i-1] (giu so tien rui ro moi ro gan nhu khong doi).
    gap_probe: cac muc gap G (gia) gia dinh di NGUOC ro tai nen mo cua sau nghi (> 24h), chi do, khong doi ket qua."""
    closes = [r[4] for r in rows]
    ag, al, rsi, ma = indicators(closes)
    pnl_usc = lambda lot, diff: lot * CONTRACT * diff   # cent: 1 lot = 100 oz, P/L tinh bang USC

    bal = 0.0                 # loi nhuan da chot (USC), cong voi deposit
    pos = []                  # [is_buy, lot, price]
    pend = []                 # [level, lot]  (cung chieu voi basket)
    side = None               # True=BUY basket, False=SELL
    basket = None
    baskets = []
    min_eq, min_eq_t = 0.0, None
    peak, max_dd, max_dd_pct = 0.0, 0.0, 0.0   # sut tu dinh equity xuong day
    blown = None
    first = RSI_LEN + MA_LEN + 3
    last = first
    in_pause = False
    probe = {g: [] for g in gap_probe}

    def floating(bid):
        s = 0.0
        for b, lot, p in pos:
            s += pnl_usc(lot, (bid - p) if b else (p - (bid + spread)))
        return s

    def close_all(bid, t, why):
        nonlocal bal, pos, pend, side, basket
        realized = floating(bid)
        bal += realized
        if basket is not None:
            basket.update(close_t=t, pnl=basket.get("pnl", 0.0) + realized, why=why)
            baskets.append(basket)
        pos, pend, side, basket = [], [], None, None

    def mark(bid, t):
        nonlocal min_eq, min_eq_t, blown, peak, max_dd, max_dd_pct
        eq = bal + floating(bid)
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)
        if deposit is not None:
            max_dd_pct = max(max_dd_pct, (peak - eq) / (deposit + peak) * 100)
        if basket is not None:
            fl = floating(bid)
            if fl < basket["worst"]:
                basket["worst"], basket["worst_t"], basket["worst_px"] = fl, t, bid
        if eq < min_eq:
            min_eq, min_eq_t = eq, t
        if deposit is not None and pos and deposit + eq <= stop_out:
            if basket is not None:
                basket["blown"] = True
            close_all(bid, t, "STOP OUT")
            blown = t

    for i in range(first, len(rows)):
        t, o, h, l, c = rows[i]
        if (start and t < start) or (end and t >= end):
            continue
        if blown:
            break
        last = i
        if t.hour == 0 and pos and swap:
            fee = swap * sum(lot for _, lot, _ in pos) * (3 if t.weekday() == 3 else 1)
            bal -= fee
            basket["pnl"] = basket.get("pnl", 0.0) - fee

        if probe and pos and (t - rows[i - 1][0]).total_seconds() > 24 * 3600:
            pc = rows[i - 1][4]
            for g in probe:
                px = pc - g if side else pc + g
                hypo = floating(px) - spread * CONTRACT * sum(lot for _, lot in pend if (px + spread <= _ if side else px >= _))
                probe[g].append((t, bal + floating(pc), bal + hypo))   # (t, equity truoc gap, equity neu gap nguoc g)

        p_now = weekend is not False and paused(t)
        if weekend is True and p_now:
            if pos or pend:
                close_all(o, t, "cuoi tuan")
            continue
        if callable(weekend) and p_now and not in_pause and pos:
            adverse = (basket["entry"] - (o + spread)) if side else (o - basket["entry"])
            act = weekend(dict(side=side, entry=basket["entry"], bid=o, adverse=adverse,
                               filled=basket["filled"], floating=floating(o)))
            if act == "close":
                close_all(o, t, "cuoi tuan")
            elif act == "cutpend":
                pend = []
        in_pause = p_now

        thr, kind = threshold_price(i, closes, ag, al, rsi)

        def hit_close(bid):
            if reverse or side is None or not pos:
                return False
            if side:
                return kind == "always" or (kind == "price" and bid >= thr)
            return kind == "never" or (kind == "price" and bid <= thr)

        # --- tin hieu: nen i-1 vua dong (v0), i-2 (v1), i-3 (v2)
        v0, v1, v2 = ma[i - 1], ma[i - 2], ma[i - 3]
        sig_sell = v1 > v0 and v1 > v2 and v1 > sig_high
        sig_buy = v1 < v0 and v1 < v2 and v1 < sig_low
        if reverse and side is not None and ((side and sig_sell) or (not side and sig_buy)):
            close_all(o, t, "dao chieu")
        if side is None and not pos:
            if (sig_sell or sig_buy) and (allow is None or allow(i, sig_buy)) and not (callable(weekend) and p_now):
                is_buy = sig_buy
                live_blocked = not reverse and (
                    (is_buy and (kind == "always" or (kind == "price" and o >= thr))) or
                    (not is_buy and (kind == "never" or (kind == "price" and o <= thr))))
                if not live_blocked:
                    entry = o + spread if is_buy else o
                    side = is_buy
                    st, b_sl, lot0 = step, sl, base_lot
                    if vol is not None:
                        if k_step is not None:
                            st = k_step * vol[i - 1]
                            b_sl = sl_mult * st if sl is not None else None
                        if atr_ref is not None:
                            lot0 = max(0.01, round(base_lot * atr_ref / vol[i - 1], 2))
                    pos = [[is_buy, lot0, entry]]
                    pend = [[entry - st * k if is_buy else entry + st * k, lot0 * m]
                            for k, m in enumerate(mults, 1)]
                    basket = dict(open_t=t, buy=is_buy, entry=entry, worst=0.0, worst_t=t,
                                  worst_px=o, filled=0, blown=False, sl=b_sl, step=st, lot=lot0)

        # --- di theo duong gia trong nen
        path = [o, l, h, c] if c >= o else [o, h, l, c]
        if hit_close(o):
            close_all(o, t, "MA 50")
        mark(o, t)
        for a, b in zip(path, path[1:]):
            if blown:
                break
            if side is None:
                continue
            down = b < a
            if (side and down) or (not side and not down):
                # chieu bat loi -> khop limit, roi cat lo neu cham moc SL
                sl_px = None
                if basket["sl"] is not None:
                    sl_px = basket["entry"] - basket["sl"] if side else basket["entry"] + basket["sl"] - spread
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
                    close_all(sl_px, t, "SL")
                    break
            else:
                mark(a, t)
                if hit_close(b):
                    px = a if kind != "price" else (max(a, thr) if side else min(a, thr))
                    close_all(px, t, "MA 50")
                mark(b, t)

    if pos:
        fl = floating(rows[last][4])   # danh gia theo nen cuoi cung duoc chay, khong phai cuoi file
        bal += fl
        if basket is not None:
            basket.update(close_t=rows[last][0], pnl=fl, why="con mo")
            baskets.append(basket)
    return dict(profit=bal, min_eq=min_eq, min_eq_t=min_eq_t, blown=blown, baskets=baskets,
                max_dd=max_dd, max_dd_pct=max_dd_pct, probe=probe)


if __name__ == "__main__":
    rows = load(sys.argv[1])
    print(rows[0][0], "->", rows[-1][0], len(rows), "nen")
