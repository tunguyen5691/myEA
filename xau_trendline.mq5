//+------------------------------------------------------------------+
//|            xau_trendline - EA PHA TRENDLINE (VANG)               |
//|                                                                  |
//|  Ban rieng cho VANG (XAUUSD). Gan EA nay vao chart XAUUSD.       |
//|  Logic tin hieu chuyen tu "Trendlines with Breaks" [LuxAlgo]     |
//|  (CC BY-NC-SA 4.0 - chi dung ca nhan, khong ban lai).            |
//|                                                                  |
//|  1) TRENDLINE (khung M15, chi xet nen DA DONG):                   |
//|     - Dinh/day (pivot): high/low cao/thap nhat trong 10 nen trai  |
//|       + 10 nen phai -> xac nhan tre 10 nen.                       |
//|     - Do doc = ATR(10, kieu RMA nhu TradingView) / 10 x InpMult.  |
//|     (Backtest 2022-2026: M15 + L=10 + cam gio 3-7h tot nhat)      |
//|     - Tu dinh ke duong GIAM, tu day ke duong TANG.                |
//|  2) TIN HIEU (moi dinh/day chi 1 lan):                            |
//|       nen dong TREN duong giam -> BUY                             |
//|       nen dong DUOI duong tang -> SELL                            |
//|  3) VAO LENH:                                                     |
//|     - SL: BUY -> low thap nhat, SELL -> high cao nhat cua         |
//|       InpSlBars (4) nen vua dong (gom ca nen pha).                |
//|     - d = khoang cach entry -> SL.                                |
//|       d > InpMaxDist       -> keo SL ve dung InpMaxDist gia       |
//|       d < InpMinDistTrade  -> KHONG vao lenh                      |
//|       d < InpMinDistLimits -> chi 1 lenh market                   |
//|       con lai -> 1 market + limit 1 (33% d, lot 0.03), limit 2    |
//|                  tat (InpLimit2Lot = 0)                           |
//|                  % cua d (tinh tu entry ve phia SL)               |
//|     - Ca ro chung SL, KHONG dat TP.                               |
//|     - 03:00-07:59 gio VN (InpNoEntryFrom/To): KHONG vao lenh moi, |
//|       tin hieu nguoc van dong ro cu.                              |
//|     - GIO TIN MY: khong vao lenh moi +-30 phut quanh 8:30 New York|
//|       (CPI, NFP...) moi ngay va 14:00 New York thu 4 (FOMC).      |
//|       Tu tinh gio he My, dua tren TimeGMT().                      |
//|     - LOC XU HUONG: SMA34 > SMA89 (InpTf, nen vua dong) -> chi    |
//|       vao BUY; SMA34 < SMA89 -> chi vao SELL. Tin hieu bi loc VAN |
//|       dung de dong ro nguoc dang loi (muc 4).                     |
//|  4) TIN HIEU NGUOC (dang co ro BUY ma ra SELL, va nguoc lai):     |
//|     - Ro DANG LOI -> dong het + xoa limit, KHONG vao ro moi       |
//|       (cho tin hieu ke tiep).                                     |
//|     - Ro DANG LO  -> GIU ro, bo qua tin hieu (cho RSI / SL).      |
//|     (InpRevOnlyProfit / InpRevOpenNew = false/true -> cach cu:    |
//|      luon dong ro roi vao ro chieu moi.)                          |
//|     Chi 1 ro tai 1 thoi diem. Cung chieu dang co ro -> bo qua.    |
//|     Lenh dong het (dinh SL) -> xoa limit con treo.                |
//|     CHOT LOI RSI BASE (MA do = SMA14 cua RSI14, khung InpTf, nen  |
//|     vua dong): MA >= 70 -> dong ro BUY, MA <= 30 -> dong ro SELL. |
//|  5) NGHI CUOI TUAN + NGAY LE (gio VN = GMT + InpGmtOffsetHours): |
//|     - Cuoi tuan: T6 tu InpFridayStopHour -> T2 InpMondayStartHour |
//|     - Ngay le (InpHolidays, yyyy-mm-dd): tu InpFridayStopHour     |
//|       ngay hom truoc -> InpMondayStartHour ngay hom sau.          |
//|       Le dinh vao T6/T2 thi noi lien voi cuoi tuan.               |
//|     Dau dot nghi: DONG HET lenh + XOA limit cua EA (1 lan moi dot,|
//|     gan lai EA khong dong lai), roi khong vao lenh moi. Tin hieu  |
//|     trong luc nghi bi bo qua. Dong loi -> thu lai sau 30 giay.    |
//|     Danh sach le cua san khac nhau -> tu cap nhat moi nam.        |
//|  Chay duoc tren tai khoan netting va hedging.                     |
//|  Gan EA vao khong vao theo tin hieu cu, cho nen H1 tiep theo.     |
//+------------------------------------------------------------------+
#property copyright "Tunt5"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//--- tham so dau vao
input ENUM_TIMEFRAMES InpTf          = PERIOD_M15; // Khung tinh trendline (backtest tot nhat M15)
input int    InpLength        = 10;      // So nen tim dinh/day (swing lookback)
input double InpMult          = 1.0;     // He so do doc
input int    InpHistBars      = 1500;    // So nen lich su de tinh
input double InpLot           = 0.01;    // Lot lenh market
input int    InpSlBars        = 4;       // SL = low/high cua bao nhieu nen vua dong (backtest: 4 tot nhat)
input double InpMaxDist       = 50.0;    // SL toi da (gia), xa hon -> keo SL ve muc nay
input double InpMinDistTrade  = 3.0;     // d nho hon (gia) -> khong vao lenh
input double InpMinDistLimits = 10.0;    // d nho hon (gia) -> chi 1 lenh market
input double InpLimit1Pct     = 33.0;    // Limit 1: % cua d tinh tu entry
input double InpLimit1Lot     = 0.03;    // Limit 1: lot (0 = tat)
input double InpLimit2Pct     = 66.0;    // Limit 2: % cua d tinh tu entry
input double InpLimit2Lot     = 0.0;     // Limit 2: lot (0 = tat; backtest: khop limit 2 thuong dinh SL)
input int    InpNoEntryFrom   = 3;       // Khong vao lenh moi tu gio nay (gio VN)...
input int    InpNoEntryTo     = 8;       // ...den truoc gio nay (3 -> 8 = 03:00-07:59)
input bool   InpRevOnlyProfit = true;    // Tin hieu nguoc: chi dong ro khi dang loi (lo -> giu)
input bool   InpRevOpenNew    = false;   // Tin hieu nguoc: dong xong co vao ro chieu moi khong
input bool   InpUseNewsFilter = true;    // Khong vao lenh quanh gio tin My
input int    InpNewsWindowMin = 30;      // So phut truoc / sau gio tin
input bool   InpNewsFomc      = true;    // Chan them 14:00 New York thu 4 (FOMC)
input bool   InpUseMaFilter   = true;    // Loc xu huong: MA nhanh > MA cham -> chi BUY, nguoc lai chi SELL
input int    InpMaFast        = 34;      // MA nhanh
input int    InpMaSlow        = 89;      // MA cham
input ENUM_MA_METHOD InpMaMethod = MODE_SMA; // Loai MA (backtest: SMA on dinh hon EMA)
input bool   InpUseRsiExit    = true;    // Chot loi theo RSI base
input int    InpRsiLen        = 14;      // RSI base: chu ky RSI
input int    InpRsiMaLen      = 14;      // RSI base: chu ky MA do (SMA cua RSI)
input double InpRsiExitHigh   = 70.0;    // MA do >= muc nay -> dong ro BUY
input double InpRsiExitLow    = 30.0;    // MA do <= muc nay -> dong ro SELL
input bool   InpPush          = true;    // Push ve dien thoai khi vao lenh
input bool   InpDraw          = true;    // Ve trendline + mui ten pha len chart
input color  InpUpColor       = clrTeal; // Mau duong giam (tu dinh)
input color  InpDnColor       = clrRed;  // Mau duong tang (tu day)
input long   InpMagic         = 20261022; // Magic number cua EA

