"""Mo xe ro lenh cua xau_trendline hien tai (co loc tin My) theo d, thu, gio, chieu, chuoi thua."""
from collections import defaultdict
from datetime import timedelta
from five_ideas import F, ALLOW, BASE, ev, news_block
from trendline_filters import both

A = both(ALLOW, news_block(30, fomc=True))
r, score, pos = ev("hien tai + loc tin (= EA)", allow=A)
bs = r["baskets"]                      # (time, is_buy, pnl, n_orders, reason, d)


def show(title, keyf, order=None):
    g = defaultdict(lambda: [0, 0.0, 0])
    for b in bs:
        k = keyf(b)
        g[k][0] += 1; g[k][1] += b[2]; g[k][2] += b[2] > 0
    print(f"\n--- {title} ---")
    for k in (order or sorted(g)):
        if k in g:
            n, p, w = g[k]
            print(f"  {str(k):<14} ro {n:4d}  win {w / n * 100:3.0f}%  PnL {p:+7.0f}  TB {p / n:+6.1f}")


show("d (khoang SL, gia)", lambda b: "<5" if b[5] < 5 else "<10" if b[5] < 10 else "<20" if b[5] < 20 else "<35" if b[5] < 35 else "35-50",
     ["<5", "<10", "<20", "<35", "35-50"])
show("ly do dong", lambda b: b[4])
show("chieu", lambda b: "BUY" if b[1] else "SELL")
show("thu (gio VN)", lambda b: (b[0] + timedelta(hours=7)).strftime("%a"), ["Mon", "Tue", "Wed", "Thu", "Fri"])
show("gio vao (VN)", lambda b: (b[0] + timedelta(hours=7)).hour, list(range(24)))
prev = {}
for k, b in enumerate(bs):
    prev[id(b)] = "sau thang" if k and bs[k - 1][2] > 0 else "sau thua"
show("ro truoc do", lambda b: prev[id(b)])
