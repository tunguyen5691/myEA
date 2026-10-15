//+------------------------------------------------------------------+
//|            rsi_base_h1_xau - LUOI LIMIT TU DAT (VANG)            |
//|                                                                  |
//|  Ban rieng cho VANG (XAUUSD). Gan EA nay vao chart XAUUSD.       |
//|  Cap kia dung file rsi_base_h1_btc.                              |
//|                                                                  |
//|  1) Anh VAO LENH TAY (BUY hoac SELL) -> EA dat san cac lenh LIMIT|
//|     cung chieu, cach nhau 1 buoc gia: 5 gia                      |
//|       BUY  -> Buy Limit  ben DUOI gia lenh tay                   |
//|       SELL -> Sell Limit ben TREN gia lenh tay                   |
//|  2) 20 lenh limit, lot = lot LENH TAY x he so trong danh sach:   |
//|       he so 1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7              |
//|       lenh tay 0.01 -> 0.01 0.01 0.01 0.02 ... 0.07 0.07         |
//|     So lenh limit = so phan tu trong danh sach he so.            |
//|     Luoi tran: 20 x 5 = 100 gia.                                 |
//|                                                                  |
//|  Chi phan ung voi lenh anh vao tay (terminal / dien thoai / web), |
//|  KHONG phan ung voi lenh cua EA khac. Lenh dang co luc gan EA bi  |
//|  bo qua (khong dat luoi cho lenh cu).                             |
//|  Luoi chi dat khi symbol chua co lenh/lenh cho cua EA nay.        |
//|                                                                  |
//|  3) DONG RO (kiem tra MOI TICK): doc duong MA DO (buffer 1) cua   |
//|     indicator rsi_based khung H1, nen H1 DANG CHAY:               |
//|       MA >= 50 -> dong TAT CA lenh BUY + xoa Buy Limit cua EA     |
//|       MA <= 50 -> dong TAT CA lenh SELL + xoa Sell Limit cua EA   |
//|     "Lenh" = lenh tay + lenh cua EA nay tren symbol chart.        |
//|     Vao BUY luc MA dang >= 50 (SELL luc <= 50) -> bi dong ngay.   |
//|     Can file rsi_based.ex5 trong MQL5\Indicators.                 |
//|                                                                  |
//|  4) CANH BAO (popup + push dien thoai):                            |
//|     a) EA dong ro theo MA 50 -> bao.                              |
//|     b) Tin hieu vao lenh, xet khi nen H1 vua dong, duong MA do:   |
//|        nen 0 = vua dong, nen 1 = truoc 1 cay, nen 2 = truoc 2 cay |
//|        DINH: nen 1 > nen 0 va nen 1 > nen 2, nen 1 > 60 -> SELL   |
//|        DAY : nen 1 < nen 0 va nen 1 < nen 2, nen 1 < 40 -> BUY    |
//|        Moi nen H1 chi bao 1 lan (gan lai EA khong bao lai).       |
//|        Dang co lenh (chay hoac cho) tren symbol -> KHONG bao,     |
//|        KHONG vao lenh.                                            |
//|     c) TU VAO LENH: co tin hieu -> EA vao lenh market lot         |
//|        InpAutoLot, roi rai luoi limit y nhu lenh tay.             |
//|        InpAutoLot = 0 -> chi BAO, khong vao lenh.                 |
//|        MA dang chay da cham muc dong ro -> khong vao (vao         |
//|        xong se bi dong ngay).                                     |
//|                                                                  |
//|  5) CHONG DU LIEU LOI: lich su H1 dang dong bo lai (vd luc broker  |
//|     qua ngay moi), indicator chua tinh xong, hoac RSI base nhay    |
//|     qua InpMaxJump diem -> KHONG dong ro, KHONG bao tin hieu.      |
//|                                                                  |
//|  6) NGHI CUOI TUAN (gio VN = GMT + InpGmtOffsetHours):            |
//|     T6 17h -> DONG HET lenh dang chay (lenh tay + lenh EA) va XOA |
//|     het lenh limit cua EA tren symbol, roi EA DUNG: khong rai     |
//|     luoi, khong dong ro, khong bao / vao lenh. T2 6h chay lai.    |
//|     Moi cuoi tuan chi dong 1 lan (gan lai EA khong dong lai).     |
//|     Lenh tay vao trong luc nghi: EA khong dong, khong rai luoi.   |
//|                                                                  |
//|  CHUA CO: SL, TP (cho anh bo sung).                               |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026"
#property version   "1.20"
#property strict

#include <Trade\Trade.mqh>

//--- Phai TRUNG thu tu voi enum trong rsi_based.mq5 (iCustom truyen theo thu tu)
enum ENUM_RSI_MA_TYPE
{
   RSI_MA_NONE,     // None
   RSI_MA_SMA,      // SMA
   RSI_MA_SMA_BB,   // SMA + Bollinger Bands
   RSI_MA_EMA,      // EMA
   RSI_MA_SMMA,     // SMMA (RMA)
   RSI_MA_WMA,      // WMA
   RSI_MA_VWMA      // VWMA
};

input string           g1 = "--- Cap giao dich ---"; //
input string           InpSymbol = "XAUUSD";   // Ten symbol VANG tren broker