input string g7 = "--- Nghi cuoi tuan + ngay le ---"; //
input bool   InpUsePause        = true;  // Dong het lenh truoc cuoi tuan / ngay le
input int    InpGmtOffsetHours  = 7;     // Mui gio dia phuong (VN = 7)
input int    InpFridayStopHour  = 17;    // Gio dung (T6 / ngay truoc le)
input int    InpMondayStartHour = 6;     // Gio chay lai (T2 / ngay sau le)
input string InpHolidays        = "2026-11-26,2026-12-25,2027-01-01"; // Ngay le (gio VN), cach nhau dau phay

CTrade   g_trade;
int      g_rsiHandle  = INVALID_HANDLE;   // iRSI khung InpTf
int      g_maFast     = INVALID_HANDLE;   // MA nhanh khung InpTf
int      g_maSlow     = INVALID_HANDLE;   // MA cham khung InpTf
datetime g_lastBar    = 0;
datetime g_holidays[];              // 00:00 cac ngay le (gio dia phuong)
bool     g_pause      = false;      // dang trong dot nghi
datetime g_pauseFail  = 0;          // lan dong that bai gan nhat (thu lai sau 30 giay)

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpLength < 2 || InpHistBars < InpLength * 10 || InpSlBars < 1)
      return(INIT_PARAMETERS_INCORRECT);

   if(!ParseHolidays())
      return(INIT_PARAMETERS_INCORRECT);
   if(InpUseRsiExit)
   {
      g_rsiHandle = iRSI(_Symbol, InpTf, InpRsiLen, PRICE_CLOSE);
      if(g_rsiHandle == INVALID_HANDLE)
      {
         Alert("xau_trendline: tao iRSI loi ", GetLastError());
         return(INIT_FAILED);
      }
   }
   if(InpUseMaFilter)
   {
      g_maFast = iMA(_Symbol, InpTf, InpMaFast, 0, InpMaMethod, PRICE_CLOSE);
      g_maSlow = iMA(_Symbol, InpTf, InpMaSlow, 0, InpMaMethod, PRICE_CLOSE);
      if(g_maFast == INVALID_HANDLE || g_maSlow == INVALID_HANDLE)
      {
         Alert("xau_trendline: tao iMA loi ", GetLastError());
         return(INIT_FAILED);
      }
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   // bo qua tin hieu cua nen vua dong luc gan EA, chi ve len chart
   g_lastBar = iTime(_Symbol, InpTf, 1);
   bool b, s;
   CalcSignals(b, s);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_rsiHandle != INVALID_HANDLE)
      IndicatorRelease(g_rsiHandle);
   if(g_maFast != INVALID_HANDLE)
      IndicatorRelease(g_maFast);
   if(g_maSlow != INVALID_HANDLE)
      IndicatorRelease(g_maSlow);
   ObjectsDeleteAll(0, "xtl_");
   ChartRedraw();
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(CheckPause())
   {
      g_lastBar = iTime(_Symbol, InpTf, 1);   // bo qua tin hieu trong luc nghi
      return;
   }

   // ro da dong het -> xoa limit con treo
   CleanPending(true);
   CleanPending(false);

   datetime bar = iTime(_Symbol, InpTf, 1);
   if(bar == 0 || bar == g_lastBar)
      return;

   bool buySig, sellSig;
   if(!CalcSignals(buySig, sellSig))
      return;               // lich su chua du -> thu lai tick sau
   g_lastBar = bar;

   // chot loi RSI base (truoc khi xet tin hieu moi, giong backtest)
   double ma;
   if(InpUseRsiExit && RsiBaseMa(ma))
   {
      if(ma >= InpRsiExitHigh && HasBasket(true))
         CloseBasket(true, StringFormat("chot loi RSI base %.1f >= %.0f", ma, InpRsiExitHigh));
      if(ma <= InpRsiExitLow && HasBasket(false))
         CloseBasket(false, StringFormat("chot loi RSI base %.1f <= %.0f", ma, InpRsiExitLow));
   }

   // ca 2 cung ra 1 nen -> khong ro chieu, bo qua
   if(buySig == sellSig)
      return;
   bool isBuy = buySig;
   if(HasBasket(isBuy))
      return;               // dang co ro cung chieu
   if(HasBasket(!isBuy))
   {
      double fl = BasketProfit(!isBuy);
      if(InpRevOnlyProfit && fl <= 0)
      {
         PrintFormat("xau_trendline: tin hieu %s nhung ro %s dang lo %.2f -> giu ro, bo qua",
                     isBuy ? "BUY" : "SELL", isBuy ? "SELL" : "BUY", fl);
         return;
      }
      if(!CloseBasket(!isBuy, StringFormat("tin hieu nguoc (ro %+.2f USD)", fl)))
         return;            // dong ro nguoc chua xong -> khong vao
      if(!InpRevOpenNew)
         return;            // chot xong, cho tin hieu ke tiep
   }
   if(InNoEntryHours())
   {
      PrintFormat("xau_trendline: tin hieu %s trong gio cam vao lenh (%dh-%dh VN) -> bo qua",
                  isBuy ? "BUY" : "SELL", InpNoEntryFrom, InpNoEntryTo);
      return;               // van dong ro nguoc o tren, chi khong vao moi
   }
   if(InpUseNewsFilter && InNewsWindow())
   {
      PrintFormat("xau_trendline: tin hieu %s gan gio tin My (+-%d phut) -> bo qua",
                  isBuy ? "BUY" : "SELL", InpNewsWindowMin);
      return;
   }
   if(InpUseMaFilter && !MaAllows(isBuy))
      return;               // nguoc xu huong MA -> khong vao (da xet dong ro o tren)

   // SL = low/high cua InpSlBars nen vua dong
   int    k  = isBuy ? iLowest(_Symbol, InpTf, MODE_LOW, InpSlBars, 1)
                     : iHighest(_Symbol, InpTf, MODE_HIGH, InpSlBars, 1);
   double sl = 0;
   if(k >= 0)
      sl = isBuy ? iLow(_Symbol, InpTf, k) : iHigh(_Symbol, InpTf, k);
   OpenBasket(isBuy, sl);
}

