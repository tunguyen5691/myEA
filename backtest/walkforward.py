"""
Kiem tra cheo (walk-forward) cho xau_trendline M15:
  - CHI dung 2022-2024 de chon thong so (do tung thong so mot, lap 2 vong, bat dau tu ban goc L14).
  - Dem bo thong so chon duoc chay tren 2025-01 -> 2026-10 (du lieu chua thay).
So voi ban chot hien tai (chon bang ca 5 nam) tren cung 2 giai doan.
Lot co dinh, von 3000 USD.
"""
import bisect
from datetime import datetime, timedelta

from bt_rsi_base_h1_xau import indicators
from bt_trendline import run
from trendline_filters import Feat, SESS, f_hours

SPLIT = datetime(2025, 1, 1)
LIMS = {
    "3 lenh deu (M + L33 + L66 x1)": [(0, 1), (0.33, 1), (0.66, 1)],
    "M + L33 x3": [(0, 1), (0.33, 3)],
    "M + L50 x2": [(0, 1), (0.50, 2)],
    "M + L33 x1": [(0, 1), (0.33, 1)],
    "chi market": [(0, 1)],
}
GRID = {
    "L": [8, 9, 10, 11, 12, 14],
    "sl_bars": [2, 3, 4, 5, 6, 7],
    "rsi": [None, (65, 35), (70, 30), (75, 25)],
    "rev": ["always/mo", "loi/khong mo"],
    "lim": list(LIMS),
    "hours": ["tat", "bo 03-07"],
}
START = {"L": 14, "sl_bars": 3, "rsi": None, "rev": "always/mo", "lim": "3 lenh deu (M + L33 + L66 x1)", "hours": "tat"}
FINAL = {"L": 10, "sl_bars": 4, "rsi": (70, 30), "rev": "loi/khong mo", "lim": "M + L33 x3", "hours": "bo 03-07"}


class WF:
    def __init__(self):
        self.F = F = Feat()
        self.parts = {"train": [r for r in F.m5 if r[0] < SPLIT], "test": [r for r in F.m5 if r[0] >= SPLIT]}
        self.ma = indicators([r[4] for r in F.m15])[3]
        self.hours = f_hours(F, SESS["bo 03-07 VN"])
        self.cache = {}

    def exit_map(self, ex_rows, hi, lo):
        ex_t = [r[0] for r in ex_rows]
        out = {}
        for k, r in enumerate(self.F.m15):
            m = self.ma[k]
            if m is None or not (m >= hi or m <= lo):
                continue
            te = r[0] + timedelta(minutes=15)
            if te < ex_t[0] or te > ex_t[-1]:
                continue
            out[bisect.bisect_left(ex_t, te)] = (m >= hi, m <= lo)
        return out

    def run(self, cfg, part):
        key = (tuple(sorted((k, str(v)) for k, v in cfg.items())), part)
        if key in self.cache:
            return self.cache[key]
        F, ex = self.F, self.parts[part]
        mode, ro = ("always", True) if cfg["rev"] == "always/mo" else ("profit", False)
        r = run("M15", F.m15, ex, 3.0, 10.0, 50.0, sig=F.signals(cfg["L"], 1.0), L=cfg["L"],
                sl_bars=cfg["sl_bars"], orders=LIMS[cfg["lim"]], rev_mode=mode, rev_open=ro,
                allow=self.hours if cfg["hours"] == "bo 03-07" else None,
                exit_at=self.exit_map(ex, *cfg["rsi"]) if cfg["rsi"] else None)
        yrs = (ex[-1][0] - ex[0][0]).days / 365.25
        out = {"pnl": r["pnl"], "dd": r["dd"], "per_year": r["pnl"] / 30 / yrs, "years": r["years"],
               "score": r["pnl"] / r["dd"] if r["dd"] else 0.0}
        self.cache[key] = out
        return out


def fmt(name, o):
    ys = " ".join(f"{y % 100}:{v / 30:+4.0f}%" for y, v in sorted(o["years"].items()))
    return f"{name:<14} {o['per_year']:+6.1f}%/nam  DD {o['dd']:5.0f} USD  loi/DD {o['score']:5.2f}  | {ys}"


if __name__ == "__main__":
    W = WF()
    cfg = dict(START)
    print("== Chon thong so CHI tren 2022-2024 (diem = loi / sut von) ==", flush=True)
    for rnd in range(2):
        for p, vals in GRID.items():
            best = None
            for v in vals:
                c = dict(cfg, **{p: v})
                o = W.run(c, "train")
                if best is None or o["score"] > best[0]:
                    best = (o["score"], v)
            cfg[p] = best[1]
            print(f"  vong {rnd + 1}: {p:<8} -> {best[1]}  (loi/DD {best[0]:.2f})", flush=True)
    print("\nBo thong so chon tu 2022-2024:", cfg)
    print("Ban chot hien tai (chon bang 5 nam):", FINAL)
    print()
    for name, c in (("goc (L14...)", START), ("chon 22-24", cfg), ("ban chot", FINAL)):
        print(fmt(name + " train", W.run(c, "train")))
        print(fmt(name + " TEST", W.run(c, "test")), flush=True)