input string           g2 = "--- Luoi lenh limit ---"; //
input double           InpStep           = 5.0;   // Buoc gia VANG (5 = 5 gia vang)
input string           InpLotMultipliers = "1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7"; // He so lot cac lenh limit (nhan voi lot lenh tay), cach nhau dau phay. So phan tu = so lenh limit

input string           g4 = "--- Dong ro theo rsi_based ---"; //
input bool             InpUseClose      = true;          // Bat dong ro theo duong MA (mau do) cua rsi_based
input ENUM_TIMEFRAMES  InpCloseTf       = PERIOD_H1;     // Khung doc indicator
input double           InpCloseLevel    = 50.0;          // BUY dong khi MA >= muc nay, SELL dong khi MA <= muc nay
input string           InpIndicatorName = "rsi_based";   // Ten file .ex5 trong MQL5\Indicators
input int              InpRSILength     = 14;            // RSI Length (khop voi indicator tren chart)
input ENUM_APPLIED_PRICE InpRSISource   = PRICE_CLOSE;   // Source
input ENUM_RSI_MA_TYPE InpMAType        = RSI_MA_SMA;    // MA Type
input int              InpMALength      = 14;            // MA Length
input double           InpBBMult        = 2.0;           // BB StdDev

input string           g5 = "--- Canh bao + tu vao lenh ---"; //
input bool             InpUseSignalAlert = true;         // Bao tin hieu dinh/day cua duong MA do (nen H1 vua dong)
input double           InpSignalHigh     = 60.0;         // DINH phai > muc nay moi bao SELL
input double           InpSignalLow      = 40.0;         // DAY phai < muc nay moi bao BUY
input double           InpAutoLot        = 0.01;         // Lot EA TU VAO khi co tin hieu (0 = chi bao, khong vao lenh)
input bool             InpPopup          = true;         // Hien popup Alert + am thanh tren MT5
input bool             InpPush           = true;         // Gui push ve dien thoai (dong ro + tin hieu)

input string           g6 = "--- Chong du lieu loi ---"; //
input double           InpMaxJump        = 15.0;         // RSI base nhay qua so diem nay giua 2 lan doc -> coi la du lieu loi, bo qua

//--- CUOI TUAN (tinh theo gio dia phuong = GMT + InpGmtOffsetHours, khong phu thuoc mui gio may)
input string           g7 = "--- Nghi cuoi tuan ---"; //
input bool             InpUseWeekendFilter = true; // T6 tu gio dung: dong het lenh + xoa limit, EA nghi den T2 gio mo
input int              InpGmtOffsetHours   = 7;    // Mui gio dia phuong (VN = 7)
input int              InpFridayStopHour   = 17;   // Thu 6 tu gio nay nghi
input int              InpMondayStartHour  = 6;    // Thu 2 tu gio nay chay lai

input string           g3 = "--- Khac ---"; //
input ulong            InpMagic          = 20261007; // Magic number cua cac lenh limit do EA dat
input ulong            InpSlippage       = 30;       // Do truot cho phep (points)
input bool             InpShowPanel      = true;     // Hien bang thong tin goc chart
input bool             InpEnableDebugLog = true;     // Bat log chi tiet

//--- GLOBALS
CTrade   g_trade;
double   g_step      = 0.0;     // buoc gia cua symbol tren chart
double   g_mult[];              // he so lot tung lenh limit
int      g_lotDigits = 2;
datetime g_failTime  = 0;       // chong spam dat lenh khi broker tu choi
string   g_lastInfo  = "";      // dong thong tin gan nhat cho panel
int      g_indHandle     = INVALID_HANDLE;   // rsi_based khung H1
double   g_maLive        = EMPTY_VALUE;      // MA (duong do) nen H1 dang chay
datetime g_closeFailTime = 0;                // chong dong lai lien tuc khi broker tu choi
string   g_lastClose     = "";               // lan dong ro gan nhat cho panel
datetime g_sigLastBar    = 0;                // nen H1 da xet tin hieu
double   g_maPrev        = EMPTY_VALUE;      // RSI base doc hop le lan truoc (de loc nhay bat thuong)
datetime g_maPrevTime    = 0;
bool     g_dataBad       = false;            // dang trong trang thai du lieu loi (de log 1 lan)
string   g_lastSignal    = "";               // tin hieu gan nhat cho panel
bool     g_weekendPause  = false;            // dang trong khung nghi cuoi tuan
datetime g_wkFailTime    = 0;                // chong dong lai lien tuc khi broker tu choi (vd da dong cua)
string   g_lastWeekend   = "";               // ket qua dong cuoi tuan gan nhat cho panel

//+------------------------------------------------------------------+
void DebugLog(const string msg)
{
   if(InpEnableDebugLog) Print("[GRID] ", msg);
}

string GvName(const ulong posId)
{
   return "GRID_" + IntegerToString((long)posId);
}

