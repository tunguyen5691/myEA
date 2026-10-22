//+------------------------------------------------------------------+
//| export_bars.mq5 - xuat nen ra CSV (mac dinh XAUUSD H1, 2 nam)     |
//+------------------------------------------------------------------+
#property script_show_inputs

input string          InpSymbol = "XAUUSD";
input ENUM_TIMEFRAMES InpTF     = PERIOD_H1;
input int             InpYears  = 2;

void OnStart()
{
   datetime to   = TimeCurrent();
   datetime from = to - (datetime)InpYears * 365 * 24 * 3600;

   MqlRates rates[];
   ArraySetAsSeries(rates, false); // cu -> moi
   int n = CopyRates(InpSymbol, InpTF, from, to, rates);
   if(n <= 0) { Print("CopyRates loi: ", GetLastError()); return; }

   int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   string fname = InpSymbol + "_" + StringSubstr(EnumToString(InpTF), 7) + ".csv";
   int h = FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("Mo file loi: ", GetLastError()); return; }

   FileWrite(h, "time", "open", "high", "low", "close", "tick_volume", "spread");
   for(int i = 0; i < n; i++)
      FileWrite(h, TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                DoubleToString(rates[i].open, digits),
                DoubleToString(rates[i].high, digits),
                DoubleToString(rates[i].low, digits),
                DoubleToString(rates[i].close, digits),
                rates[i].tick_volume, rates[i].spread);
   FileClose(h);

   // canh bao neu lich su ngan hon yeu cau (Max bars in chart thap / chua tai du)
   if(rates[0].time > from + 7 * 24 * 3600)
      Print("Canh bao: nen dau tien ", TimeToString(rates[0].time),
            " muon hon ", TimeToString(from), " - kiem tra Max bars in chart");
   Print("Da ghi ", n, " nen (", TimeToString(rates[0].time), " -> ",
         TimeToString(rates[n - 1].time), ") vao MQL5/Files/", fname);
}
