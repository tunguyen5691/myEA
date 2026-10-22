"""
Mo phong xau_trendline.mq5 (tin hieu pha trendline LuxAlgo) tren nhieu khung.

Tin hieu tinh tren khung TF (nen da dong), khop lenh chay tren duong gia M5 (O-L-H-C / O-H-L-C)
-> SL / limit trong nen H1, M15 sat thuc te hon chay thang tren nen H1.
Gia trong CSV la BID, server GMT+0. Tai khoan USD thuong: 0.01 lot = 1 USD / 1 gia.

Luat (giong EA):
  - Pivot 14/14, do doc = ATR14 (RMA) / 14 x mult, pha len -> BUY, pha xuong -> SELL.
  - Vao market o open nen ke tiep. SL = low/high InpSlBars nen TF vua dong, d = |entry - SL|.
      d < min_trade -> bo qua; d > max_dist -> keo SL ve max_dist;
      d >= min_limits -> them 2 limit o 33% / 66% cua d. Chung SL, khong TP.
  - Tin hieu nguoc -> dong ro cu (+ xoa limit) roi vao ro moi. Cung chieu dang co ro -> bo qua.
  - Nghi cuoi tuan T6 17h -> T2 6h (gio VN) + ngay le: dong het luc bat dau nghi.
"""
import bisect
import math
import sys
from datetime import datetime, timedelta, date

from bt_rsi_base_h1_xau import load

GMT_OFFSET, STOP_H, START_H = 7, 17, 6
HOLIDAYS = [date(*d) for d in [
    (2022, 4, 15), (2022, 11, 24), (2022, 12, 25), (2023, 1, 1),
    (2023, 4, 7), (2023, 11, 23), (2023, 12, 25), (2024, 1, 1),
    (2024, 3, 29), (2024, 11, 28), (2024, 12, 25), (2025, 1, 1),
    (2025, 4, 18), (2025, 11, 27), (2025, 12, 25), (2026, 1, 1),
    (2026, 4, 3), (2026, 11, 26), (2026, 12, 25), (2027, 1, 1)]]
ROOT = "E:/PERSONAL/gitHub/myEA/"
FILES = {
    "M5": ROOT + "XAUUSD_M5_202201022305_202610220230.csv",
    "M15": ROOT + "XAUUSD_M15_202201022300_202610220230.csv",
    "H1": ROOT + "XAUUSD_H1_202201022300_202610220100.csv",
}
TF_MIN = {"M1": 1, "M5": 5, "M15": 15, "H1": 60}


def paused(t):
    loc = t + timedelta(hours=GMT_OFFSET)
    wd = loc.weekday()
    if (wd == 4 and loc.hour >= STOP_H) or wd in (5, 6) or (wd == 0 and loc.hour < START_H):
        return True
    for h in HOLIDAYS:
        d0 = datetime(h.year, h.month, h.day)
        if d0 - timedelta(days=1) + timedelta(hours=STOP_H) <= loc < d0 + timedelta(days=1, hours=START_H):
            return True
    return False