//--- Tach danh sach he so lot. Tra ve so phan tu hop le (0 = loi)
int ParseMultipliers()
{
   ArrayResize(g_mult, 0);
   string parts[];
   int nParts = StringSplit(InpLotMultipliers, ',', parts);
   for(int i = 0; i < nParts; i++)
   {
      string s = parts[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "") continue;
      double m = StringToDouble(s);
      if(m <= 0.0) return 0;
      int n = ArraySize(g_mult);
      ArrayResize(g_mult, n + 1);
      g_mult[n] = m;
   }
   return ArraySize(g_mult);
}

//--- Chuan hoa lot theo min/max/step cua broker
double NormalizeLot(double lot)
{
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) step = 0.01;

   lot = MathRound(lot / step) * step;
   if(lot < minLot) lot = minLot;
   if(lot > maxLot) lot = maxLot;
   return NormalizeDouble(lot, g_lotDigits);
}

//--- Lenh dang chay nay co phai LENH TAY (terminal / mobile / web) khong?
bool IsManualPosition()
{
   if(PositionGetString(POSITION_SYMBOL) != _Symbol) return false;
   if(PositionGetInteger(POSITION_MAGIC) != 0) return false;
   ENUM_POSITION_REASON r = (ENUM_POSITION_REASON)PositionGetInteger(POSITION_REASON);
   return (r == POSITION_REASON_CLIENT || r == POSITION_REASON_MOBILE || r == POSITION_REASON_WEB);
}

//--- Danh dau lenh EA tu vao theo tin hieu (theo POSITION_IDENTIFIER)
string AutoGvName(const ulong posId)
{
   return "GRIDAUTO_" + IntegerToString((long)posId);
}

//--- Lenh dang chay nay co phai LENH GOC (lenh tay, hoac lenh EA tu vao theo tin hieu) khong?
//--- Lenh goc la lenh duoc rai luoi limit.
bool IsBasePosition()
{
   if(IsManualPosition()) return true;
   if(PositionGetString(POSITION_SYMBOL) != _Symbol) return false;
   if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) return false;
   return GlobalVariableCheck(AutoGvName((ulong)PositionGetInteger(POSITION_IDENTIFIER)));
}

//--- Symbol nay da co lenh dang chay / lenh cho cua EA chua? (bo qua lenh co id = excludeId)
bool HasEaExposure(int &pendings, int &positions, const ulong excludeId = 0)
{
   pendings = 0;
   positions = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderGetTicket(i) == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      pendings++;
   }
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(excludeId != 0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER) == excludeId) continue;
      positions++;
   }
   return (pendings + positions > 0);
}

//--- Da co lenh cho cua EA nam gan muc gia nay chua (tranh dat trung khi thu lai)
bool HasPendingNear(const double level)
{
   double tol = g_step * 0.5;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderGetTicket(i) == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;
      if(MathAbs(OrderGetDouble(ORDER_PRICE_OPEN) - level) < tol) return true;
   }
   return false;
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(StringCompare(_Symbol, InpSymbol, false) != 0)
   {
      Print("[GRID] EA nay chi chay tren ", InpSymbol, ", chart nay la ", _Symbol,
            ". Neu broker dat ten khac thi sua InpSymbol.");
      return(INIT_FAILED);
   }
   g_step = InpStep;
   if(g_step <= 0.0)
   {
      Print("[GRID] Buoc gia phai > 0.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(ParseMultipliers() == 0)
   {
      Print("[GRID] Danh sach he so lot '", InpLotMultipliers, "' khong hop le (vd 1,1,1,2,2,2,3,3,3).");
      return(INIT_PARAMETERS_INCORRECT);
   }

   if(InpUseClose || InpUseSignalAlert)
   {
      // Tham so truyen vao iCustom PHAI dung thu tu input cua rsi_based.mq5
      g_indHandle = iCustom(_Symbol, InpCloseTf, InpIndicatorName,
                            InpRSILength, InpRSISource, InpMAType, InpMALength, InpBBMult,
                            false);   // tat log cua indicator
      if(g_indHandle == INVALID_HANDLE)
      {
         Print("[GRID] Khong nap duoc indicator '", InpIndicatorName,
               "'. Kiem tra file .ex5 co nam trong MQL5\\Indicators khong. err=", GetLastError());
         return(INIT_FAILED);
      }
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpSlippage);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   g_lotDigits = (lotStep >= 0.1) ? 1 : ((lotStep >= 0.01) ? 2 : 3);

   //--- Lenh tay DANG CO luc gan EA -> danh dau da xu ly, khong dat luoi cho chung
   int existing = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) == 0 || !IsManualPosition()) continue;
      GlobalVariableSet(GvName((ulong)PositionGetInteger(POSITION_IDENTIFIER)), 1.0);
      existing++;
   }

   string mults = "";
   for(int i = 0; i < ArraySize(g_mult); i++) mults += (i > 0 ? "," : "") + DoubleToString(g_mult[i], 1);
   Print("[GRID-BUILD] rsi_base_h1_xau v1.20 | ", _Symbol, " | buoc ", DoubleToString(g_step, 2), " gia | ",
         ArraySize(g_mult), " lenh limit, he so lot ", mults, " (nhan voi lot lenh tay)",
         " | magic ", InpMagic, " | bo qua ", existing, " lenh tay dang co");
   if(InpUseWeekendFilter)
   {
      Print("[GRID] Nghi cuoi tuan: T6 ", InpFridayStopHour, "h dong het lenh + xoa limit -> T2 ",
            InpMondayStartHour, "h chay lai (GMT+", InpGmtOffsetHours, ")");
      if(MQLInfoInteger(MQL_TESTER))
         Print("[GRID] Luu y: trong Tester TimeGMT() = gio server, nen moc cuoi tuan co the lech gio.");
   }
   else
      Print("[GRID] Nghi cuoi tuan: TAT");
   datetime pauseStart;
   g_weekendPause = InWeekendPause(pauseStart);
   if(g_weekendPause) Print("[GRID] Gan EA trong luc NGHI CUOI TUAN -> EA dung den T2 ", InpMondayStartHour, "h");
   if(InpUseClose)
      Print("[GRID] Dong ro: doc '", InpIndicatorName, "' ", TfText(), " duong MA (do), nen dang chay, moi tick",
            " | BUY dong khi MA >= ", DoubleToString(InpCloseLevel, 1),
            ", SELL dong khi MA <= ", DoubleToString(InpCloseLevel, 1));
   else
      Print("[GRID] Dong ro: TAT");
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
      Print("[GRID] Algo Trading dang TAT -> EA KHONG dat lenh duoc. Bat nut Algo Trading + tick 'Allow Algo Trading' cua EA.");

   EventSetTimer(1);
   UpdatePanel();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_indHandle != INVALID_HANDLE) IndicatorRelease(g_indHandle);
   g_indHandle = INVALID_HANDLE;
   Comment("");
}

