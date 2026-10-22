"""Von 1000-5000 USD voi ban chot (lot co dinh): co chay khong, bat dau o thoi diem nao cung duoc."""
from trendline_rsi_exit import Feat, SESS, TH, exit_map, f_hours
from bt_trendline import run

F = Feat()
r = run("M15", F.m15, F.m5, *TH, allow=f_hours(F, SESS["bo 03-07 VN"]), L=10,
        exit_at=exit_map(F, F.m15, 15, 70, 30), rev_mode="profit", rev_open=False,
        sig=F.signals(10, 1.0), orders=[(0, 1), (0.33, 3)], sl_bars=4)
cv = r["curve"]
eq = [e for _, e in cv]
n = len(eq)
# lo lon nhat ke tu moi diem bat dau: eq[s] - min(eq[s:])
suf_min = [0.0] * n
m = float("inf")
for i in range(n - 1, -1, -1):
    m = min(m, eq[i])
    suf_min[i] = m
loss_from = [eq[i] - suf_min[i] for i in range(n)]
# bat dau dau moi thang
starts, seen = [], set()
for i, (t, _) in enumerate(cv):
    k = (t.year, t.month)
    if k not in seen:
        seen.add(k)
        starts.append(i)
print(f"Lo lon nhat neu bat dau tu 01/2022: {loss_from[0]:.0f} USD")
w = max(range(n), key=lambda i: loss_from[i])
print(f"Lo lon nhat neu bat dau o thoi diem XAU NHAT ({cv[w][0]:%d/%m/%Y}): {loss_from[w]:.0f} USD")
print(f"So thang bat dau thu: {len(starts)}")
print("Von  | sut lon nhat (te nhat) | thang bat dau bi lo > 50% von | > 80% von (gan chay) | chay (lo >= von)")
for D in (1000, 1500, 2000, 2500, 3000, 4000, 5000):
    L = [loss_from[i] for i in starts]
    print(f"{D:5} | {loss_from[w] / D * 100:5.0f}%                 | {sum(x > 0.5 * D for x in L):3}/{len(L)}"
          f"                        | {sum(x > 0.8 * D for x in L):3}/{len(L)}               | {sum(x >= D for x in L):3}/{len(L)}")
top = sorted(((loss_from[i], cv[i][0]) for i in starts), reverse=True)[:5]
print("5 thang bat dau te nhat:", [(f"{t:%m/%Y}", round(x)) for x, t in top])

# bat dau moi ngay (chinh xac hon dau thang)
dstarts, seen = [], set()
for i, (t, _) in enumerate(cv):
    if t.date() not in seen:
        seen.add(t.date())
        dstarts.append(i)
print(f"\nBat dau moi ngay ({len(dstarts)} ngay):")
for D in (1000, 1500, 2000, 2500, 3000, 4000, 5000):
    L = [loss_from[i] for i in dstarts]
    bad = [cv[i][0] for i in dstarts if loss_from[i] >= D]
    rng = f"{bad[0]:%d/%m/%Y} -> {bad[-1]:%d/%m/%Y}" if bad else "-"
    print(f"{D:5}: chay {len(bad):4} ngay ({len(bad)/len(L)*100:4.1f}%)  lo > 50% von {sum(x > 0.5*D for x in L)/len(L)*100:4.1f}%  | ngay chay: {rng}")