def signals(rows, L=14, mult=1.0):
    """Tra ve buy[i], sell[i], brk[i]: tin hieu khi nen i dong (giong CalcSignals cua EA),
    brk = gia dong vuot duong bao nhieu ATR (do manh cu pha)."""
    n = len(rows)
    h = [r[2] for r in rows]
    l = [r[3] for r in rows]
    c = [r[4] for r in rows]
    buy, sell, brk = [False] * n, [False] * n, [0.0] * n
    atr = upper = lower = sph = spl = 0.0
    upos = dnos = 0
    seen_ph = seen_pl = False
    for i in range(n):
        tr = h[i] - l[i]
        if i > 0:
            tr = max(tr, abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        if i < L:
            atr += tr / L
            continue
        atr = (atr * (L - 1) + tr) / L
        slope = atr / L * mult
        p = i - L
        is_ph = is_pl = False
        if p >= L:
            hp, lp = h[p], l[p]
            is_ph = all(h[j] < hp for j in range(p - L, i + 1) if j != p)
            is_pl = all(l[j] > lp for j in range(p - L, i + 1) if j != p)
        if is_ph:
            sph, upper, seen_ph = slope, h[p], True
        else:
            upper -= sph
        if is_pl:
            spl, lower, seen_pl = slope, l[p], True
        else:
            lower += spl
        pu, pd = upos, dnos
        if is_ph:
            upos = 0
        elif c[i] > upper - sph * L:
            upos = 1
        if is_pl:
            dnos = 0
        elif c[i] < lower + spl * L:
            dnos = 1
        buy[i] = seen_ph and upos > pu
        sell[i] = seen_pl and dnos > pd
        if buy[i]:
            brk[i] = (c[i] - (upper - sph * L)) / atr
        elif sell[i]:
            brk[i] = ((lower + spl * L) - c[i]) / atr
    return buy, sell, brk


def run(tf, sig_rows, ex_rows, min_trade, min_limits, max_dist, sl_bars=3, spread=0.30,
        lot=0.01, deposit=3000.0, pcts=(0.33, 0.66), L=14, mult=1.0, sig=None, allow=None,
        exit_filtered=True, be_r=None, trail_r=None, tp_r=None, exit_at=None, exit_profit_only=False,
        rev_mode="always", rev_open=True, orders=None, scale_per=None, scale_mode="floor",
        pyr_max=0, pyr_sl="struct", part_frac=None, part_be=False, part_trail_r=None, lot_fn=None):
    """be_r: lai >= be_r x d -> dua SL ve gia vao lenh market (hoa von).
    trail_r: lai >= trail_r x d -> SL bam theo, cach gia tot nhat trail_r x d.
    tp_r: chot loi ca ro khi gia di duoc tp_r x d tu gia vao market (None = khong TP).
    exit_at: {chi so nen M5: (dong_buy, dong_sell)} -> dong ro o open nen do (vd theo RSI base).
    exit_profit_only: chi dong theo exit_at khi ro dang loi.
    rev_mode: tin hieu nguoc dong ro cu khi nao: "always" / "loss" (chi khi dang lo) /
              "profit" (chi khi dang loi) / "never". Khong dong -> giu ro, bo qua tin hieu.
    rev_open: sau khi dong ro do tin hieu nguoc co vao ro moi chieu moi khong.
    scale_per: tang lot theo von: moi scale_per USD von (deposit + lai) = 1 lan lot goc.
      scale_mode "floor": he so = floor(von / scale_per) (tang theo bac);
      "prop": tung lenh = round(he_so_lot x von / scale_per) don vi 0.01 (min 0.01).
    orders: [(pct, he_so_lot), ...] khi d >= min_limits; pct 0 = market, >0 = limit o pct x d.
            None = market + pcts (lot x1). Khong co market -> ro chi gom limit; chua khop lenh
            nao thi tin hieu moi / RSI / nghi se huy limit (khong tinh la ro).
    sig: (buy, sell, brk) tinh san (khoi tinh lai moi lan).
    allow(i, is_buy) -> bool: bo loc tin hieu nen TF thu i.
    exit_filtered: tin hieu nguoc bi loc van dong ro cu (True) hay bo qua han (False).
    pyr_max: tin hieu CUNG chieu khi ro dang loi -> vao them 1 market (toi da pyr_max lan);
      pyr_sl "struct": SL ca ro = SL moi (InpSlBars nen) neu chat hon, "be": SL ve gia vao goc.
    part_frac: cham RSI -> chot part_frac moi lenh, xoa limit; phan con lai giu den tin hieu nguoc /
      SL / nghi; part_be: dua SL phan con lai ve hoa von; part_trail_r: trailing phan con lai.
    lot_fn(i) -> he so lot cho ro vao o nen TF thu i (vd theo ATR)."""
    usd = lot * 100.0                      # USD / 1 gia / lenh he so 1
    if orders is None:
        orders = [(0.0, 1.0)] + [(k, 1.0) for k in pcts]

    def flo_at(px):                        # lai/lo (gia x he so) cua ro tai gia px
        return sum(((px - e) if side else (e - px)) * m for e, m in pos)
    buy, sell, _ = sig or signals(sig_rows, L, mult)
    tf_delta = timedelta(minutes=TF_MIN[tf])
    ex_times = [r[0] for r in ex_rows]

    # tin hieu -> chi so nen M5 vao lenh (nen dau tien mo sau khi nen TF dong)
    plan = {}
    for i, r in enumerate(sig_rows):
        if not (buy[i] or sell[i]) or buy[i] == sell[i] or i < sl_bars:
            continue
        is_buy = buy[i]
        ok = allow is None or allow(i, is_buy)
        if not ok and not exit_filtered:
            continue
        win = sig_rows[i - sl_bars + 1:i + 1]
        sl = min(x[3] for x in win) if is_buy else max(x[2] for x in win)
        if r[0] + tf_delta < ex_times[0]:
            continue        # tin hieu truoc giai doan khop lenh (khi ex_rows bi cat)
        j = bisect.bisect_left(ex_times, r[0] + tf_delta)
        if j < len(ex_rows):
            plan.setdefault(j, (is_buy, sl, ok, i))

    bal = 0.0
    side = None           # True buy / False sell / None
    pos, pend, sl = [], [], 0.0
    baskets = []          # (time, is_buy, pnl, n_orders, reason, d)
    cur = None
    adds, partial, extra = 0, False, 0.0
    sz = lambda m: m
    e0 = 0.0
    peak = 0.0
    max_dd = 0.0
    peak_eq, max_dd_rel = deposit, 0.0     # sut von theo % dinh tai khoan
    curve = []                             # (thoi gian, lai/lo luy ke gom ca lenh dang chay)
    stats = {"skip_small": 0, "clamped": 0, "one": 0, "full": 0}

    def close_all(price_bid, reason, t):
        nonlocal bal, side, pos, pend, cur, adds, partial, extra
        px = price_bid if side else price_bid + spread
        pnl = flo_at(px) * usd
        bal += pnl
        if pos:
            baskets.append((cur[0], side, pnl + extra, len(pos), reason, cur[1]))
        side, pos, pend, cur = None, [], [], None
        adds, partial, extra = 0, False, 0.0

    for j, (t, o, hi, lo, c) in enumerate(ex_rows):
        p = paused(t)
        if side is not None and p:
            close_all(o, "pause", t)
        if side is not None and exit_at and j in exit_at and exit_at[j][0 if side else 1]:
            px = o if side else o + spread
            if partial:
                pass                          # da chot 1 phan, phan con lai cho tin hieu nguoc / SL
            elif part_frac and pos:
                got = flo_at(px) * part_frac * usd
                bal += got
                extra += got
                pos = [(e, m * (1 - part_frac)) for e, m in pos]
                pend, partial = [], True
                if part_be:
                    avg = sum(e * m for e, m in pos) / sum(m for _, m in pos)
                    sl = max(sl, avg) if side else min(sl, avg)
            elif not exit_profit_only or not pos or flo_at(px) > 0:
                close_all(o, "rsi", t)
        if j in plan and not p:
            is_buy, s, ok, si = plan[j]
            if side is not None and not pos:
                close_all(o, "cancel", t)     # ro chi co limit chua khop -> thay bang tin hieu moi
            if (pyr_max and side is not None and side == is_buy and ok and pos and adds < pyr_max
                    and not partial and flo_at(o if side else o + spread) > 0):
                pos.append((o + spread if side else o, sz(1.0)))
                adds += 1
                if pyr_sl == "be":
                    sl = max(sl, e0) if side else min(sl, e0)
                elif (side and o > s > sl) or (not side and o + spread < s < sl):
                    sl = s
            if side is not None and side != is_buy:
                px = o if side else o + spread
                fl = flo_at(px)
                if (rev_mode == "always" or (rev_mode == "loss" and fl <= 0)
                        or (rev_mode == "profit" and fl > 0)):
                    close_all(o, "reverse", t)
                    if not rev_open:
                        ok = False
            if side is None and ok:
                entry = o + spread if is_buy else o
                d = entry - s if is_buy else s - entry
                if d < min_trade:
                    stats["skip_small"] += 1
                else:
                    if d > max_dist:
                        d = max_dist
                        s = entry - d if is_buy else entry + d
                        stats["clamped"] += 1
                    side, sl, cur = is_buy, s, (t, d)
                    e0, best = entry, o
                    f = (deposit + bal) / scale_per if scale_per else 1.0
                    if lot_fn:
                        f *= lot_fn(si)
                    if scale_mode == "floor" and not lot_fn:
                        sz = lambda m, f=f: m * max(1, math.floor(f))
                    else:
                        sz = lambda m, f=f: max(1, round(m * f))
                    if d >= min_limits:
                        pos = [(entry, sz(m)) for k, m in orders if k == 0]
                        pend = [((entry - d * k) if is_buy else (entry + d * k), sz(m)) for k, m in orders if k > 0]
                        stats["full"] += 1
                    else:
                        pos, pend = [(entry, sz(1.0))], []
                        stats["one"] += 1
        # duong gia trong nen M5 (BID)
        path = [o, lo, hi, c] if c >= o else [o, hi, lo, c]
        if side is not None:
            for a, b in zip(path, path[1:]):
                if side is None:
                    break
                d = cur[1]
                if side and b < a:            # buy: gia xuong -> limit / SL theo thu tu gia
                    ev = sorted([(P - spread, q) for q in pend for P in (q[0],)] + [(sl, None)],
                                key=lambda x: x[0], reverse=True)
                    for lv, q in ev:
                        if lv < b:
                            break
                        if q is None:
                            close_all(min(sl, a), "sl", t)
                            break
                        pos.append((min(q[0], a + spread), q[1]))
                        pend.remove(q)
                elif side and b > a:          # buy: gia len -> TP / hoa von / trailing
                    if tp_r and b >= e0 + tp_r * d:
                        close_all(max(e0 + tp_r * d, a), "tp", t)
                        break
                    best = max(best, b)
                    if be_r and best >= e0 + be_r * d:
                        sl = max(sl, e0)
                    if trail_r and best >= e0 + trail_r * d:
                        sl = max(sl, best - trail_r * d)
                    if partial and part_trail_r:
                        sl = max(sl, best - part_trail_r * d)
                elif side is False and b > a:  # sell: gia len -> limit / SL theo thu tu gia
                    ev = sorted([(q[0], q) for q in pend] + [(sl - spread, None)], key=lambda x: x[0])
                    for lv, q in ev:
                        if lv > b:
                            break
                        if q is None:
                            close_all(max(sl, a + spread) - spread, "sl", t)
                            break
                        pos.append((max(q[0], a), q[1]))
                        pend.remove(q)
                elif side is False and b < a:  # sell: gia xuong -> TP / hoa von / trailing
                    if tp_r and b + spread <= e0 - tp_r * d:
                        close_all(min(e0 - tp_r * d, a + spread) - spread, "tp", t)
                        break
                    best = min(best, b)
                    if be_r and best + spread <= e0 - be_r * d:
                        sl = min(sl, e0)
                    if trail_r and best + spread <= e0 - trail_r * d:
                        sl = min(sl, best + spread + trail_r * d)
                    if partial and part_trail_r:
                        sl = min(sl, best + spread + part_trail_r * d)
        flo = 0.0
        if side is not None:
            flo = flo_at(c if side else c + spread) * usd
        eq = bal + flo
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)
        peak_eq = max(peak_eq, deposit + eq)
        curve.append((t, eq))
        max_dd_rel = max(max_dd_rel, (peak_eq - deposit - eq) / peak_eq)

    if side is not None:
        close_all(ex_rows[-1][4], "end", ex_rows[-1][0])

    wins = [b for b in baskets if b[2] > 0]
    gp = sum(b[2] for b in wins)
    gl = -sum(b[2] for b in baskets if b[2] <= 0)
    years = {}
    for b in baskets:
        years[b[0].year] = years.get(b[0].year, 0.0) + b[2]
    reasons = {}
    for b in baskets:
        reasons[b[4]] = reasons.get(b[4], 0) + 1
    months = (ex_rows[-1][0] - ex_rows[0][0]).days / 30.44
    return {
        "tf": tf, "pnl": bal, "ret": bal / deposit * 100, "dd": max_dd, "dd_pct": max_dd / (deposit + 0) * 100,
        "n": len(baskets), "per_month": len(baskets) / months, "win": len(wins) / max(1, len(baskets)) * 100,
        "pf": gp / gl if gl else float("inf"), "years": years, "reasons": reasons, "stats": stats,
        "avg_win": gp / max(1, len(wins)), "avg_loss": gl / max(1, len(baskets) - len(wins)),
        "baskets": baskets, "dd_rel": max_dd_rel * 100, "end": deposit + bal, "curve": curve,
    }


