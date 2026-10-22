import sys
from datetime import datetime
from bt_rsi_base_h1_xau import load, run

rows = load(sys.argv[1])
LOT, SPREAD = 0.1, float(sys.argv[2]) if len(sys.argv) > 2 else 0.30
usd = lambda usc: usc / 100

r = run(rows, LOT, SPREAD)
bs = r["baskets"]
print(f"== Toan bo {rows[0][0]:%Y-%m-%d} -> {rows[-1][0]:%Y-%m-%d} | lot {LOT} cent | spread {SPREAD}")
print(f"Loi nhuan: ${usd(r['profit']):.2f} | so ro: {len(bs)} | equity thap nhat (tu luc bat dau): ${usd(r['min_eq']):.2f} @ {r['min_eq_t']}")
print("Von toi thieu de khong chay (stop out 0 phan tram): ~$%.0f" % -usd(r['min_eq']))
win = sum(b['pnl'] > 0 for b in bs)
print(f"Ro loi: {win}/{len(bs)} | lenh limit khop nhieu nhat: {max(b['filled'] for b in bs)}")
from collections import Counter
print("Phan bo so lenh limit khop:", sorted(Counter(b['filled'] for b in bs).items()))
print("\n== 8 ro thua lo tha noi nang nhat")
for b in sorted(bs, key=lambda b: b['worst'])[:8]:
    print(f"{b['open_t']:%Y-%m-%d %H:%M} {'BUY ' if b['buy'] else 'SELL'} @ {b['entry']:.2f} | khop {b['filled']:2d} | "
          f"tha noi te nhat ${usd(b['worst']):8.2f} @ {b['worst_t']:%Y-%m-%d %H:%M} gia {b['worst_px']:.2f} "
          f"(cach {abs(b['worst_px']-b['entry']):.0f} gia) | dong {b['close_t']:%Y-%m-%d %H:%M} {b['why']} ${usd(b['pnl']):.2f}")

print("\n== Tung nam, bat dau von moi")
deps = [100, 200, 300, 500, 1000]
print("nam  | loi($) von vo han | tha noi te nhat($) | " + " | ".join(f"von ${d}" for d in deps))
for y in range(2022, 2027):
    s, e = datetime(y, 1, 1), datetime(y + 1, 1, 1)
    inf = run(rows, LOT, SPREAD, start=s, end=e)
    cells = []
    for d in deps:
        x = run(rows, LOT, SPREAD, deposit=d * 100, start=s, end=e)
        cells.append(f"CHAY {x['blown']:%m-%d}" if x['blown'] else f"{x['profit'] / (d * 100) * 100:+.0f}%")
    worst = min(b['worst'] for b in inf['baskets'])
    print(f"{y} | {usd(inf['profit']):8.2f} | {usd(worst):8.2f} (equity min {usd(inf['min_eq']):.2f}) | " + " | ".join(cells))

print("\n== Chay lien tuc tu 2022, khong rut")
for d in deps:
    x = run(rows, LOT, SPREAD, deposit=d * 100)
    print(f"von ${d}: " + (f"CHAY TAI KHOAN {x['blown']:%Y-%m-%d %H:%M}, loi truoc do ${usd(x['profit']):.2f}" if x['blown']
                          else f"song, loi ${usd(x['profit']):.2f} ({x['profit']/(d*100)*100:+.0f}%)"))