//--- MA do RSI base cua nen vua dong = trung binh InpRsiMaLen gia tri RSI (nen 1..N)
bool RsiBaseMa(double &ma)
{
   double buf[];
   if(CopyBuffer(g_rsiHandle, 0, 1, InpRsiMaLen, buf) != InpRsiMaLen)
   {
      Print("xau_trendline: chua doc duoc RSI (", GetLastError(), ") -> bo qua chot loi RSI nen nay");
      return(false);
   }
   ma = 0;
   for(int i = 0; i < InpRsiMaLen; i++)
      ma += buf[i];
   ma /= InpRsiMaLen;
   return(true);
}

//--- Ngay CN thu n (1 = dau tien) cua thang, 00:00
datetime NthSunday(int year, int mon, int n)
{
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year; d.mon = mon; d.day = 1;
   datetime t = StructToTime(d);
   TimeToStruct(t, d);
   int first = (7 - d.day_of_week) % 7;           // so ngay toi CN dau tien
   return(t + (first + 7 * (n - 1)) * 86400);
}

//--- Gio he My: CN thu 2 thang 3 -> CN dau thang 11
bool UsDst(datetime gmt)
{
   MqlDateTime d;
   TimeToStruct(gmt, d);
   return(gmt >= NthSunday(d.year, 3, 2) && gmt < NthSunday(d.year, 11, 1));
}

