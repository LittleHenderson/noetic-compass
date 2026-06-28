// CASForexHistoryExporterEA.mq4 - CAS Forex MT4 closed-history exporter EA.
//
// Purpose:
// - Read closed Account History rows from the attached MT4 terminal.
// - Write CAS-shaped history JSON into MQL4\Files\<MailboxRoot>\history.
// - Write exporter health/status JSON into MQL4\Files\<MailboxRoot>\status.
// - Never place, modify, or close broker orders.

#property strict

#define CAS_HISTORY_EXPORT_SCHEMA "cas_forex_mt4_closed_history_export.v1"
#define CAS_HISTORY_ORDER_SCHEMA "cas_forex_mt4_closed_history_order.v1"
#define CAS_HISTORY_STATUS_SCHEMA "cas_forex_mt4_closed_history_status.v1"
#define MT4_TERMINAL_NAME "MetaTrader 4"

input string MailboxRoot = "CASForexMailbox";
input bool UseCommonFiles = false;
input int ExportSeconds = 30;
input int LookbackDays = 30;
input int MaxClosedOrders = 500;
input int MagicNumberFilter = 0;
input bool IncludePendingOrders = false;
input string BrokerMode = "PAPER_MT4";

int OnInit()
{
   EnsureExporterFolders();
   int seconds = ExportSeconds;
   if(seconds < 1)
      seconds = 1;
   EventSetTimer(seconds);
   ExportClosedHistory("INIT");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   ExportClosedHistory("DEINIT");
   EventKillTimer();
}

void OnTimer()
{
   EnsureExporterFolders();
   ExportClosedHistory("TIMER");
}

void ExportClosedHistory(string trigger)
{
   string historyPath = HistoryRoot() + "\\cas_forex_closed_history.json";
   int handle = FileOpen(historyPath, FILE_WRITE | FILE_TXT | FILE_ANSI | FileScopeFlag());
   if(handle == INVALID_HANDLE)
   {
      WriteStatus("EXPORT_FAILED", trigger, 0, 0, 0.0, GetLastError(), "could not open history export file");
      return;
   }

   int total = OrdersHistoryTotal();
   int scanned = 0;
   int exported = 0;
   double netProfitLoss = 0.0;
   double totalCommission = 0.0;
   double totalSwap = 0.0;
   bool first = true;

   FileWriteString(handle, "{");
   FileWriteString(handle, "\"schema\":\"" + CAS_HISTORY_EXPORT_SCHEMA + "\",");
   FileWriteString(handle, "\"terminal\":\"" + MT4_TERMINAL_NAME + "\",");
   FileWriteString(handle, "\"terminal_build\":\"" + TerminalBuildText() + "\",");
   FileWriteString(handle, "\"server\":\"" + JsonEscape(AccountServer()) + "\",");
   FileWriteString(handle, "\"account_id_hash\":\"" + AccountIdHash() + "\",");
   FileWriteString(handle, "\"account_currency\":\"" + JsonEscape(AccountCurrency()) + "\",");
   FileWriteString(handle, "\"account_leverage\":" + IntegerToString(AccountLeverage()) + ",");
   FileWriteString(handle, "\"broker_mode\":\"" + JsonEscape(BrokerMode) + "\",");
   FileWriteString(handle, "\"exported_at\":\"" + JsonEscape(TimeText(TimeCurrent())) + "\",");
   FileWriteString(handle, "\"lookback_days\":" + IntegerToString(LookbackDays) + ",");
   FileWriteString(handle, "\"max_closed_orders\":" + IntegerToString(MaxClosedOrders) + ",");
   FileWriteString(handle, "\"magic_number_filter\":" + IntegerToString(MagicNumberFilter) + ",");
   FileWriteString(handle, "\"history_records\":[");

   for(int i = total - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
         continue;

      scanned++;
      if(!ShouldExportSelectedOrder())
         continue;

      if(exported >= MaxClosedOrders)
         break;

      double net = OrderProfit() + OrderCommission() + OrderSwap();
      netProfitLoss += net;
      totalCommission += OrderCommission();
      totalSwap += OrderSwap();

      if(!first)
         FileWriteString(handle, ",");
      FileWriteString(handle, SelectedOrderJson(net));
      first = false;
      exported++;
   }

   FileWriteString(handle, "],");
   FileWriteString(handle, "\"summary\":{");
   FileWriteString(handle, "\"orders_history_total\":" + IntegerToString(total) + ",");
   FileWriteString(handle, "\"scanned_order_count\":" + IntegerToString(scanned) + ",");
   FileWriteString(handle, "\"exported_order_count\":" + IntegerToString(exported) + ",");
   FileWriteString(handle, "\"net_profit_loss_account\":" + MoneyJson(netProfitLoss) + ",");
   FileWriteString(handle, "\"total_commission\":" + MoneyJson(totalCommission) + ",");
   FileWriteString(handle, "\"total_swap\":" + MoneyJson(totalSwap));
   FileWriteString(handle, "},");
   FileWriteString(handle, "\"claim_boundary\":\"" + JsonEscape(ClaimBoundary()) + "\"");
   FileWriteString(handle, "}");
   FileClose(handle);

   WriteStatus("EXPORT_COMPLETE", trigger, scanned, exported, netProfitLoss, 0, "closed history export written");
}