string TfText() { return StringSubstr(EnumToString(InpCloseTf), 7); }

//+------------------------------------------------------------------+
//| Dong ro truoc, dat luoi sau: lenh tay vao luc MA da thoa dieu kien |
//| dong thi bi dong luon, khong dat luoi vo ich.                      |
//+------------------------------------------------------------------+
void OnTick()
{
   if(CheckWeekend()) return;   // dang nghi cuoi tuan -> EA dung
   CheckClose(); ScanManual(); CheckSignal();
}
void OnTimer() { OnTick(); UpdatePanel(); }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD && !g_weekendPause) ScanManual();
}

//+------------------------------------------------------------------+
//| Tim lenh goc moi (tay / tu vao) chua dat luoi -> dat luoi limit    |
//+------------------------------------------------------------------+
void ScanManual()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsBasePosition()) continue;

      ulong  id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      string gv = GvName(id);
      if(GlobalVariableCheck(gv)) continue;                  // da xu ly roi
      if(TimeLocal() - g_failTime < 10) return;              // vua bi broker tu choi -> doi 10 giay

      int pendings, positions;
      if(HasEaExposure(pendings, positions, id))   // khong tinh chinh lenh goc (lenh tu vao co magic EA)
      {
         DebugLog("Lenh goc #" + IntegerToString((long)ticket) + " bo qua: symbol da co " +
                  IntegerToString(pendings) + " lenh cho + " + IntegerToString(positions) + " lenh dang chay cua EA");
         GlobalVariableSet(gv, 1.0);
         continue;
      }

      if(PlaceGrid(ticket)) GlobalVariableSet(gv, 1.0);
      else                  g_failTime = TimeLocal();
      return;   // PlaceGrid doi trang thai lenh -> quet lai o lan sau
   }
}

