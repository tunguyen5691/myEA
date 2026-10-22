"""Tang lot theo von cho ban chot xau_trendline (SL 4 nen, M0.01 + L33 0.03, RSI 70/30, nguoc chi dong khi loi)."""
from trendline_rsi_exit import Feat, SESS, TH, exit_map, f_hours
from bt_trendline import run

if __name__ == "__main__":
    F = Feat()
    base = dict(allow=f_hours(F, SESS["bo 03-07 VN"]), L=10, exit_at=exit_map(F, F.m15, 15, 70, 30),
                rev_mode="profit", rev_open=False, sig=F.signals(10, 1.0), orders=[(0, 1), (0.33, 3)],
                sl_bars=4)
    yrs = (F.m5[-1][0] - F.m5[0][0]).days / 365.25
    for name, kw in (("lot co dinh", {}),
                     ("bac: x1 moi 3000 USD", dict(scale_per=3000)),
                     ("ty le: lot theo von/3000", dict(scale_per=3000, scale_mode="prop")),
                     ("ty le: lot theo von/4000 (nhe hon)", dict(scale_per=4000, scale_mode="prop")),
                     ("ty le: lot theo von/6000 (nhe nua)", dict(scale_per=6000, scale_mode="prop"))):
        r = run("M15", F.m15, F.m5, *TH, **base, **kw)
        cagr = (r["end"] / 3000) ** (1 / yrs) - 1
        # von cuoi tung nam
        bal, ends = 3000.0, []
        for y in range(2022, 2027):
            bal += r["years"].get(y, 0)
            ends.append(bal)
        worst = min(b[2] for b in r["baskets"])
        print(f"{name:<36} von cuoi {r['end']:9.0f}  lai kep {cagr*100:5.1f}%/nam  sut von max {r['dd_rel']:3.0f}% "
              f"({r['dd']:6.0f} USD)  ro lo nhat {worst:6.0f} | cuoi nam: "
              + " ".join(f"{y%100}:{e:7.0f}" for y, e in zip(range(2022, 2027), ends)), flush=True)
