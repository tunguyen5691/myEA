"""
5 huong tang loi nhuan cho ban hien tai (M15, L10, SL 4 nen, M0.01 + L33 0.03, RSI 70/30,
nguoc chi dong khi loi, bo 03-07h, SMA34 > SMA89):
  1) nhoi lenh khi tin hieu cung chieu va ro dang loi
  2) chot 1 phan khi cham RSI, de phan con lai chay
  3) lot theo ATR (danh lon khi vang bien dong manh)
  4) tranh gio ra tin My (gan dung: 8:30 ET moi ngay, 14:00 ET thu 4 = gio FOMC)
  5) tang lot theo von (lai kep)
"""
from datetime import datetime, timedelta

from bt_trendline import run
from trendline_filters import sma, both, atr_rma
from trendline_rsi_exit import Feat, SESS, TH, exit_map, f_hours, evaluate

F = Feat()
hours = f_hours(F, SESS["bo 03-07 VN"])
s34, s89 = sma(F.m15c, 34), sma(F.m15c, 89)
ma = lambda i, b: (s34[i] > s89[i]) == b
ALLOW = both(hours, ma)
BASE = dict(L=10, exit_at=exit_map(F, F.m15, 15, 70, 30), rev_mode="profit", rev_open=False,
            orders=[(0, 1), (0.33, 3)], sl_bars=4)
YRS = (F.m5[-1][0] - F.m5[0][0]).days / 365.25


def ev(name, allow=ALLOW, **kw):
    return evaluate(F, name, allow=allow, **dict(BASE, **kw))


# --- 3) che do bien dong: ATR14 M15 so voi trung binh ~1 nam truoc do
atr = atr_rma(F.m15)
N = 96 * 260
regime, s = [1.0] * len(atr), 0.0
for i, a in enumerate(atr):
    s += a
    if i >= N:
        s -= atr[i - N]
    regime[i] = a / (s / min(i + 1, N)) if s else 1.0


# --- 4) gio tin My (server GMT+0), quy doi gio he My
def us_dst(d):
    y = d.year
    mar = datetime(y, 3, 8) + timedelta(days=(6 - datetime(y, 3, 8).weekday()) % 7)   # CN thu 2 thang 3
    nov = datetime(y, 11, 1) + timedelta(days=(6 - datetime(y, 11, 1).weekday()) % 7)  # CN dau thang 11
    return mar <= d < nov


def news_block(win_min, fomc=False, ten=False):
    def ok(i, b):
        te = F.m15[i][0] + timedelta(minutes=15)
        if te.weekday() >= 5:
            return True
        off = 4 if us_dst(te) else 5
        evs = [(8, 30)] + ([(10, 0)] if ten else []) + ([(14, 0)] if fomc and te.weekday() == 2 else [])
        for h, m in evs:
            rel = datetime(te.year, te.month, te.day, h, m) + timedelta(hours=off)
            if abs((te - rel).total_seconds()) <= win_min * 60:
                return False
        return True
    return ok


if __name__ == "__main__":
    print("=== goc ===")
    ev("hien tai")
    print("=== 1) nhoi lenh ===")
    for n in (1, 2, 3):
        for slm in ("struct", "be"):
            ev(f"nhoi toi da {n}, SL {slm}", pyr_max=n, pyr_sl=slm)
    print("=== 2) chot 1 phan o RSI ===")
    for fr in (0.5, 0.67):
        ev(f"chot {int(fr*100)}%, con lai cho nguoc/SL", part_frac=fr)
        ev(f"chot {int(fr*100)}%, con lai SL hoa von", part_frac=fr, part_be=True)
        ev(f"chot {int(fr*100)}%, con lai trailing 2R", part_frac=fr, part_trail_r=2.0)
        ev(f"chot {int(fr*100)}%, hoa von + trailing 3R", part_frac=fr, part_be=True, part_trail_r=3.0)
    print("=== 3) lot theo ATR (so voi ~1 nam) ===")
    ev("lot x2 co dinh (de so sanh)", lot=0.02)
    for th in (1.2, 1.5):
        ev(f"x2 khi ATR >= {th} lan TB", lot_fn=(lambda th: lambda i: 2.0 if regime[i] >= th else 1.0)(th))
    ev("lot = ATR/TB, kep 1..2", lot_fn=lambda i: min(2.0, max(1.0, regime[i])))
    ev("lot = ATR/TB, kep 1..3", lot_fn=lambda i: min(3.0, max(1.0, regime[i])))
    print("=== 4) tranh gio tin My ===")
    for w in (15, 30, 60):
        ev(f"bo +-{w}p quanh 8:30 ET", allow=both(ALLOW, news_block(w)))
    ev("bo +-30p 8:30 + 14:00 thu 4", allow=both(ALLOW, news_block(30, fomc=True)))
    ev("bo +-30p 8:30 + 10:00 + 14:00 T4", allow=both(ALLOW, news_block(30, fomc=True, ten=True)))
    print("=== 5) lai kep (lot theo von) ===")
    for per in (3000, 4000):
        r = run("M15", F.m15, F.m5, *TH, allow=ALLOW, sig=F.signals(10, 1.0), scale_per=per,
                scale_mode="prop", **BASE)
        cagr = (r["end"] / 3000) ** (1 / YRS) - 1
        print(f"lot theo von/{per}: von cuoi {r['end']:.0f}  lai kep {cagr*100:.1f}%/nam  "
              f"sut von {r['dd_rel']:.0f}% dinh ({r['dd']:.0f} USD)", flush=True)
    r = run("M15", F.m15, F.m5, *TH, allow=ALLOW, sig=F.signals(10, 1.0), **BASE)
    print(f"lot co dinh: von cuoi {r['end']:.0f}  lai kep {((r['end']/3000)**(1/YRS)-1)*100:.1f}%/nam  "
          f"sut von {r['dd_rel']:.0f}% dinh ({r['dd']:.0f} USD)")
