//+------------------------------------------------------------------+
//|                                          RSI + RSI-based MA      |
//|  Custom indicator (subwindow rieng), port tu TradingView RSI     |
//|  built-in (Pine v6), chi giu phan "RSI-based MA" (bo Divergence).|
//|                                                                  |
//|  Buffer 0: RSI (iRSI chuan MT5, tuong duong ta.rma cua Pine)      |
//|  Buffer 1: MA tinh tren chinh chuoi RSI (khong phai tren gia)     |
//|  Buffer 2/3: Bollinger Bands quanh MA do (chi khi chon SMA+BB)    |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026"
#property version   "1.00"
#property indicator_separate_window
#property indicator_buffers 4
#property indicator_plots   4
#property indicator_minimum 0
#property indicator_maximum 100

#property indicator_label1  "RSI"
#property indicator_type1   DRAW_NONE   // an duong RSI tim, van tinh de iCustom / Data Window doc duoc
#property indicator_color1  C'126,87,194'
#property indicator_width1  2

#property indicator_label2  "RSI-based MA"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrRed
#property indicator_width2  2

#property indicator_label3  "BB Upper"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrLimeGreen
#property indicator_width3  1

#property indicator_label4  "BB Lower"
#property indicator_type4   DRAW_LINE
#property indicator_color4  clrLimeGreen
#property indicator_width4  1

//--- Cac loai MA tinh tren chuoi RSI (giong dropdown "Type" trong Pine)
enum ENUM_RSI_MA_TYPE
{
   RSI_MA_NONE,     // None - khong ve MA
   RSI_MA_SMA,      // SMA
   RSI_MA_SMA_BB,   // SMA + Bollinger Bands
   RSI_MA_EMA,      // EMA
   RSI_MA_SMMA,     // SMMA (RMA)
   RSI_MA_WMA,      // WMA
   RSI_MA_VWMA      // VWMA
};

//--- RSI
input int                 InpRSILength = 14;          // RSI Length
input ENUM_APPLIED_PRICE   InpRSISource = PRICE_CLOSE;  // Source

//--- Smoothing (RSI-based MA)
input ENUM_RSI_MA_TYPE     InpMAType   = RSI_MA_SMA;   // Type
input int                  InpMALength = 14;           // Length
input double               InpBBMult   = 2.0;          // BB StdDev (chi dung khi Type = SMA + Bollinger Bands)

//--- Log
input bool                 InpEnableDebugLog = true;   // Bat log chi tiet (moi nen dong, xem tab Experts)

//--- Buffers
double ExtRSIBuffer[];
double ExtMABuffer[];
double ExtBBUpperBuffer[];
double ExtBBLowerBuffer[];

int      ExtRSIHandle  = INVALID_HANDLE;
datetime ExtLastLogBar = 0;   // nen gan nhat da log, tranh log moi tick

//--- LOG HELPER
void DebugLog(const string message)
{
   if(InpEnableDebugLog)
      Print("[RSI-MA-DEBUG] ", message);
}