bool ShouldExportSelectedOrder()
{
   datetime closeTime = OrderCloseTime();
   if(closeTime <= 0)
      return false;

   int type = OrderType();
   bool marketOrder = (type == OP_BUY || type == OP_SELL);
   if(!marketOrder && !IncludePendingOrders)
      return false;

   if(MagicNumberFilter != 0 && OrderMagicNumber() != MagicNumberFilter)
      return false;

   if(LookbackDays > 0)
   {
      datetime threshold = TimeCurrent() - LookbackDays * 86400;
      if(closeTime < threshold)
         return false;
   }
   return true;
}

string SelectedOrderJson(double netProfitLoss)
{
   string comment = OrderComment();
   string commandId = ExtractCommandId(comment);
   string receiptId = "";
   if(commandId != "")
      receiptId = "receipt-" + commandId;

   string out = "{";
   out += "\"schema\":\"" + CAS_HISTORY_ORDER_SCHEMA + "\",";
   out += "\"ticket\":\"" + IntegerToString(OrderTicket()) + "\",";
   out += "\"broker_ticket\":\"" + IntegerToString(OrderTicket()) + "\",";
   out += "\"command_id\":\"" + JsonEscape(commandId) + "\",";
   out += "\"receipt_id\":\"" + JsonEscape(receiptId) + "\",";
   out += "\"symbol\":\"" + JsonEscape(OrderSymbol()) + "\",";
   out += "\"direction\":\"" + DirectionText(OrderType()) + "\",";
   out += "\"lots\":" + DoubleToString(OrderLots(), 2) + ",";
   out += "\"open_time\":\"" + JsonEscape(TimeText(OrderOpenTime())) + "\",";
   out += "\"close_time\":\"" + JsonEscape(TimeText(OrderCloseTime())) + "\",";
   out += "\"open_price\":" + PriceJson(OrderOpenPrice()) + ",";
   out += "\"close_price\":" + PriceJson(OrderClosePrice()) + ",";
   out += "\"stop_loss\":" + PriceJson(OrderStopLoss()) + ",";
   out += "\"take_profit\":" + PriceJson(OrderTakeProfit()) + ",";
   out += "\"profit\":" + MoneyJson(OrderProfit()) + ",";
   out += "\"profit_loss_account\":" + MoneyJson(netProfitLoss) + ",";
   out += "\"commission\":" + MoneyJson(OrderCommission()) + ",";
   out += "\"swap\":" + MoneyJson(OrderSwap()) + ",";
   out += "\"magic_number\":" + IntegerToString(OrderMagicNumber()) + ",";
   out += "\"comment\":\"" + JsonEscape(comment) + "\",";
   out += "\"close_reason\":\"MT4_CLOSED_HISTORY\",";
   out += "\"broker_mode\":\"" + JsonEscape(BrokerMode) + "\",";
   out += "\"terminal\":\"" + MT4_TERMINAL_NAME + "\",";
   out += "\"terminal_build\":\"" + TerminalBuildText() + "\",";
   out += "\"server\":\"" + JsonEscape(AccountServer()) + "\",";
   out += "\"account_id_hash\":\"" + AccountIdHash() + "\",";
   out += "\"account_currency\":\"" + JsonEscape(AccountCurrency()) + "\"";
   out += "}";
   return out;
}