//--- Dang trong khung +-InpNewsWindowMin phut quanh gio tin My (8:30 NY moi ngay, 14:00 NY thu 4)
bool InNewsWindow()
{
   datetime now = TimeGMT();
   MqlDateTime d;
   TimeToStruct(now, d);
   if(d.day_of_week == 0 || d.day_of_week == 6)
      return(false);
   int off = UsDst(now) ? 4 : 5;                  // NY = GMT - off
   datetime day0 = now - now % 86400;
   int win = InpNewsWindowMin * 60;
   datetime rel = day0 + (8 * 3600 + 30 * 60) + off * 3600;
   if(MathAbs((double)(now - rel)) <= win)
      return(true);
   if(InpNewsFomc && d.day_of_week == 3)
   {
      rel = day0 + 14 * 3600 + off * 3600;
      if(MathAbs((double)(now - rel)) <= win)
         return(true);
   }
   return(false);
}

//--- Loc xu huong: nen vua dong MA nhanh > MA cham -> cho BUY, < -> cho SELL
bool MaAllows(bool isBuy)
{
   double f[], s[];
   if(CopyBuffer(g_maFast, 0, 1, 1, f) != 1 || CopyBuffer(g_maSlow, 0, 1, 1, s) != 1)
   {
      Print("xau_trendline: chua doc duoc MA (", GetLastError(), ") -> khong vao lenh nen nay");
      return(false);
   }
   bool ok = isBuy ? f[0] > s[0] : f[0] < s[0];
   if(!ok)
      PrintFormat("xau_trendline: tin hieu %s nguoc xu huong MA%d %.2f / MA%d %.2f -> bo qua",
                  isBuy ? "BUY" : "SELL", InpMaFast, f[0], InpMaSlow, s[0]);
   return(ok);
}