//--- Dat cac lenh limit quanh lenh tay. Tra ve true neu xong (khong con loi can thu lai)
bool PlaceGrid(const ulong posTicket)
{
   if(!PositionSelectByTicket(posTicket)) return false;

   bool   isBuy   = ((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
   double entry   = PositionGetDouble(POSITION_PRICE_OPEN);
   double baseLot = PositionGetDouble(POSITION_VOLUME);
   string src     = ((ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic) ? "Lenh tu vao " : "Lenh tay ";

   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   double bid     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   Print("[GRID] ", src, (isBuy ? "BUY " : "SELL "), DoubleToString(baseLot, g_lotDigits), " lot @ ",
         DoubleToString(entry, _Digits), " -> dat ", ArraySize(g_mult), " lenh ",
         (isBuy ? "Buy Limit " : "Sell Limit "), "cach ", DoubleToString(g_step, 2), " gia");

   int placed = 0, skipped = 0, failed = 0;
   for(int k = 1; k <= ArraySize(g_mult); k++)
   {
      double level = NormalizeDouble(isBuy ? entry - g_step * k : entry + g_step * k, _Digits);
      if(HasPendingNear(level)) { placed++; continue; }

      // Gia da di qua moc nay (hoac qua sat gia hien tai) -> khong dat duoc limit hop le
      bool valid = isBuy ? (level <= ask - minDist) : (level >= bid + minDist);
      if(!valid)
      {
         skipped++;
         DebugLog("Bo qua moc #" + IntegerToString(k) + " @ " + DoubleToString(level, _Digits) +
                  ": gia da di qua / qua sat gia hien tai");
         continue;
      }

      double lot     = NormalizeLot(baseLot * g_mult[k - 1]);
      string comment = "GRID#" + IntegerToString(k);
      bool ok = isBuy ? g_trade.BuyLimit(lot, level, _Symbol, 0.0, 0.0, ORDER_TIME_GTC, 0, comment)
                      : g_trade.SellLimit(lot, level, _Symbol, 0.0, 0.0, ORDER_TIME_GTC, 0, comment);
      if(ok)
      {
         placed++;
         Print("[GRID] DAT ", (isBuy ? "BUY LIMIT " : "SELL LIMIT "), DoubleToString(lot, g_lotDigits),
               " lot @ ", DoubleToString(level, _Digits), " | ", comment);
      }
      else
      {
         failed++;
         Print("[GRID] Dat ", comment, " @ ", DoubleToString(level, _Digits), " THAT BAI: retcode=",
               g_trade.ResultRetcode(), " (", g_trade.ResultRetcodeDescription(), ")");
         break;   // doi 10 giay roi thu lai cac moc con thieu
      }
   }

   g_lastInfo = src + (isBuy ? "BUY " : "SELL ") + DoubleToString(baseLot, g_lotDigits) + " @ " +
                DoubleToString(entry, _Digits) + ": dat " + IntegerToString(placed) + " lenh limit" +
                (skipped > 0 ? ", bo qua " + IntegerToString(skipped) : "") +
                (failed > 0 ? ", LOI " + IntegerToString(failed) : "");
   Print("[GRID] ", g_lastInfo);
   return (failed == 0);
}

//+------------------------------------------------------------------+
//|                            DONG RO                                |
//+------------------------------------------------------------------+
//--- Lenh dang chay thuoc ro: lenh tay hoac lenh cua EA nay, tren symbol chart
bool InBasket()
{
   if(PositionGetString(POSITION_SYMBOL) != _Symbol) return false;
   if((ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic) return true;
   return IsManualPosition();
}

//--- Ghi log 1 lan khi trang thai du lieu doi (loi <-> on)
void SetDataBad(const bool bad, const string why)
{
   if(bad == g_dataBad) return;
   g_dataBad = bad;
   if(bad) Print("[GRID] DU LIEU ", TfText(), " CHUA ON (", why, ") -> tam dung dong ro + bao tin hieu");
   else    Print("[GRID] Du lieu ", TfText(), " on dinh lai -> chay binh thuong");
}

//--- Lich su H1 + indicator da dong bo, nen H1 hien tai dung la nen cua gio hien tai?
bool DataReady()
{
   datetime t0 = iTime(_Symbol, InpCloseTf, 0);
   if(t0 == 0 || TimeCurrent() - t0 >= PeriodSeconds(InpCloseTf))
   {
      SetDataBad(true, "nen " + TfText() + " moi nhat " + TimeToString(t0) + " khong phai gio hien tai");
      return false;
   }
   if(!(bool)SeriesInfoInteger(_Symbol, InpCloseTf, SERIES_SYNCHRONIZED))
   {
      SetDataBad(true, "lich su chua dong bo xong");
      return false;
   }
   int bars = Bars(_Symbol, InpCloseTf);
   int calc = BarsCalculated(g_indHandle);
   if(calc < bars)
   {
      SetDataBad(true, "indicator moi tinh " + IntegerToString(calc) + "/" + IntegerToString(bars) + " nen");
      return false;
   }
   return true;
}

void CheckClose()
{
   if(!InpUseClose || g_indHandle == INVALID_HANDLE) return;
   if(!DataReady()) return;

   double buf[];
   if(CopyBuffer(g_indHandle, 1, 0, 1, buf) != 1 || buf[0] == EMPTY_VALUE || !MathIsValidNumber(buf[0]))
      return;   // indicator chua tinh xong
   double ma = buf[0];

   // RSI base (SMA 14 tren RSI) chi dich toi da ~7 diem moi nen; nhay manh trong thoi gian ngan = du lieu loi
   if(g_maPrev != EMPTY_VALUE && TimeCurrent() - g_maPrevTime <= 2 * PeriodSeconds(InpCloseTf) &&
      MathAbs(ma - g_maPrev) > InpMaxJump)
   {
      SetDataBad(true, "RSI base nhay " + DoubleToString(g_maPrev, 2) + " -> " + DoubleToString(ma, 2));
      return;
   }
   SetDataBad(false, "");
   g_maPrev     = ma;
   g_maPrevTime = TimeCurrent();
   g_maLive     = ma;

   bool closeBuy  = (ma >= InpCloseLevel);
   bool closeSell = (ma <= InpCloseLevel);
   if(TimeLocal() - g_closeFailTime < 5) return;   // vua bi broker tu choi -> doi 5 giay

   int    closedBuy, closedSell, deleted;
   double pnl;
   int    failed = CloseBasket(closeBuy, closeSell, closedBuy, closedSell, deleted, pnl);

   if(failed > 0) g_closeFailTime = TimeLocal();
   if(closedBuy + closedSell + deleted + failed == 0) return;

   g_lastClose = "DONG RO " + _Symbol + ": " + CloseText(closedBuy, closedSell, deleted) +
                 " | MA " + TfText() + " = " + DoubleToString(ma, 2) +
                 (closedSell > 0 && closedBuy == 0 ? " <= " : " >= ") + DoubleToString(InpCloseLevel, 0) +
                 " | PnL ~" + DoubleToString(pnl, 2) +
                 (failed > 0 ? " | THAT BAI " + IntegerToString(failed) + ", thu lai sau 5 giay" : "");
   Notify(g_lastClose, _Symbol + ": Da dong het lenh");
}

//--- Dong lenh trong ro (lenh tay + lenh EA) va xoa lenh cho cua EA tren symbol, theo chieu.
//--- Tra ve so lenh dong / xoa THAT BAI.
int CloseBasket(const bool closeBuy, const bool closeSell,
                int &closedBuy, int &closedSell, int &deleted, double &pnl)
{
   closedBuy = 0; closedSell = 0; deleted = 0; pnl = 0.0;
   int failed = 0;

   // Xoa lenh cho TRUOC, tranh lenh cho khop them trong luc dang dong
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic) continue;

      ENUM_ORDER_TYPE t = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      bool isBuyOrder = (t == ORDER_TYPE_BUY_LIMIT || t == ORDER_TYPE_BUY_STOP || t == ORDER_TYPE_BUY_STOP_LIMIT);
      if(!(isBuyOrder ? closeBuy : closeSell)) continue;

      if(g_trade.OrderDelete(ticket)) deleted++;
      else
      {
         failed++;
         Print("[GRID] Xoa lenh cho #", ticket, " THAT BAI: retcode=", g_trade.ResultRetcode(),
               " (", g_trade.ResultRetcodeDescription(), ")");
      }
   }

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !InBasket()) continue;

      bool isBuy = ((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      if(!(isBuy ? closeBuy : closeSell)) continue;

      double p = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      if(g_trade.PositionClose(ticket))
      {
         if(isBuy) closedBuy++;
         else      closedSell++;
         pnl += p;
      }
      else
      {
         failed++;
         Print("[GRID] Dong lenh #", ticket, " THAT BAI: retcode=", g_trade.ResultRetcode(),
               " (", g_trade.ResultRetcodeDescription(), ")");
      }
   }

   return failed;
}

string CloseText(const int closedBuy, const int closedSell, const int deleted)
{
   string what = "";
   if(closedBuy  > 0) what += IntegerToString(closedBuy) + " BUY";
   if(closedSell > 0) what += (what != "" ? ", " : "") + IntegerToString(closedSell) + " SELL";
   if(deleted    > 0) what += (what != "" ? ", " : "") + "xoa " + IntegerToString(deleted) + " lenh cho";
   return (what != "" ? what : "chua dong duoc");
}

//+------------------------------------------------------------------+
//|                         NGHI CUOI TUAN                            |
//+------------------------------------------------------------------+
//--- Dang trong khung nghi (gio dia phuong)? pauseStart = moc T6 gio dung cua dot nghi nay
bool InWeekendPause(datetime &pauseStart)
{
   pauseStart = 0;
   if(!InpUseWeekendFilter) return false;

   datetime local = TimeGMT() + InpGmtOffsetHours * 3600;
   MqlDateTime dt;
   TimeToStruct(local, dt);
   bool pause = (dt.day_of_week == 5 && dt.hour >= InpFridayStopHour) ||
                dt.day_of_week == 6 || dt.day_of_week == 0 ||
                (dt.day_of_week == 1 && dt.hour < InpMondayStartHour);
   if(!pause) return false;

   int daysFromFri = (dt.day_of_week + 2) % 7;   // T6=0, T7=1, CN=2, T2=3
   pauseStart = local - (local % 86400) - daysFromFri * 86400 + InpFridayStopHour * 3600;
   return true;
}

//--- Tra ve true khi dang nghi cuoi tuan (cac phan khac cua EA dung lai).
//--- Dau dot nghi: dong het lenh dang chay + xoa het lenh cho, chi 1 lan moi cuoi tuan.
bool CheckWeekend()
{
   datetime pauseStart;
   bool pause = InWeekendPause(pauseStart);
   if(pause != g_weekendPause)
   {
      g_weekendPause = pause;
      if(pause) Print("[GRID] BAT DAU NGHI CUOI TUAN -> dong het lenh, EA dung den T2 ", InpMondayStartHour, "h");
      else      Notify("HET NGHI CUOI TUAN " + _Symbol + " -> EA chay lai binh thuong", _Symbol + ": EA chay lai");
   }
   if(!pause) return false;

   // Da dong xong dot nghi nay (luu bang GV de gan lai EA / khoi dong lai may khong dong lai)
   string gv = "GRIDWKND_" + _Symbol;
   if(GlobalVariableCheck(gv) && (datetime)GlobalVariableGet(gv) == pauseStart)
   {
      // Lenh tay vao trong luc nghi: danh dau da xu ly -> T2 khong rai luoi cho lenh nay
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(PositionGetTicket(i) == 0 || !IsManualPosition()) continue;
         string g = GvName((ulong)PositionGetInteger(POSITION_IDENTIFIER));
         if(!GlobalVariableCheck(g)) GlobalVariableSet(g, 1.0);
      }
      return true;
   }
   if(TimeLocal() - g_wkFailTime < 30) return true;   // vua that bai (vd thi truong da dong) -> doi 30 giay

   int    closedBuy, closedSell, deleted;
   double pnl;
   int    failed = CloseBasket(true, true, closedBuy, closedSell, deleted, pnl);
   if(failed > 0)
   {
      g_wkFailTime = TimeLocal();
      string txt   = "CUOI TUAN " + _Symbol + ": " + CloseText(closedBuy, closedSell, deleted) +
                     " | THAT BAI " + IntegerToString(failed) + ", thu lai sau 30 giay";
      if(txt != g_lastWeekend) Print("[GRID] ", txt);   // thi truong dong ca cuoi tuan -> khong log lap lai
      g_lastWeekend = txt;
      return true;
   }

   GlobalVariableSet(gv, (double)pauseStart);
   g_lastWeekend = "CUOI TUAN " + _Symbol + ": " +
                   (closedBuy + closedSell + deleted > 0 ? CloseText(closedBuy, closedSell, deleted) +
                                                          " | PnL ~" + DoubleToString(pnl, 2)
                                                        : "khong co lenh");
   Notify(g_lastWeekend + " -> EA nghi den T2 " + IntegerToString(InpMondayStartHour) + "h",
          _Symbol + ": Nghi cuoi tuan, " + (closedBuy + closedSell + deleted > 0 ? "da dong het lenh" : "khong co lenh"));
   return true;
}

//+------------------------------------------------------------------+
//|                            CANH BAO                               |
//+------------------------------------------------------------------+
//--- detail: ghi log + popup | pushText: noi dung ngan gui ve dien thoai
void Notify(const string detail, const string pushText)
{
   Print("[GRID] BAO: ", detail);
   if(MQLInfoInteger(MQL_TESTER)) return;
   if(InpPopup) Alert(detail);
   if(InpPush && TerminalInfoInteger(TERMINAL_NOTIFICATIONS_ENABLED) && !SendNotification(pushText))
      Print("[GRID] Gui push THAT BAI, err=", GetLastError());
}

//--- Tin hieu dinh / day cua duong MA do, xet 1 lan moi khi nen H1 dong
void CheckSignal()
{
   if(!InpUseSignalAlert || g_indHandle == INVALID_HANDLE) return;

   datetime bar = iTime(_Symbol, InpCloseTf, 1);   // nen 0 cua anh = nen vua dong
   if(bar == 0 || bar == g_sigLastBar) return;
   if(!DataReady()) return;

   double v[];
   ArraySetAsSeries(v, true);   // v[0] = nen vua dong, v[1] = truoc 1 cay, v[2] = truoc 2 cay
   if(CopyBuffer(g_indHandle, 1, 1, 3, v) != 3) return;
   for(int k = 0; k < 3; k++)
      if(v[k] == EMPTY_VALUE || !MathIsValidNumber(v[k])) return;
   if(MathAbs(v[0] - v[1]) > InpMaxJump || MathAbs(v[1] - v[2]) > InpMaxJump)
   {
      SetDataBad(true, "RSI base 3 nen nhay bat thuong " + DoubleToString(v[2], 2) + " / " +
                 DoubleToString(v[1], 2) + " / " + DoubleToString(v[0], 2));
      return;   // khong danh dau nen -> tick sau doc lai
   }
   g_sigLastBar = bar;

   bool peak   = (v[1] > v[0] && v[1] > v[2] && v[1] > InpSignalHigh);
   bool trough = (v[1] < v[0] && v[1] < v[2] && v[1] < InpSignalLow);

   string vals = "nen 0=" + DoubleToString(v[0], 2) + ", 1=" + DoubleToString(v[1], 2) +
                 ", 2=" + DoubleToString(v[2], 2);
   if(!peak && !trough)
   {
      DebugLog("Nen " + TfText() + " " + TimeToString(bar, TIME_DATE | TIME_MINUTES) + " dong | MA do: " + vals +
               " -> khong co tin hieu");
      return;
   }

   // Dang co lenh (lenh tay / lenh EA dang chay / lenh cho cua EA) -> khong bao, khong vao lenh
   int pendings, eaPositions, basket = 0;
   HasEaExposure(pendings, eaPositions);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) != 0 && InBasket()) basket++;
   if(basket + pendings > 0)
   {
      DebugLog("Co tin hieu " + string(peak ? "SELL" : "BUY") + " (" + vals + ") nhung dang co " +
               IntegerToString(basket) + " lenh chay + " + IntegerToString(pendings) + " lenh cho -> khong bao, khong vao");
      return;
   }

   // Gan lai EA / doi khung chart giua chung -> khong bao lai tin hieu cua cung nen H1
   string gv = "GRIDSIG_" + _Symbol + "_" + TfText();
   if(GlobalVariableCheck(gv) && (datetime)GlobalVariableGet(gv) == bar) return;
   GlobalVariableSet(gv, (double)bar);

   g_lastSignal = _Symbol + " " + TfText() + ": MA do tao " +
                  (peak ? "DINH " + DoubleToString(v[1], 2) + " > " + DoubleToString(InpSignalHigh, 0) + " -> tin hieu SELL"
                        : "DAY " + DoubleToString(v[1], 2) + " < " + DoubleToString(InpSignalLow, 0) + " -> tin hieu BUY") +
                  " | " + vals + " | gia " + DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), _Digits);

   string pushEntry = "";
   if(InpAutoLot > 0.0) g_lastSignal += AutoEnter(peak, pushEntry);
   Notify(g_lastSignal, _Symbol + ": Co tin hieu " + (peak ? "SELL" : "BUY") + pushEntry);
}

