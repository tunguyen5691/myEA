"""Loc 'nen pha manh' cho ban hien tai (SL 4 nen, M0.01 + L33 0.03, RSI 70/30, nguoc chi dong khi loi,
bo 03-07h, SMA34 > SMA89 M15). Chi chan vao lenh moi; tin hieu bi loc van dong ro nguoc dang loi.
Do manh nen pha (nen tin hieu, M15):
  vuot  : gia dong vuot trendline >= x ATR(10)
  than  : than nen |C-O| >= x ATR(14), cung chieu tin hieu
  ty le : than / (H-L) >= x, cung chieu
  dong  : dong cua o phan tren (BUY) / duoi (SELL) cua nen: (C-L)/(H-L) >= x
  bien  : (H-L) >= x ATR(14)
"""
from trendline_filters import sma, both, atr_rma
from trendline_rsi_exit import Feat, SESS, exit_map, f_hours, evaluate

F = Feat()
hours = f_hours(F, SESS["bo 03-07 VN"])
s34, s89 = sma(F.m15c, 34), sma(F.m15c, 89)
ma = lambda i, b: (s34[i] > s89[i]) == b
base = dict(L=10, exit_at=exit_map(F, F.m15, 15, 70, 30), rev_mode="profit", rev_open=False,
            orders=[(0, 1), (0.33, 3)], sl_bars=4)
atr = atr_rma(F.m15)
brk = F.signals(10, 1.0)[2]
R = F.m15


def body(i, b):
    _, o, h, l, c = R[i]
    return (c - o) if b else (o - c)


def rng(i):
    return max(R[i][2] - R[i][3], 1e-9)


FILT = {
    "vuot >= 0.1 ATR": lambda x: lambda i, b: brk[i] >= x, "vuot": [0.1, 0.25, 0.5],
}
tests = []
for x in (0.1, 0.25, 0.5):
    tests.append((f"vuot trendline >= {x} ATR", (lambda x: lambda i, b: brk[i] >= x)(x)))
for x in (0.3, 0.5, 0.8, 1.0):
    tests.append((f"than nen >= {x} ATR", (lambda x: lambda i, b: body(i, b) >= x * atr[i])(x)))
for x in (0.5, 0.6, 0.7):
    tests.append((f"than/bien nen >= {x}", (lambda x: lambda i, b: body(i, b) / rng(i) >= x)(x)))
for x in (0.6, 0.7, 0.8):
    tests.append((f"dong o {int(x*100)}% phia pha", (lambda x: lambda i, b:
                  ((R[i][4] - R[i][3]) if b else (R[i][2] - R[i][4])) / rng(i) >= x)(x)))
for x in (1.0, 1.5):
    tests.append((f"bien nen >= {x} ATR", (lambda x: lambda i, b: rng(i) >= x * atr[i])(x)))

evaluate(F, "hien tai (khong loc nen)", allow=both(hours, ma), **base)
for name, f in tests:
    evaluate(F, name, allow=both(hours, ma, f), **base)