//--- Gio VN hien tai nam trong khung cam vao lenh moi (chuyen phien, spread gian)
bool InNoEntryHours()
{
   if(InpNoEntryFrom == InpNoEntryTo)
      return(false);
   MqlDateTime dt;
   TimeToStruct(TimeGMT() + InpGmtOffsetHours * 3600, dt);
   if(InpNoEntryFrom < InpNoEntryTo)
      return(dt.hour >= InpNoEntryFrom && dt.hour < InpNoEntryTo);
   return(dt.hour >= InpNoEntryFrom || dt.hour < InpNoEntryTo);   // qua nua dem
}

//+------------------------------------------------------------------+
//|                    NGHI CUOI TUAN + NGAY LE                      |
//+------------------------------------------------------------------+
//--- Tach InpHolidays "yyyy-mm-dd,..." thanh mang ngay
bool ParseHolidays()
{
   ArrayResize(g_holidays, 0);
   string parts[];
   int n = StringSplit(InpHolidays, ',', parts);
   for(int i = 0; i < n; i++)
   {
      string s = parts[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "") continue;
      StringReplace(s, "-", ".");
      datetime d = StringToTime(s);
      if(d <= 0)
      {
         Alert("xau_trendline: ngay le '", parts[i], "' sai dinh dang (dung yyyy-mm-dd)");
         return(false);
      }
      int k = ArraySize(g_holidays);
      ArrayResize(g_holidays, k + 1);
      g_holidays[k] = d - d % 86400;
   }
   return(true);
}

//--- Thoi diem local (gio dia phuong) co nam trong dot nghi khong
bool IsPausedAt(datetime local)
{
   MqlDateTime dt;
   TimeToStruct(local, dt);
   if((dt.day_of_week == 5 && dt.hour >= InpFridayStopHour) ||
      dt.day_of_week == 6 || dt.day_of_week == 0 ||
      (dt.day_of_week == 1 && dt.hour < InpMondayStartHour))
      return(true);

   for(int i = 0; i < ArraySize(g_holidays); i++)
   {
      datetime from = g_holidays[i] - 86400 + InpFridayStopHour * 3600;
      datetime to   = g_holidays[i] + 86400 + InpMondayStartHour * 3600;
      if(local >= from && local < to)
         return(true);
   }
   return(false);
}