void WriteStatus(
   string status,
   string trigger,
   int scanned,
   int exported,
   double netProfitLoss,
   int errorCode,
   string message
)
{
   EnsureExporterFolders();
   string statusPath = StatusRoot() + "\\cas_forex_closed_history_status.json";
   int handle = FileOpen(statusPath, FILE_WRITE | FILE_TXT | FILE_ANSI | FileScopeFlag());
   if(handle == INVALID_HANDLE)
      return;

   string payload = "{";
   payload += "\"schema\":\"" + CAS_HISTORY_STATUS_SCHEMA + "\",";
   payload += "\"export_status\":\"" + JsonEscape(status) + "\",";
   payload += "\"trigger\":\"" + JsonEscape(trigger) + "\",";
   payload += "\"terminal\":\"" + MT4_TERMINAL_NAME + "\",";
   payload += "\"terminal_build\":\"" + TerminalBuildText() + "\",";
   payload += "\"server\":\"" + JsonEscape(AccountServer()) + "\",";
   payload += "\"account_id_hash\":\"" + AccountIdHash() + "\",";
   payload += "\"broker_mode\":\"" + JsonEscape(BrokerMode) + "\",";
   payload += "\"exported_at\":\"" + JsonEscape(TimeText(TimeCurrent())) + "\",";
   payload += "\"history_path\":\"" + JsonEscape(HistoryRoot() + "\\cas_forex_closed_history.json") + "\",";
   payload += "\"scanned_order_count\":" + IntegerToString(scanned) + ",";
   payload += "\"exported_order_count\":" + IntegerToString(exported) + ",";
   payload += "\"net_profit_loss_account\":" + MoneyJson(netProfitLoss) + ",";
   payload += "\"error_code\":" + IntegerToString(errorCode) + ",";
   payload += "\"message\":\"" + JsonEscape(message) + "\",";
   payload += "\"claim_boundary\":\"" + JsonEscape(ClaimBoundary()) + "\"";
   payload += "}";
   FileWriteString(handle, payload);
   FileClose(handle);
}

bool EnsureExporterFolders()
{
   FolderCreate(MailboxRoot, FileScopeFlag());
   FolderCreate(HistoryRoot(), FileScopeFlag());
   FolderCreate(StatusRoot(), FileScopeFlag());
   return true;
}

string HistoryRoot()
{
   return MailboxRoot + "\\history";
}

string StatusRoot()
{
   return MailboxRoot + "\\status";
}

int FileScopeFlag()
{
   if(UseCommonFiles)
      return FILE_COMMON;
   return 0;
}

string DirectionText(int type)
{
   if(type == OP_BUY)
      return "buy";
   if(type == OP_SELL)
      return "sell";
   if(type == OP_BUYLIMIT)
      return "buy_limit";
   if(type == OP_SELLLIMIT)
      return "sell_limit";
   if(type == OP_BUYSTOP)
      return "buy_stop";
   if(type == OP_SELLSTOP)
      return "sell_stop";
   return "unknown";
}

string ExtractCommandId(string comment)
{
   int pos = StringFind(comment, "agent-");
   if(pos < 0)
      return "";

   int end = pos;
   while(end < StringLen(comment))
   {
      int code = StringGetCharacter(comment, end);
      bool alpha = (code >= 65 && code <= 90) || (code >= 97 && code <= 122);
      bool digit = (code >= 48 && code <= 57);
      bool allowed = alpha || digit || code == 45 || code == 95;
      if(!allowed)
         break;
      end++;
   }
   return StringSubstr(comment, pos, end - pos);
}

string AccountIdHash()
{
   return "mt4-" + SimpleHash(IntegerToString(AccountNumber()) + "|" + AccountServer());
}

string TerminalBuildText()
{
   return IntegerToString((int)TerminalInfoInteger(TERMINAL_BUILD));
}

string TimeText(datetime value)
{
   return TimeToString(value, TIME_DATE | TIME_SECONDS);
}

string PriceJson(double value)
{
   return DoubleToString(value, 8);
}

string MoneyJson(double value)
{
   return DoubleToString(value, 2);
}

string ClaimBoundary()
{
   return "MT4 closed-history exporter reads closed terminal history and writes evidence files only. It does not place live broker orders, create broker ACCEPT, deposit, withdraw, move bank/card funds, or automate payouts.";
}

string JsonEscape(string value)
{
   string out = value;
   StringReplace(out, "\\", "\\\\");
   StringReplace(out, "\"", "\\\"");
   StringReplace(out, "\r", " ");
   StringReplace(out, "\n", " ");
   StringReplace(out, "\t", " ");
   return out;
}

string SimpleHash(string value)
{
   uint hash = 2166136261;
   for(int i = 0; i < StringLen(value); i++)
   {
      uint code = (uint)StringGetCharacter(value, i);
      hash = (hash ^ code) * 16777619;
   }
   return StringFormat("%08X", hash);
}
