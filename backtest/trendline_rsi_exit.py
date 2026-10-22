"""
Thu chot loi xau_trendline bang RSI base (duong MA do = SMA14 cua RSI14, giong rsi_based.mq5).
Cau hinh nen: M15, L=10, bo vao lenh 03-07h VN, 2 limit, nguong 3/10/50.
Xet MA cua nen RSI-TF vua DONG, dong ro o open nen M5 ke tiep:
  BUY dong khi MA >= hi, SELL dong khi MA <= lo. Tin hieu nguoc / SL / nghi cuoi tuan van giu.
"""
import bisect
from datetime import timedelta

from bt_rsi_base_h1_xau import indicators
from trendline_filters import Feat, SESS, TH, NO_LIM, evaluate, f_hours


def exit_map(F, rows, tf_min, hi, lo):
    ma = indicators([r[4] for r in rows])[3]
    ex_t = [r[0] for r in F.m5]
    out = {}
    for k, r in enumerate(rows):
        if ma[k] is None:
            continue
        cb, cs = ma[k] >= hi, ma[k] <= lo
        if cb or cs:
            j = bisect.bisect_left(ex_t, r[0] + timedelta(minutes=tf_min))
            out[j] = (cb, cs)
    return out


def exit_map_peak(F, rows, tf_min, hi, lo):
    """Logic 3 nen cua rsi_base_h1_xau: nen 0 = vua dong, nen 1, nen 2 truoc do.
    BUY dong khi MA tao DINH (nen1 > nen0, nen1 > nen2, nen1 > hi);
    SELL dong khi MA tao DAY (nen1 < nen0, nen1 < nen2, nen1 < lo)."""
    ma = indicators([r[4] for r in rows])[3]
    ex_t = [r[0] for r in F.m5]
    out = {}
    for k in range(2, len(rows)):
        m0, m1, m2 = ma[k], ma[k - 1], ma[k - 2]
        if m0 is None or m1 is None or m2 is None:
            continue
        cb = m1 > m0 and m1 > m2 and m1 > hi
        cs = m1 < m0 and m1 < m2 and m1 < lo
        if cb or cs:
            j = bisect.bisect_left(ex_t, rows[k][0] + timedelta(minutes=tf_min))
            out[j] = (cb, cs)
    return out


def peak_test(F):
    base = dict(allow=f_hours(F, SESS["bo 03-07 VN"]), L=10)
    evaluate(F, "goc: khong chot RSI", **base)
    evaluate(F, "RSI M15 cham 70/30 (lan truoc)", exit_at=exit_map(F, F.m15, 15, 70, 30), **base)
    for tfn, rows, m in (("M15", F.m15, 15), ("H1", F.h1, 60)):
        for hi, lo in ((60, 40), (65, 35), (70, 30)):
            ex = exit_map_peak(F, rows, m, hi, lo)
            for po in (False, True):
                name = f"3 nen {tfn} dinh>{hi}/day<{lo}" + (" chi khi loi" if po else "")
                evaluate(F, name, exit_at=ex, exit_profit_only=po, **base)


if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "peak":
    peak_test(Feat())
elif __name__ == "__main__":
    F = Feat()
    allow = f_hours(F, SESS["bo 03-07 VN"])
    base = dict(allow=allow, L=10)
    evaluate(F, "goc: khong chot RSI", **base)
    for tfn, rows, m in (("M15", F.m15, 15), ("H1", F.h1, 60)):
        for hi, lo in ((50, 50), (60, 40), (70, 30)):
            ex = exit_map(F, rows, m, hi, lo)
            for po in (False, True):
                name = f"RSI {tfn} {hi}/{lo}" + (" chi khi loi" if po else "")
                evaluate(F, name, exit_at=ex, exit_profit_only=po, **base)
    # ban khong limit voi 2 cau hinh RSI tot (tham khao)
    for tfn, rows, m, hi, lo in (("H1", F.h1, 60, 70, 30), ("M15", F.m15, 15, 70, 30)):
        ex = exit_map(F, rows, m, hi, lo)
        evaluate(F, f"RSI {tfn} {hi}/{lo} chi khi loi, 0lim", th=NO_LIM, exit_at=ex,
                 exit_profit_only=True, **base)