//--- Moc bat dau cua dot nghi dang chua local (lui tung gio)
datetime PauseStart(datetime local)
{
   datetime t = local - local % 3600;
   for(int k = 0; k < 24 * 14 && IsPausedAt(t - 3600); k++)
      t -= 3600;
   return(t);
}

//--- true = dang nghi (EA khong vao lenh). Dau dot nghi: dong het ro, 1 lan moi dot
bool CheckPause()
{
   if(!InpUsePause)
      return(false);

   datetime local = TimeGMT() + InpGmtOffsetHours * 3600;
   bool pause = IsPausedAt(local);
   if(pause != g_pause)
   {
      g_pause = pause;
      Notify(pause ? "xau_trendline " + _Symbol + ": BAT DAU NGHI (cuoi tuan / le) -> dong het lenh"
                   : "xau_trendline " + _Symbol + ": HET NGHI -> chay lai binh thuong");
   }
   if(!pause)
      return(false);

   // da dong xong dot nay (luu GV de gan lai EA / khoi dong lai may khong dong lai)
   datetime start = PauseStart(local);
   string gv = "XTL_PAUSE_" + _Symbol + "_" + IntegerToString(InpMagic);
   if(GlobalVariableCheck(gv) && (datetime)GlobalVariableGet(gv) == start)
      return(true);
   if(TimeLocal() - g_pauseFail < 30)
      return(true);         // vua that bai (vd thi truong da dong) -> doi 30 giay

   bool ok    = true;
   bool quiet = (g_pauseFail != 0);   // dang thu lai -> khong push lap
   if(HasBasket(true)  && !CloseBasket(true,  "nghi cuoi tuan / le", quiet)) ok = false;
   if(HasBasket(false) && !CloseBasket(false, "nghi cuoi tuan / le", quiet)) ok = false;
   if(!ok)
   {
      g_pauseFail = TimeLocal();
      return(true);
   }
   g_pauseFail = 0;
   GlobalVariableSet(gv, (double)start);
   return(true);
}

//--- Ghi log + push ve dien thoai
void Notify(string msg)
{
   Print(msg);
   if(InpPush && !MQLInfoInteger(MQL_TESTER) && TerminalInfoInteger(TERMINAL_NOTIFICATIONS_ENABLED))
      SendNotification(msg);
}

//+------------------------------------------------------------------+
//| Dong het lenh chay + xoa limit cua 1 chieu                       |
//+------------------------------------------------------------------+
bool CloseBasket(bool isBuy, string reason, bool quiet = false)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if((isBuy && type == POSITION_TYPE_BUY) || (!isBuy && type == POSITION_TYPE_SELL))
         if(!g_trade.PositionClose(t))
            PrintFormat("xau_trendline: dong lenh %I64u loi %d %s", t,
                        g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
   }
   CleanPending(isBuy);

   bool done = !HasBasket(isBuy);
   if(!quiet)
      Notify(StringFormat("xau_trendline %s %s -> dong ro %s%s", _Symbol, reason,
                          isBuy ? "BUY" : "SELL", done ? "" : " (CHUA DONG HET, thu lai)"));
   return(done);
}

