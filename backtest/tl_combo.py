"""Ghep cac cai tien tot + kiem tra lan can (tl_all: H1 cung chieu, limit 50% x3, vao limit hoi 20%)."""
import bisect
import sys
from datetime import timedelta
import bt_trendline as T
from tl_all import F, new, noWed, both


def h1_filter(L):
    hb, hs, _ = T.signals(F.h1, L)
    h1t = [r[0] + timedelta(hours=1) for r in F.h1]
    last, d = [], None
    for i in range(len(F.h1)):
        d = True if hb[i] else (False if hs[i] else d)
        last.append(d)
    def ok(i, b):
        k = bisect.bisect_right(h1t, F.m15[i][0] + timedelta(minutes=15)) - 1
        return k >= 0 and last[k] == b
    return ok


H1 = {L: h1_filter(L) for L in (6, 8, 10, 14, 20)}
if __name__ == "__main__":
    print("--- lan can: L trendline H1 ---")
    for L in (6, 8, 10, 14, 20):
        new(f"H1 cung chieu (L{L})", allow=both(noWed, H1[L]))
    print("--- lan can: vi tri limit x3 ---")
    for p in (0.4, 0.5, 0.6):
        new(f"M + L{int(p*100)} x3", orders=[(0, 1), (p, 3)])
    print("--- ket hop ---")
    hw = both(noWed, H1[10])
    new("H1 + L50 x3", allow=hw, orders=[(0, 1), (0.5, 3)])
    new("H1 + L40 x3", allow=hw, orders=[(0, 1), (0.4, 3)])
    new("H1 + L50 x3 + vao limit hoi 20%", allow=hw, orders=[(0.2, 1), (0.5, 3)])
    new("H1 + M + L25 x2 + L50 x2", allow=hw, orders=[(0, 1), (0.25, 2), (0.5, 2)])
    new("H1 + L50 x4", allow=hw, orders=[(0, 1), (0.5, 4)])