string MATypeText()
{
   switch(InpMAType)
   {
      case RSI_MA_NONE:   return "None";
      case RSI_MA_SMA:    return "SMA";
      case RSI_MA_SMA_BB: return "SMA + Bollinger Bands";
      case RSI_MA_EMA:    return "EMA";
      case RSI_MA_SMMA:   return "SMMA (RMA)";
      case RSI_MA_WMA:    return "WMA";
      case RSI_MA_VWMA:   return "VWMA";
   }
   return "khong ro";
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpRSILength < 1 || InpMALength < 1)
   {
      Print("[RSI-MA] RSI Length va MA Length phai >= 1.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   SetIndexBuffer(0, ExtRSIBuffer,     INDICATOR_DATA);
   SetIndexBuffer(1, ExtMABuffer,      INDICATOR_DATA);
   SetIndexBuffer(2, ExtBBUpperBuffer, INDICATOR_DATA);
   SetIndexBuffer(3, ExtBBLowerBuffer, INDICATOR_DATA);

   // An di cac duong khong dung toi, tuy theo Type da chon
   if(InpMAType == RSI_MA_NONE)
      PlotIndexSetInteger(1, PLOT_DRAW_TYPE, DRAW_NONE);
   if(InpMAType != RSI_MA_SMA_BB)
   {
      PlotIndexSetInteger(2, PLOT_DRAW_TYPE, DRAW_NONE);
      PlotIndexSetInteger(3, PLOT_DRAW_TYPE, DRAW_NONE);
   }

   // Vach 40/50/60
   IndicatorSetInteger(INDICATOR_LEVELS, 3);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 0, 40);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 1, 50);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 2, 60);
   for(int lvl = 0; lvl < 3; lvl++)
   {
      IndicatorSetInteger(INDICATOR_LEVELCOLOR, lvl, clrGray);
      IndicatorSetInteger(INDICATOR_LEVELSTYLE, lvl, STYLE_DOT);
   }

   IndicatorSetInteger(INDICATOR_DIGITS, 2);
   IndicatorSetString(INDICATOR_SHORTNAME, "RSI(" + IntegerToString(InpRSILength) +
                       ") MA(" + IntegerToString(InpMALength) + ")");

   ExtRSIHandle = iRSI(_Symbol, _Period, InpRSILength, InpRSISource);
   if(ExtRSIHandle == INVALID_HANDLE)
   {
      Print("[RSI-MA] Khong tao duoc handle iRSI, err=", GetLastError());
      return(INIT_FAILED);
   }

   ExtLastLogBar = 0;
   Print("[RSI-MA-BUILD] rsi_based v1.00 | ", _Symbol, " ", EnumToString((ENUM_TIMEFRAMES)_Period),
         " | RSI(", InpRSILength, ", ", EnumToString(InpRSISource), ")",
         " | MA tren RSI: ", MATypeText(), "(", InpMALength, ")",
         (InpMAType == RSI_MA_SMA_BB ? " | BB StdDev=" + DoubleToString(InpBBMult, 2) : ""),
         " | log=", (InpEnableDebugLog ? "BAT" : "TAT"));

   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(ExtRSIHandle != INVALID_HANDLE)
      IndicatorRelease(ExtRSIHandle);
}

//+------------------------------------------------------------------+
//| Cac ham tinh MA tren 1 chuoi gia tri bat ky (o day la RSI)        |
//| src, vol: mang tang dan (index 0 = nen cu nhat), giong buffer     |
//+------------------------------------------------------------------+
double SmaOnBuffer(const double &src[], const int i, const int length)
{
   double sum = 0.0;
   for(int k = i - length + 1; k <= i; k++) sum += src[k];
   return sum / length;
}

double WmaOnBuffer(const double &src[], const int i, const int length)
{
   double sum = 0.0, weightSum = 0.0;
   for(int k = 0; k < length; k++)
   {
      double w = (double)(k + 1);
      sum       += src[i - length + 1 + k] * w;
      weightSum += w;
   }
   return sum / weightSum;
}

double VwmaOnBuffer(const double &src[], const long &vol[], const int i, const int length)
{
   double sum = 0.0, volSum = 0.0;
   for(int k = i - length + 1; k <= i; k++)
   {
      sum    += src[k] * (double)vol[k];
      volSum += (double)vol[k];
   }
   if(volSum <= 0.0) return SmaOnBuffer(src, i, length);
   return sum / volSum;
}