def report(r):
    print(f"== {r['tf']}: PnL {r['pnl']:+.0f} USD ({r['ret']:+.1f}% / 3000)  maxDD {r['dd']:.0f} USD "
          f"({r['dd_pct']:.1f}%)  ro {r['n']} ({r['per_month']:.1f}/thang)  win {r['win']:.0f}%  "
          f"PF {r['pf']:.2f}  TB thang {r['avg_win']:.1f} / TB thua {r['avg_loss']:.1f}")
    print("   theo nam: " + "  ".join(f"{y}:{v:+.0f}" for y, v in sorted(r["years"].items())))
    print(f"   dong do: {r['reasons']}   vao: {r['stats']}")


# nguong d theo khung (H1 = mac dinh EA, khung nho thu nho lai)
THRESH = {"M5": (1.0, 3.0, 15.0), "M15": (1.5, 5.0, 25.0), "H1": (3.0, 10.0, 50.0)}

if __name__ == "__main__":
    tfs = sys.argv[1:] or ["H1", "M15", "M5"]
    m5 = load(FILES["M5"])
    for tf in tfs:
        rows = m5 if tf == "M5" else load(FILES[tf])
        for label, th in (("nguong theo khung", THRESH[tf]), ("nguong H1 3/10/50", THRESH["H1"])):
            if tf == "H1" and label != "nguong theo khung":
                continue
            r = run(tf, rows, m5, *th)
            print(f"[{label} {th}]")
            report(r)