//+------------------------------------------------------------------+
//| Tinh trendline tren nen da dong, tra tin hieu cua nen vua dong   |
//+------------------------------------------------------------------+
bool CalcSignals(bool &buySig, bool &sellSig)
{
   buySig = sellSig = false;

   int n = InpHistBars;
   int L = InpLength;
   double h[], l[], c[];
   datetime tm[];
   // lay tu nen 1 (da dong), mang cu -> moi
   if(CopyHigh(_Symbol, InpTf, 1, n, h) != n) return(false);
   if(CopyLow(_Symbol, InpTf, 1, n, l) != n) return(false);
   if(CopyClose(_Symbol, InpTf, 1, n, c) != n) return(false);
   if(CopyTime(_Symbol, InpTf, 1, n, tm) != n) return(false);

   double atr = 0, upper = 0, lower = 0, slopePH = 0, slopePL = 0;
   int    upos = 0, dnos = 0, prevUpos = 0, prevDnos = 0;
   int    phIdx = -1, plIdx = -1;   // nen dinh/day gan nhat (de ve)
   if(InpDraw)
      ObjectsDeleteAll(0, "xtl_");

   for(int i = 0; i < n; i++)
   {
      // ATR kieu RMA (giong ta.atr cua TradingView)
      double tr = h[i] - l[i];
      if(i > 0)
         tr = MathMax(tr, MathMax(MathAbs(h[i] - c[i - 1]), MathAbs(l[i] - c[i - 1])));
      if(i < L)
      {
         atr += tr / L;     // nen dau: trung binh cong
         continue;
      }
      atr = (atr * (L - 1) + tr) / L;
      double slope = atr / L * InpMult;

      // pivot tai nen i-L, xac nhan o nen i
      bool isPH = false, isPL = false;
      int  p = i - L;
      if(p >= L)
      {
         isPH = isPL = true;
         for(int j = p - L; j <= i; j++)
         {
            if(j == p) continue;
            if(h[j] >= h[p]) isPH = false;
            if(l[j] <= l[p]) isPL = false;
         }
      }

      if(isPH) { slopePH = slope; upper = h[p]; phIdx = p; }
      else       upper -= slopePH;
      if(isPL) { slopePL = slope; lower = l[p]; plIdx = p; }
      else       lower += slopePL;

      prevUpos = upos;
      prevDnos = dnos;
      // gia tri duong tai nen i = upper - slope x L (duong bat dau tu nen p)
      if(isPH)                              upos = 0;
      else if(c[i] > upper - slopePH * L)  upos = 1;
      if(isPL)                              dnos = 0;
      else if(c[i] < lower + slopePL * L)  dnos = 1;

      // mui ten pha (bo qua doan dau chua co dinh/day that)
      if(InpDraw && phIdx >= 0 && upos > prevUpos)
         DrawArrow(true, tm[i], l[i]);
      if(InpDraw && plIdx >= 0 && dnos > prevDnos)
         DrawArrow(false, tm[i], h[i]);
   }

   // trendline hien tai: tu dinh/day, doc moi nen = slope, keo dai sang phai
   if(InpDraw && phIdx >= 0)
      DrawLine("xtl_up", tm[phIdx], h[phIdx], tm[phIdx + 1], h[phIdx] - slopePH, InpUpColor);
   if(InpDraw && plIdx >= 0)
      DrawLine("xtl_dn", tm[plIdx], l[plIdx], tm[plIdx + 1], l[plIdx] + slopePL, InpDnColor);
   if(InpDraw)
      ChartRedraw();

   buySig  = upos > prevUpos;
   sellSig = dnos > prevDnos;
   return(true);
}

//+------------------------------------------------------------------+
//|                         VE LEN CHART                             |
//+------------------------------------------------------------------+
void DrawLine(string name, datetime t1, double p1, datetime t2, double p2, color clr)
{
   ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
}

//--- Mui ten pha: BUY duoi nen, SELL tren nen
void DrawArrow(bool isBuy, datetime t, double price)
{
   string name = "xtl_B_" + (isBuy ? "up_" : "dn_") + IntegerToString((long)t);
   ObjectCreate(0, name, OBJ_ARROW, 0, t, price);
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, isBuy ? 233 : 234);
   ObjectSetInteger(0, name, OBJPROP_COLOR, isBuy ? InpUpColor : InpDnColor);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, isBuy ? ANCHOR_TOP : ANCHOR_BOTTOM);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