double StdevOnBuffer(const double &src[], const int i, const int length, const double mean)
{
   double sum2 = 0.0;
   for(int k = i - length + 1; k <= i; k++)
   {
      double d = src[k] - mean;
      sum2 += d * d;
   }
   return MathSqrt(sum2 / length);
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   int rsiWarmup = InpRSILength + 1; // so nen toi thieu de co gia tri RSI dau tien
   if(rates_total < rsiWarmup) return(0);

   // iRSI chua tinh het so nen hien tai (vd terminal dang dong bo lai lich su luc qua ngay):
   // copy luc nay se lay so lieu cu gan vao nen moi -> lech nhieu nen. Cho tick sau tinh lai tu dau.
   int rsiCalculated = BarsCalculated(ExtRSIHandle);
   if(rsiCalculated < rates_total)
   {
      if(prev_calculated > 0)
         DebugLog("iRSI chua tinh xong (" + IntegerToString(rsiCalculated) + "/" + IntegerToString(rates_total) +
                  " nen) -> cho tinh lai");
      return(0);
   }

   //--- Nap gia tri RSI vao ExtRSIBuffer, giu dung thu tu tang dan (index 0 = nen cu nhat)
   int copyFrom = (prev_calculated > 0) ? prev_calculated - 1 : 0;
   int toCopy    = rates_total - copyFrom;

   double rsiTmp[];
   ArraySetAsSeries(rsiTmp, false); // ep CopyBuffer tra ve thu tu tang dan (index 0 = nen cu nhat trong khoang copy)
   int copied = CopyBuffer(ExtRSIHandle, 0, 0, toCopy, rsiTmp);
   if(copied <= 0) return(0);
   for(int k = 0; k < copied; k++)
      ExtRSIBuffer[copyFrom + k] = rsiTmp[k];

   int calcTotal = copyFrom + copied; // co the < rates_total neu handle RSI chua tinh xong het

   if(prev_calculated == 0)
      DebugLog("Tinh lai toan bo: nap duoc " + IntegerToString(copied) + "/" +
               IntegerToString(rates_total) + " nen RSI" +
               (calcTotal < rates_total ? " (handle iRSI chua tinh xong, se bu o tick sau)" : ""));

   //--- RSI chua san sang (chua du nen warmup) -> de trong
   int rsiBegin = rsiWarmup - 1;

   //--- Tinh MA tren chuoi RSI, tu bar moi (khong dong lai bar da tinh o lan truoc)
   int start = (prev_calculated > 0) ? prev_calculated - 1 : rsiBegin + InpMALength - 1;
   if(start < rsiBegin + InpMALength - 1) start = rsiBegin + InpMALength - 1;

   for(int i = start; i < calcTotal; i++)
   {
      if(InpMAType == RSI_MA_NONE || i < rsiBegin + InpMALength - 1)
      {
         ExtMABuffer[i]      = EMPTY_VALUE;
         ExtBBUpperBuffer[i] = EMPTY_VALUE;
         ExtBBLowerBuffer[i] = EMPTY_VALUE;
         continue;
      }

      double ma;
      switch(InpMAType)
      {
         case RSI_MA_EMA:
         {
            if(i == rsiBegin + InpMALength - 1)
               ma = SmaOnBuffer(ExtRSIBuffer, i, InpMALength); // seed EMA bang SMA, giong iMA chuan MT5
            else
            {
               double alpha = 2.0 / (InpMALength + 1.0);
               ma = ExtMABuffer[i - 1] + alpha * (ExtRSIBuffer[i] - ExtMABuffer[i - 1]);
            }
            break;
         }
         case RSI_MA_SMMA:
         {
            if(i == rsiBegin + InpMALength - 1)
               ma = SmaOnBuffer(ExtRSIBuffer, i, InpMALength); // seed RMA bang SMA
            else
               ma = ExtMABuffer[i - 1] + (ExtRSIBuffer[i] - ExtMABuffer[i - 1]) / InpMALength;
            break;
         }
         case RSI_MA_WMA:
            ma = WmaOnBuffer(ExtRSIBuffer, i, InpMALength);
            break;
         case RSI_MA_VWMA:
            ma = VwmaOnBuffer(ExtRSIBuffer, tick_volume, i, InpMALength);
            break;
         default: // RSI_MA_SMA, RSI_MA_SMA_BB
            ma = SmaOnBuffer(ExtRSIBuffer, i, InpMALength);
            break;
      }
      ExtMABuffer[i] = ma;

      if(InpMAType == RSI_MA_SMA_BB)
      {
         double dev = StdevOnBuffer(ExtRSIBuffer, i, InpMALength, ma) * InpBBMult;
         ExtBBUpperBuffer[i] = ma + dev;
         ExtBBLowerBuffer[i] = ma - dev;
      }
      else
      {
         ExtBBUpperBuffer[i] = EMPTY_VALUE;
         ExtBBLowerBuffer[i] = EMPTY_VALUE;
      }

   }

   //--- Log gia tri cua nen VUA DONG (1 dong/nen, khong log moi tick)
   bool newBar = (calcTotal >= 2 && time[calcTotal - 1] != ExtLastLogBar);
   if(newBar) ExtLastLogBar = time[calcTotal - 1];

   if(InpEnableDebugLog && newBar)
   {
      int c = calcTotal - 2;

      if(c >= rsiBegin)
      {
         string txt = TimeToString(time[c], TIME_DATE|TIME_MINUTES) +
                      " | RSI=" + DoubleToString(ExtRSIBuffer[c], 2);

         if(InpMAType != RSI_MA_NONE && ExtMABuffer[c] != EMPTY_VALUE)
            txt += " | MA=" + DoubleToString(ExtMABuffer[c], 2) +
                   " | RSI nam " + (ExtRSIBuffer[c] > ExtMABuffer[c] ? "TREN" : "DUOI") + " MA";

         if(InpMAType == RSI_MA_SMA_BB && ExtBBUpperBuffer[c] != EMPTY_VALUE)
            txt += " | BB[" + DoubleToString(ExtBBLowerBuffer[c], 2) + " - " +
                   DoubleToString(ExtBBUpperBuffer[c], 2) + "]";

         DebugLog(txt);
      }
   }

   return(calcTotal);
}
//+------------------------------------------------------------------+
