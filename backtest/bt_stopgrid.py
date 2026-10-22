"""
Mo phong xau_new.mq5 (luoi lenh stop 2 chieu + trailing) tren nen M5 / M15 (gio server GMT+0, gia = BID).

Gia dinh:
- Duong gia trong 1 nen: O -> L -> H -> C (nen tang) / O -> H -> L -> C (nen giam). Giua 4 diem gia di 1 chieu,
  nen moi su kien (khop stop, cham SL, doi trailing) tinh chinh xac theo duong do. Nen that co nhieu lan
  dao chieu hon -> ket qua THIEN LAC QUAN cho chien luoc nhieu lenh nho nay.
- Spread co dinh, truot gia `slip` (gia) tinh bat loi cho moi lan khop stop va moi lan cham SL.
- Tai khoan USD thuong: 0.01 lot = 1 oz -> 1 gia = $1. Stop out khi equity / margin < stop_out.
"""
import random
from datetime import timedelta
from bt_rsi_base_h1_xau import load

CONTRACT = 100.0


def fine_path(o, h, l, c, n, rng):
    """Duong gia n buoc kieu Brownian bridge, ep di qua dung O (dau), C (cuoi), cham dung H va L."""
    w, acc = [0.0], 0.0
    for _ in range(n):
        acc += rng.gauss(0.0, 1.0)
        w.append(acc)
    p = [o + (c - o) * k / n + (w[k] - w[n] * k / n) for k in range(n + 1)]
    top, bot = max(o, c), min(o, c)
    hi0, lo0 = max(p), min(p)
    if h > top and hi0 <= top:
        p[rng.randrange(1, n)] = hi0 = top + 1e-9
    if l < bot and lo0 >= bot:
        k = rng.randrange(1, n)
        if p[k] > top:
            k = (k % (n - 1)) + 1
        p[k] = lo0 = bot - 1e-9
    out = []
    for x in p:
        if x > top:
            x = top + (x - top) * (h - top) / (hi0 - top)
        elif x < bot:
            x = bot - (bot - x) * (bot - l) / (bot - lo0)
        out.append(x)
    out[0], out[-1] = o, c
    return out


def local(t, off=7):
    return t + timedelta(hours=off)


def run(rows, grid_min=15, levels=20, step=0.5, lot=0.01, sl=1.0, trail_start=1.0, trail_dist=1.0,
        spread=0.30, slip=0.0, deposit=500.0, day_loss=10.0, night=(3, 6), fri_stop=22, mon_start=6,
        leverage=500, stop_out=0.5, start=None, end=None, fine=0, seed=1):
    """fine > 0: thay duong O-L-H-C bang fine_path n=fine buoc (gia lap nhieu lan dao chieu trong nen)."""
    rng = random.Random(seed)
    pnl = lambda b, op, ex, lt: (ex - op if b else op - ex) * lt * CONTRACT
    bal = deposit
    pos = []          # [is_buy, open, sl, lot]
    bstops, sstops = [], []
    peak = deposit
    max_dd = 0.0
    day_key, day_eq, day_stop = None, deposit, False
    trades = []       # (t, pnl)
    blown = None
    daily = {}

    def eq_at(bid):
        return bal + sum(pnl(b, op, bid if b else bid + spread, lt) for b, op, _, lt in pos)

    def margin(bid):
        return sum(lt * CONTRACT * bid for *_, lt in pos) / leverage

    def close(p, exit_px, t):
        nonlocal bal
        r = pnl(p[0], p[1], exit_px, p[3])
        bal += r
        trades.append((t, r))

    def close_all(bid, t):
        nonlocal pos
        for p in pos:
            close(p, bid if p[0] else bid + spread, t)
        pos = []

    def check(bid, t):
        """equity, DD, lo trong ngay, stop out tai 1 diem gia"""
        nonlocal peak, max_dd, day_stop, blown, bstops, sstops
        eq = eq_at(bid)
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak * 100)
        if pos and margin(bid) > 0 and eq / margin(bid) < stop_out:
            close_all(bid, t)
            bstops, sstops = [], []
            if bal <= deposit * 0.05:
                blown = t
            return
        if day_loss and not day_stop and (day_eq - eq) / day_eq * 100 >= day_loss:
            close_all(bid, t)
            bstops, sstops = [], []
            day_stop = True

    def segment(a, b, t):
        nonlocal pos, bstops, sstops
        if b > a:      # gia di len
            still = []
            for lv in bstops:
                if b + spread >= lv:
                    op = max(lv, a + spread) + slip
                    pos.append([True, op, lv - sl if sl else 0.0, lot])   # SL tinh tu gia dat lenh, nhu EA
                else:
                    still.append(lv)
            bstops = still
            keep = []
            for p in pos:
                if not p[0] and p[2] and b + spread >= p[2]:
                    close(p, max(p[2], a + spread) + slip, t)
                else:
                    keep.append(p)
            pos = keep
            for p in pos:
                if p[0] and b - p[1] >= trail_start:
                    p[2] = max(p[2], b - trail_dist)
        elif b < a:    # gia di xuong
            still = []
            for lv in sstops:
                if b <= lv:
                    op = min(lv, a) - slip
                    pos.append([False, op, lv + sl if sl else 0.0, lot])
                else:
                    still.append(lv)
            sstops = still
            keep = []
            for p in pos:
                if p[0] and p[2] and b <= p[2]:
                    close(p, min(p[2], a) - slip, t)
                else:
                    keep.append(p)
            pos = keep
            for p in pos:
                if not p[0] and p[1] - (b + spread) >= trail_start:
                    p[2] = min(p[2], b + spread + trail_dist)

    for t, o, h, l, c in rows:
        if (start and t < start) or (end and t >= end):
            continue
        if blown:
            break
        lt = local(t)
        dk = lt.date()
        if dk != day_key:
            daily[day_key] = bal
            day_key, day_eq, day_stop = dk, eq_at(o), False
        wd = lt.weekday()
        weekend = (wd == 4 and lt.hour >= fri_stop) or wd in (5, 6) or (wd == 0 and lt.hour < mon_start)
        if weekend:
            if pos:
                close_all(o, t)
            bstops, sstops = [], []
            continue
        nightp = night and night[0] <= lt.hour < night[1]

        # dat lai luoi moi nen grid_min phut
        if t.minute % grid_min == 0 and not day_stop and not nightp:
            bstops = [o + spread + step * k for k in range(1, levels + 1)]
            sstops = [o - step * k for k in range(1, levels + 1)]
        if nightp or day_stop:
            bstops, sstops = [], []

        check(o, t)
        path = fine_path(o, h, l, c, fine, rng) if fine else ([o, l, h, c] if c >= o else [o, h, l, c])
        for a, b in zip(path, path[1:]):
            if blown:
                break
            segment(a, b, t)
            check(b, t)

    if pos:
        close_all(rows[-1][4], rows[-1][0])
    daily[day_key] = bal
    return dict(final=bal, max_dd=max_dd, trades=trades, blown=blown, daily=daily)
