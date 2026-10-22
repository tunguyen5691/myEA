"""Thu moi cach xu ly cuoi tuan + stress gap gia dinh. Von $5k, swap 40, spread 0.30."""
import sys
import factor_search as F
from bt_rsi_base_h1_xau import run, MULTS

D = F.D
GAPS = (100, 150, 200)
for n in (300,):
    F.REG[n] = F.reg_slope(n)

POL = {
    "giu het": False,
    "dong het (EA goc)": True,
    "giu, khong vao moi": lambda d: "keep",
    "xoa limit, giu lenh": lambda d: "cutpend",
    "dong neu dang nguoc >0": lambda d: "close" if d["adverse"] > 0 else "keep",
    "dong neu nguoc >25": lambda d: "close" if d["adverse"] > 25 else "keep",
    "dong neu nguoc >50": lambda d: "close" if d["adverse"] > 50 else "keep",
    "dong neu nguoc >75": lambda d: "close" if d["adverse"] > 75 else "keep",
    "dong neu khop >=1 limit": lambda d: "close" if d["filled"] >= 1 else "keep",
    "dong neu khop >=5 limit": lambda d: "close" if d["filled"] >= 5 else "keep",
    "dong neu khop >=10 limit": lambda d: "close" if d["filled"] >= 10 else "keep",
    "dong neu dang lo": lambda d: "close" if d["floating"] < 0 else "keep",
    "dong neu dang loi": lambda d: "close" if d["floating"] > 0 else "keep",
    "xoa limit + dong neu nguoc >25": lambda d: "close" if d["adverse"] > 25 else "cutpend",
    "xoa limit + dong neu dang lo": lambda d: "close" if d["floating"] < 0 else "cutpend",
}
CFG = {"HQ240": F.f_reg(240), "HQ300": F.f_reg(300), "HQ480": F.f_reg(480)}


def shock(x, g):
    pr = x['probe'][g]
    if not pr:
        return 0.0
    return max((pre - hypo) / (D + pre) * 100 for _, pre, hypo in pr)


if __name__ == "__main__":
    lots = [float(a) for a in sys.argv[1:]] or [0.1]
    for cfg, allow in CFG.items():
        for lot in lots:
            print(f"\n== {cfg} | luoi 1->7 | SL125 | MA50 | 60/40 | lot {lot}")
            print(f"{'cach xu ly cuoi tuan':32} | loi%   | DD%   | so tuan giu ro | gap nguoc 100/150/200 lam mat (% equity)")
            for name, pol in POL.items():
                x = run(F.rows, lot, 0.30, deposit=D, swap=40, allow=allow, mults=MULTS, sl=125, reverse=False,
                        weekend=pol, gap_probe=GAPS)
                if x['blown']:
                    print(f"{name:32} | CHAY {x['blown']:%Y-%m-%d}")
                    continue
                print(f"{name:32} | {x['profit'] / D * 100:+5.0f}% | {x['max_dd_pct']:4.1f}% | {len(x['probe'][100]):4} | "
                      + " / ".join(f"{shock(x, g):4.0f}%" for g in GAPS))
            sys.stdout.flush()