//| Vao 1 market + toi da 2 limit, chung SL va TP                    |
//+------------------------------------------------------------------+
void OpenBasket(bool isBuy, double sl)
{
   string side  = isBuy ? "BUY" : "SELL";
   double entry = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                        : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double d     = isBuy ? entry - sl : sl - entry;
   double minStop = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;

   if(sl <= 0 || d < InpMinDistTrade || d <= minStop)
   {
      PrintFormat("xau_trendline: tin hieu %s bo qua, SL %.2f cach entry %.2f (d=%.2f qua nho)",
                  side, sl, entry, d);
      return;
   }
   if(InpMaxDist > 0 && d > InpMaxDist)
   {
      PrintFormat("xau_trendline: SL %s %.2f qua xa (d=%.2f) -> keo ve %.2f gia",
                  side, sl, d, InpMaxDist);
      d  = InpMaxDist;
      sl = isBuy ? entry - d : entry + d;
   }

   sl = NormalizeDouble(sl, _Digits);
   double tp = 0;           // khong TP, chot bang tin hieu nguoc
   string cmt = "xtl " + side;

   bool ok = isBuy ? g_trade.Buy(InpLot, _Symbol, 0, sl, tp, cmt)
                   : g_trade.Sell(InpLot, _Symbol, 0, sl, tp, cmt);
   if(!ok || g_trade.ResultRetcode() != TRADE_RETCODE_DONE)
   {
      PrintFormat("xau_trendline: vao %s loi %d %s", side,
                  g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      return;
   }

   int nLim = 0;
   if(d >= InpMinDistLimits)
   {
      double pct[2], lots[2];
      pct[0] = InpLimit1Pct;  lots[0] = InpLimit1Lot;
      pct[1] = InpLimit2Pct;  lots[1] = InpLimit2Lot;
      double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      for(int k = 0; k < 2; k++)
      {
         double lot = MathRound(lots[k] / step) * step;
         if(lot < SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN))
            continue;       // limit nay tat
         double off   = d * pct[k] / 100.0;
         double price = NormalizeDouble(isBuy ? entry - off : entry + off, _Digits);
         // limit phai cach gia hien tai va SL du stops level
         if(off <= minStop || d - off <= minStop)
            continue;
         bool lok = isBuy ? g_trade.BuyLimit(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt)
                          : g_trade.SellLimit(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt);
         if(lok && g_trade.ResultRetcode() == TRADE_RETCODE_DONE)
            nLim++;
         else
            PrintFormat("xau_trendline: dat %s limit %.2f loi %d %s", side, price,
                        g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      }
   }

   Notify(StringFormat("xau_trendline %s %s %.2f SL %.2f d=%.2f, %d limit",
                       _Symbol, side, entry, sl, d, nLim));
}

//+------------------------------------------------------------------+
//| Chieu nay dang co lenh chay hoac limit treo cua EA khong         |
//+------------------------------------------------------------------+
bool HasBasket(bool isBuy)
{
   return(CountPositions(isBuy) > 0 || CountPending(isBuy) > 0);
}

//--- Lai/lo dang chay (USD) cua cac lenh chieu nay
double BasketProfit(bool isBuy)
{
   double sum = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if((isBuy && type == POSITION_TYPE_BUY) || (!isBuy && type == POSITION_TYPE_SELL))
         sum += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return(sum);
}

int CountPositions(bool isBuy)
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if((isBuy && type == POSITION_TYPE_BUY) || (!isBuy && type == POSITION_TYPE_SELL))
         cnt++;
   }
   return(cnt);
}

int CountPending(bool isBuy)
{
   int cnt = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong t = OrderGetTicket(i);
      if(t == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      long type = OrderGetInteger(ORDER_TYPE);
      if((isBuy && type == ORDER_TYPE_BUY_LIMIT) || (!isBuy && type == ORDER_TYPE_SELL_LIMIT))
         cnt++;
   }
   return(cnt);
}

//+------------------------------------------------------------------+
//| Het lenh chay cua chieu nay -> xoa limit con treo                |
//+------------------------------------------------------------------+
void CleanPending(bool isBuy)
{
   if(CountPositions(isBuy) > 0)
      return;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong t = OrderGetTicket(i);
      if(t == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      long type = OrderGetInteger(ORDER_TYPE);
      if((isBuy && type == ORDER_TYPE_BUY_LIMIT) || (!isBuy && type == ORDER_TYPE_SELL_LIMIT))
         g_trade.OrderDelete(t);
   }
}
//+------------------------------------------------------------------+
