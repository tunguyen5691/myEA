import sys, time
from datetime import datetime
from bt_mtf import Data, run

D = 500000
FILES = {"M15": "../XAUUSD_M15_202201022300_202610220230.csv", "M5": "../XAUUSD_M5_202201022305_202610220230.csv"}
H1 = "../XAUUSD_H1_202201022300_202610220100.csv"


def line(name, x):
    if x['blown']:
        return f"{name:40} | CHAY {x['blown']:%Y-%m-%d}"
    bs = x['baskets']; yr = []; prev = 0
    for y in range(2022, 2027):
        cur = sum(b['pnl'] for b in bs if b['close_t'] < datetime(y + 1, 1, 1))
        yr.append(f"{(cur - prev) / (D + prev) * 100:+5.1f}%"); prev = cur
    nsl = sum(b['why'] == 'SL' for b in bs)
    p = x['profit'] / D * 100
    return (f"{name:40} | {p:+5.0f}% | DD {x['max_dd_pct']:4.1f}% | loi/DD {p / max(x['max_dd_pct'], 0.1):4.2f} | ro {len(bs):4} SL {nsl:3} | "
            + " ".join(yr))


if __name__ == "__main__":
    for tf in sys.argv[1:]:
        t0 = time.time()
        d = Data(H1, FILES[tf])
        print(f"== khung {tf} (nap {time.time() - t0:.0f}s)")
        print(line("H1 tin hieu goc + EMA800 (doi chieu)", run(d, mode="h1sig", trend=800)))
        print(line("H1 tin hieu goc, khong loc", run(d, mode="h1sig")))
        for trig in ("rsi", "ma", "break"):
            for tr in (None, 800):
                x = run(d, mode="setup", trigger=trig, trend=tr)
                print(line(f"setup H1 + {trig} {tf}" + (" + EMA800" if tr else ""), x))
        sys.stdout.flush()