//--- Tu vao lenh market theo tin hieu. Lenh nay duoc rai luoi o ScanManual nhu lenh tay.
//--- Tra ve mo ta ket qua (ghi them vao canh bao), shortTxt = doan ngan cho push.
string AutoEnter(const bool isSell, string &shortTxt)
{
   string side = isSell ? "SELL" : "BUY";

   // MA dang chay da cham muc dong ro -> vao xong se bi dong ngay
   if(InpUseClose && g_maLive != EMPTY_VALUE &&
      (isSell ? g_maLive <= InpCloseLevel : g_maLive >= InpCloseLevel))
   {
      shortTxt = ", KHONG vao lenh";
      return " | KHONG VAO: MA dang chay " + DoubleToString(g_maLive, 2) + (isSell ? " <= " : " >= ") +
             DoubleToString(InpCloseLevel, 0) + ", vao se bi dong ngay";
   }

   double lot = NormalizeLot(InpAutoLot);
   string cmt = "SIG " + side;
   bool   ok  = isSell ? g_trade.Sell(lot, _Symbol, 0.0, 0.0, 0.0, cmt)
                       : g_trade.Buy(lot, _Symbol, 0.0, 0.0, 0.0, cmt);
   uint   rc  = g_trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED))
   {
      shortTxt = ", VAO LENH THAT BAI";
      return " | VAO " + side + " THAT BAI: retcode=" + IntegerToString((long)rc) +
             " (" + g_trade.ResultRetcodeDescription() + ")";
   }

   // Id cua lenh dang chay = ticket lenh mo no; lay tu deal neu co cho chac
   ulong posId = g_trade.ResultOrder();
   ulong deal  = g_trade.ResultDeal();
   if(deal > 0 && HistoryDealSelect(deal)) posId = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   GlobalVariableSet(AutoGvName(posId), 1.0);   // danh dau la lenh goc -> ScanManual rai luoi

   string lotTxt = DoubleToString(lot, g_lotDigits);
   Print("[GRID] TU VAO ", side, " ", lotTxt, " lot @ ", DoubleToString(g_trade.ResultPrice(), _Digits),
         " | position id ", posId);
   shortTxt = ", da vao " + side + " " + lotTxt;
   return " | DA VAO " + side + " " + lotTxt + " lot @ " + DoubleToString(g_trade.ResultPrice(), _Digits);
}

