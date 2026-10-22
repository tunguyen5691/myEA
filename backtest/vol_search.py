"""Thu luoi / SL / lot co gian theo bien dong (ATR) de nam yen ang cung co loi. Von $5k, swap 40, dong cuoi tuan + le."""
import sys
from datetime import timedelta, datetime
import factor_search as F
import bt_rsi_base_h1_xau as B

rows = F.rows
D = F.D
orig = B.paused


def paused_hol(t):
    loc = t + timedelta(hours=B.GMT_OFFSET)
    md = (loc.month, loc.day)
    if md in ((12, 24), (12, 31)) and loc.hour >= B.FRI_STOP:
        return True
    if md in ((12, 25), (1, 1)):
        return True
    if md in ((12, 26), (1, 2)) and loc.hour < B.MON_START:
        return True
    return orig(t)


B.paused = paused_hol
F.REG[300] = F.reg_slope(300)
TR = [rows[0][2] - rows[0][3]] + [max(rows[i][2], rows[i - 1][4]) - min(rows[i][3], rows[i - 1][4]) for i in range(1, len(rows))]
VOL = F.sma(TR, 240) if hasattr(F, "sma") else None
if VOL is None:
    VOL, s = [], 0.0
    for i, x in enumerate(TR):
        s += x - (TR[i - 240] if i >= 240 else 0)
        VOL.append(s / min(i + 1, 240))


def go(lot, **kw):
    x = B.run(rows, lot, 0.30, deposit=D, swap=40, allow=F.f_reg(300), mults=B.MULTS, reverse=False, weekend=True, **kw)
    if x['blown']:
        return None
    bs = x['baskets']; yr = []; prev = 0
    for y in range(2022, 2027):
        cur = sum(b['pnl'] for b in bs if b['close_t'] < datetime(y + 1, 1, 1))
        yr.append((cur - prev) / (D + prev) * 100); prev = cur
    return dict(p=x['profit'] / D * 100, dd=x['max_dd_pct'], yr=yr, worst=min(b['pnl'] for b in bs) / 100,
                maxlot=max(b.get('lot', lot) for b in bs))


def show(name, r):
    if r is None:
        print(f"{name:44} | CHAY"); return
    print(f"{name:44} | {r['p']:+5.0f}% | DD {r['dd']:4.1f}% | loi/DD {r['p'] / r['dd']:4.1f} | nam te nhat {min(r['yr']):+5.1f}% | "
          + " ".join(f"{y:+5.1f}" for y in r['yr']) + f" | ro lo nhat ${r['worst']:.0f} lot max {r['maxlot']:.2f}")


if __name__ == "__main__":
    print("Bien do nen H1 TB (240 nen): 2022 ~4.8, 2024 ~6.1, 2026 ~22.8")
    print(f"{'cau hinh':44} | loi%   | DD    | loi/DD | nam te nhat | 2022 2023 2024 2025 2026")
    show("goc: buoc 5, SL125, lot 0.2 co dinh", go(0.2, sl=125))
    for k in (0.25, 0.35, 0.5, 0.75):
        show(f"buoc {k}xATR, SL 25xbuoc, lot 0.2 co dinh", go(0.2, sl=125, vol=VOL, k_step=k))
    for k in (0.25, 0.35, 0.5, 0.75):
        for ref in (10, 15):
            show(f"buoc {k}xATR, SL 25xbuoc, lot 0.1x{ref}/ATR", go(0.1, sl=125, vol=VOL, k_step=k, atr_ref=ref))
    for ref in (10, 15):
        show(f"buoc 5 co dinh, SL125, lot 0.1x{ref}/ATR", go(0.1, sl=125, vol=VOL, atr_ref=ref))
    for k, m in ((0.35, 20), (0.35, 30), (0.5, 20), (0.5, 30)):
        show(f"buoc {k}xATR, SL {m}xbuoc, lot 0.1x15/ATR", go(0.1, sl=125, vol=VOL, k_step=k, sl_mult=m, atr_ref=15))
