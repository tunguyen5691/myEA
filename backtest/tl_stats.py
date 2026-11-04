"""Bang chi so day du cho BAN CUOI tren du lieu M1 07/2021-11/2026 (lot goc 0.01 + limit 0.03, von 3000)."""
import tl_oos  # noqa: F401  (dung FILES tu M1)
from collections import defaultdict
from tl_ideas import run, last_win, U
from tl_oos import noWed

r, *_ = run("BAN CUOI", allow=noWed, ctx=lambda i, d, bs, bal: U * (0.5 if last_win(bs) else 1.0),
            th=(3.0, 10.0, 100.0), orders=[(0, 1), (0.5, 3)])
bs = r["baskets"]
pn = [b[2] for b in bs]
win = [x for x in pn if x > 0]
loss = [x for x in pn if x <= 0]
streak = cur = 0
for x in pn:
    cur = cur + 1 if x <= 0 else 0
    streak = max(streak, cur)
mon = defaultdict(float)
for b in bs:
    mon[(b[7].year, b[7].month)] += b[2]
t0, t1 = r["curve"][0][0], r["curve"][-1][0]
yrs = (t1 - t0).days / 365.25
end = 3000 + r["pnl"]
print(f"Giai doan {t0:%d/%m/%Y} -> {t1:%d/%m/%Y} ({yrs:.1f} nam)")
print(f"Lai {r['pnl']:+.0f} ({r['pnl'] / 30:+.0f}%), CAGR {((end / 3000) ** (1 / yrs) - 1) * 100:.1f}%/nam")
print(f"DD max {r['dd']:.0f} ({r['dd'] / 30:.1f}% von dau) | DD % dinh {r['dd_rel']:.1f}%")
print(f"So ro {len(bs)} ({len(bs) / yrs / 12:.1f}/thang) | win {len(win) / len(bs) * 100:.1f}% | PF {sum(win) / -sum(loss):.2f}")
print(f"TB thang {sum(win) / len(win):.1f} | TB thua {sum(loss) / len(loss):.1f} | ro lai nhat {max(pn):.0f} | ro lo nhat {min(pn):.0f}")
print(f"Lo noi sau nhat 1 ro {min(b[6] for b in bs):.0f} | thua lien tiep dai nhat {streak}")
print(f"Thang duong {sum(1 for v in mon.values() if v > 0)}/{len(mon)} | thang te nhat {min(mon.values()):.0f} | thang tot nhat {max(mon.values()):.0f}")
print("Ly do dong:", r["reasons"])
print("Theo nam:", {y: round(v) for y, v in sorted(r["years"].items())})