//+------------------------------------------------------------------+
void UpdatePanel()
{
   if(!InpShowPanel) return;

   int pendings, positions;
   HasEaExposure(pendings, positions);

   string lots = "";
   for(int i = 0; i < ArraySize(g_mult); i++) lots += (i > 0 ? "/" : "") + DoubleToString(g_mult[i], 0) + "x";

   Comment("\n\n=== rsi_base_h1_xau (luoi limit) ===\n",
           _Symbol, " | buoc ", DoubleToString(g_step, 2), " gia | ", ArraySize(g_mult), " lenh limit\n",
           "He so lot: ", lots, " (nhan voi lot lenh tay)\n",
           "Dang co: ", pendings, " lenh cho, ", positions, " lenh dang chay cua EA\n",
           (g_lastInfo != "" ? g_lastInfo : "Cho anh vao lenh tay..."), "\n",
           (InpUseClose ? "MA (duong do) " + TfText() + " (nen dang chay) = " +
                          (g_maLive == EMPTY_VALUE ? "chua san sang" : DoubleToString(g_maLive, 2)) +
                          " | BUY dong khi >= " + DoubleToString(InpCloseLevel, 0) +
                          ", SELL dong khi <= " + DoubleToString(InpCloseLevel, 0)
                        : "Dong ro: TAT"),
           (g_lastClose != "" ? "\n" + g_lastClose : ""),
           (!InpUseWeekendFilter ? "\nNghi cuoi tuan: TAT"
                                 : "\nNghi cuoi tuan: T6 " + IntegerToString(InpFridayStopHour) + "h -> T2 " +
                                   IntegerToString(InpMondayStartHour) + "h (GMT+" + IntegerToString(InpGmtOffsetHours) + ")" +
                                   (g_weekendPause ? " | DANG NGHI, EA dung" : "") +
                                   (g_lastWeekend != "" ? "\n" + g_lastWeekend : "")),
           (InpUseSignalAlert ? "\nTin hieu (nen " + TfText() + " dong): dinh > " + DoubleToString(InpSignalHigh, 0) +
                                " bao SELL, day < " + DoubleToString(InpSignalLow, 0) + " bao BUY" +
                                (InpAutoLot > 0.0 ? "\nTu vao lenh: lot " + DoubleToString(NormalizeLot(InpAutoLot), g_lotDigits)
                                                  : "\nTu vao lenh: TAT (lot = 0, chi bao)") +
                                (g_lastSignal != "" ? "\n" + g_lastSignal : "") : ""));
}
//+------------------------------------------------------------------+
