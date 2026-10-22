import sys, time
from collections import defaultdict
from bt_stopgrid import load, run

M5 = load("../XAUUSD_M5_202201022305_202610220230.csv")
M15 = load("../XAUUSD_M15_202201022300_202610220230.csv")


def summary(name, x, dep=500.0):
    tr = x['trades']
    win = sum(r > 0 for _, r in tr)
    days = [v for k, v in sorted((k, v) for k, v in x['daily'].items() if k)]
    dchg = [(b - a) / a * 100 for a, b in zip(days, days[1:]) if a > 0]
    worst = min(dchg) if dchg else 0
    yr = defaultdict(float)
    for t, r in tr:
        yr[t.year] += r
    return (f"{name:38} | cuoi ${x['final']:9.0f} ({(x['final'] / dep - 1) * 100:+7.0f}%) | DD {x['max_dd']:5.1f}% | "
            f"lenh {len(tr):6} thang {win / max(len(tr), 1) * 100:4.1f}% | ngay te nhat {worst:+5.1f}% | "
            + ("CHAY " + x['blown'].strftime('%Y-%m-%d') if x['blown'] else "song") + " | "
            + " ".join(f"{y}:{v:+.0f}" for y, v in sorted(yr.items())))


if __name__ == "__main__":
    t0 = time.time()
    print(summary("M5, spread 0.3, truot 0", run(M5)))
    print(f"({time.time() - t0:.0f}s)")
