"""
Thu cau truc lenh cua ro (market + limit, he so lot) cho xau_trendline ban hien tai:
M15, L=10, bo 03-07h VN, chot loi RSI 70/30, tin hieu nguoc chi dong khi loi + khong vao moi.
orders = [(pct, he so lot)], pct 0 = market. Khi d < 10 van chi 1 market x1 (tru khi nang min_trade).
"""
from trendline_rsi_exit import Feat, SESS, TH, evaluate, exit_map, f_hours

VARIANTS = [
    ("hien tai: M1 + L33 x1 + L66 x1", [(0, 1), (0.33, 1), (0.66, 1)]),
    ("M1 + L33 x1 (bo L66)",           [(0, 1), (0.33, 1)]),
    ("M1 + L33 x2",                    [(0, 1), (0.33, 2)]),
    ("M1 + L33 x3",                    [(0, 1), (0.33, 3)]),
    ("M1 + L25 x2",                    [(0, 1), (0.25, 2)]),
    ("M1 + L50 x2",                    [(0, 1), (0.50, 2)]),
    ("M1 + L33 x2 + L66 x1",           [(0, 1), (0.33, 2), (0.66, 1)]),
    ("chi limit: L33 x1",              [(0.33, 1)]),
    ("chi limit: L33 x2",              [(0.33, 2)]),
    ("chi limit: L25 x2",              [(0.25, 2)]),
    ("chi limit: L33 x1 + L66 x1",     [(0.33, 1), (0.66, 1)]),
]

if __name__ == "__main__":
    F = Feat()
    base = dict(allow=f_hours(F, SESS["bo 03-07 VN"]), L=10, exit_at=exit_map(F, F.m15, 15, 70, 30),
                rev_mode="profit", rev_open=False)
    for name, orders in VARIANTS:
        evaluate(F, name, orders=orders, **base)
    print("--- bo ro 1 lenh (chi vao khi d >= 10) ---")
    for name, orders in VARIANTS[:3] + VARIANTS[7:9]:
        evaluate(F, name + " | d>=10", th=(10.0, 10.0, 50.0), orders=orders, **base)
