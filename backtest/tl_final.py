"""Ban cuoi: SL toi da 100 + bo thu 4 + nua lot sau ro thang + limit 50% x3. Monte Carlo + so sanh."""
import random
from tl_all import new, run, max_dd, NEW

FINAL = dict(orders=[(0, 1), (0.5, 3)])
for name, f, kw in (("EA hien tai", run, {}), ("BAN CUOI", new, FINAL)):
    r, *_ = f(name, **kw)
    seq = [(b[2], b[6]) for b in r["baskets"]]
    hist = max_dd(seq)
    rnd = random.Random(7)
    n, res = len(seq), []
    for _ in range(3000):
        blk = []
        while len(blk) < n:
            k = rnd.randrange(n - 20)
            blk.extend(seq[k:k + 20])
        res.append(max_dd(blk[:n]))
    res.sort()
    k95 = res[int(.95 * len(res))] / hist
    print(f"   Monte Carlo (khoi 20 ro): DD 95% = {k95:.2f} x DD lich su -> DD mo phong {r['dd']:.0f} x {k95:.2f} "
          f"= ~{r['dd'] * k95:.0f} USD ({r['dd'] * k95 / 30:.0f}% von 3000)")
