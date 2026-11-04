from collections import defaultdict
from datetime import timedelta
from tl_ideas import F, A, U, run, wd, last_win
from trendline_filters import both

noWed = both(A, lambda i, b: wd(i) != 2)
cw = lambda f: (lambda i, d, bs, bal: U * (f if last_win(bs) else 1.0))
r, *_ = run("goc")
bs = r["baskets"]
g = defaultdict(float); h = defaultdict(float)
for k, b in enumerate(bs):
    y = b[0].year
    if (b[0] + timedelta(hours=7)).weekday() == 2:
        g[y] += b[2]
    h[(y, "sau thang" if k and bs[k - 1][2] > 0 else "sau thua")] += b[2]
print("PnL ro thu 4 theo nam:", {y: round(v) for y, v in sorted(g.items())})
print("PnL TB/ro sau thang vs sau thua theo nam:")
cnt = defaultdict(int)
for k, b in enumerate(bs):
    cnt[(b[0].year, "sau thang" if k and bs[k - 1][2] > 0 else "sau thua")] += 1
for y in range(2022, 2027):
    print("  ", y, " ".join(f"{s}: {h[(y, s)] / max(cnt[(y, s)], 1):+5.1f}" for s in ("sau thang", "sau thua")))
print("=== SL toi da ===")
for m in (80.0, 100.0, 150.0, 1e9):
    run(f"SL toi da {m:.0f}", th=(3.0, 10.0, m))
print("=== ket hop ===")
for m in (80.0, 100.0):
    run(f"SL{m:.0f} + bo thu 4", allow=noWed, th=(3.0, 10.0, m))
    run(f"SL{m:.0f} + sau thang x0.5", ctx=cw(0.5), th=(3.0, 10.0, m))
    run(f"SL{m:.0f} + bo thu 4 + sau thang x0.5", allow=noWed, ctx=cw(0.5), th=(3.0, 10.0, m))
