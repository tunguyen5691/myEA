import sys
from datetime import datetime
from bt_rsi_base_h1_xau import load, run, MULTS

rows = load('../XAUUSD_H1_202201022300_202610220100.csv')
D, LOT, SPREAD = 5000 * 100, 0.1, 0.30
YEARS = (rows[-1][0] - datetime(2022, 1, 3)).days / 365.25
SETS = {
    "1->7 x20 (hien tai)": MULTS,
    "deu 1 x20":           [1] * 20,
    "1->5 x10":            [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
    "deu 1 x10":           [1] * 10,
}
print(f"{'he so':20} step  SL  | loi%   /nam  | DD dinh-day | loi/DD | 22-24 | 25-26 | ro lo nhat")
for name, m in SETS.items():
    for step in (5, 10):
        for sl in (None, 100, 125, 150, 175, 200, 250):
            x = run(rows, LOT, SPREAD, deposit=D, sl=sl, step=step, mults=m)
            if x['blown']:
                print(f"{name:20} {step:4} {str(sl):>4} | CHAY {x['blown']:%Y-%m-%d}")
                continue
            p = x['profit'] / D * 100
            cagr = ((1 + p / 100) ** (1 / YEARS) - 1) * 100
            a = sum(b['pnl'] for b in x['baskets'] if b['close_t'] < datetime(2025, 1, 1)) / D * 100
            worst = min(b['pnl'] for b in x['baskets']) / 100
            print(f"{name:20} {step:4} {str(sl):>4} | {p:+5.0f}% {cagr:+5.1f}% | {x['max_dd_pct']:5.1f}%      | {p / x['max_dd_pct']:5.2f}  | {a:+5.0f}% | {p - a:+5.0f}% | ${worst:7.0f}")
    sys.stdout.flush()
