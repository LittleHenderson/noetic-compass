// CAS Forex MT4 mailbox bridge EA.
//
// Purpose:
// - Read CAS command JSON files from MQL4\Files\<MailboxRoot>\commands.
// - Acknowledge PAPER_MT4 commands by writing terminal receipt JSON.
// - Execute LIVE_MT4 only when the owner intentionally enables this EA input
//   and the command itself carries live authorization.
// - Write heartbeat and receipt JSON files back to <MailboxRoot>\receipts.
//
// The EA is deliberately schema-specific. MQL4 has no built-in JSON parser, so
// the helper functions below parse the stable CAS mailbox command shape.

#property strict

#define CAS_COMMAND_SCHEMA "cas_forex_mt4_mailbox_command.v1"
#define CAS_RECEIPT_SCHEMA "cas_forex_mt4_mailbox_receipt.v1"
#define MT4_TERMINAL_NAME "MetaTrader 4"

input string MailboxRoot = "CASForexMailbox";
input bool UseCommonFiles = false;
input bool LiveTradingAllowed = false;
input string SymbolSuffix = "";
input int TimerSeconds = 2;
input int MaxCommandsPerTimer = 10;

int OnInit()
{
   EnsureMailboxFolders();
   int seconds = TimerSeconds;
   if(seconds < 1)
      seconds = 1;
   EventSetTimer(seconds);
   WriteHeartbeat("INIT");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   WriteHeartbeat("DEINIT");
   EventKillTimer();
}

void OnTimer()
{
   EnsureMailboxFolders();
   WriteHeartbeat("TIMER");
   ProcessCommandMailbox();
}

void ProcessCommandMailbox()
{
   string fileName = "";
   string commandGlob = MailboxRoot + "\\commands\\*.json";
   long findHandle = FileFindFirst(commandGlob, fileName, FileScopeFlag());
   if(findHandle == INVALID_HANDLE)
      return;

   int processed = 0;
   do
   {
      if(processed >= MaxCommandsPerTimer)
         break;
      if(ProcessCommandFile(fileName))
         processed++;
   }
   while(FileFindNext(findHandle, fileName));

   FileFindClose(findHandle);
}

bool ProcessCommandFile(string fileName)
{
   string commandPath = MailboxRoot + "\\commands\\" + fileName;
   string commandJson = ReadTextFile(commandPath);
   if(commandJson == "")
      return false;

   string commandId = JsonString(commandJson, "command_id");
   if(commandId == "")
      commandId = FileBaseName(fileName);

   string receiptId = "receipt-" + commandId;
   string receiptPath = MailboxRoot + "\\receipts\\" + receiptId + ".json";
   if(FileIsExist(receiptPath, FileScopeFlag()))
      return false;

   string schema = JsonString(commandJson, "schema");
   string commandType = JsonString(commandJson, "command_type");
   string brokerMode = JsonString(commandJson, "broker_mode");
   string rawRequestHash = JsonString(commandJson, "raw_request_hash");
   bool commandLiveAuthorized = JsonBool(commandJson, "live_money_authorized", false);

   if(schema != CAS_COMMAND_SCHEMA)
   {
      WriteReceipt(receiptPath, receiptId, commandId, "REJECTED", rawRequestHash, brokerMode,
         false, 0, 0.0, 0.0, 0.0, -9101, "unsupported command schema");
      return true;
   }

   if(commandType == "PING")
   {
      WriteReceipt(receiptPath, receiptId, commandId, "ACKNOWLEDGED", rawRequestHash, brokerMode,
         false, 0, 0.0, 0.0, 0.0, 0, "ping acknowledged");
      return true;
   }

   if(commandType != "PLACE_ORDER")
   {
      WriteReceipt(receiptPath, receiptId, commandId, "REJECTED", rawRequestHash, brokerMode,
         false, 0, 0.0, 0.0, 0.0, -9102, "unsupported command_type");
      return true;
   }

   return HandlePlaceOrderCommand(receiptPath, receiptId, commandId, commandJson, brokerMode,
      rawRequestHash, commandLiveAuthorized);
}

bool HandlePlaceOrderCommand(
   string receiptPath,
   string receiptId,
   string commandId,
   string commandJson,
   string brokerMode,
   string rawRequestHash,
   bool commandLiveAuthorized
)
{
   string orderJson = JsonObject(commandJson, "order");
   string casSymbol = JsonString(orderJson, "symbol");
   string mt4Symbol = ToMt4Symbol(casSymbol);
   string direction = JsonString(orderJson, "direction");
   string orderType = JsonString(orderJson, "order_type");
   string comment = JsonString(orderJson, "comment");
   double volume = JsonNumber(orderJson, "volume", 0.0);
   double requestedPrice = JsonNumber(orderJson, "price", 0.0);
   double stopLoss = JsonNumber(orderJson, "stop_loss", 0.0);
   double takeProfit = JsonNumber(orderJson, "take_profit", 0.0);
   int slippage = JsonInt(orderJson, "slippage", 30);
   int magicNumber = JsonInt(orderJson, "magic_number", 20260624);
   int expiryMinutes = JsonInt(orderJson, "expiry_minutes", 5);

   if(comment == "")
      comment = "CAS_FOREX_AUTO";
   if(orderType == "")
      orderType = "MARKET";

   int operation = ToMt4Operation(orderType, direction);
   if(mt4Symbol == "" || operation < 0 || volume <= 0.0)
   {
      WriteReceipt(receiptPath, receiptId, commandId, "REJECTED", rawRequestHash, brokerMode,
         false, 0, requestedPrice, volume, 0.0, -9201, "invalid order fields");
      return true;
   }

   SymbolSelect(mt4Symbol, true);
   RefreshRates();
   double fillPrice = EffectiveOrderPrice(mt4Symbol, operation, requestedPrice);
   double slippagePips = 0.0;
   if(requestedPrice > 0.0 && fillPrice > 0.0)
      slippagePips = MathAbs(fillPrice - requestedPrice) / PipSize(mt4Symbol);

   bool liveCommand = (brokerMode == "LIVE_MT4");
   if(!liveCommand)
   {
      WriteReceipt(receiptPath, receiptId, commandId, "ACKNOWLEDGED", rawRequestHash, brokerMode,
         false, 0, fillPrice, volume, slippagePips, 0, "paper command acknowledged");
      return true;
   }

   if(!LiveTradingAllowed || !commandLiveAuthorized)
   {
      WriteReceipt(receiptPath, receiptId, commandId, "REJECTED", rawRequestHash, brokerMode,
         false, 0, fillPrice, volume, slippagePips, -9301, "live command not authorized by EA and command");
      return true;
   }

   if(!IsTradeAllowed())
   {
      WriteReceipt(receiptPath, receiptId, commandId, "REJECTED", rawRequestHash, brokerMode,
         false, 0, fillPrice, volume, slippagePips, -9302, "terminal trading is not allowed");
      return true;
   }

   datetime expiry = 0;
   if(operation != OP_BUY && operation != OP_SELL)
   {
      int minutes = expiryMinutes;
      if(minutes < 1)
         minutes = 1;
      expiry = TimeCurrent() + minutes * 60;
   }

   ResetLastError();
   int ticket = OrderSend(
      mt4Symbol,
      operation,
      volume,
      fillPrice,
      slippage,
      stopLoss,
      takeProfit,
      comment,
      magicNumber,
      expiry,
      clrDodgerBlue
   );
   int errorCode = GetLastError();
   string status = "REJECTED";
   bool liveMode = false;
   if(ticket > 0)
   {
      status = "EXECUTED";
      liveMode = true;
      errorCode = 0;
   }

   WriteReceipt(receiptPath, receiptId, commandId, status, rawRequestHash, brokerMode,
      liveMode, ticket, fillPrice, volume, slippagePips, errorCode, "live command processed by MT4");
   return true;
}

void WriteHeartbeat(string state)
{
   string path = MailboxRoot + "\\heartbeat.json";
   int handle = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI | FileScopeFlag());
   if(handle == INVALID_HANDLE)
      return;

   string payload = "{"
      + "\"schema\":\"cas_forex_mt4_heartbeat.v1\","
      + "\"terminal\":\"" + MT4_TERMINAL_NAME + "\","
      + "\"terminal_build\":\"" + TerminalBuildText() + "\","
      + "\"state\":\"" + JsonEscape(state) + "\","
      + "\"account_id_hash\":\"" + AccountIdHash() + "\","
      + "\"server\":\"" + JsonEscape(AccountServer()) + "\","
      + "\"live_trading_allowed\":" + BoolJson(LiveTradingAllowed) + ","
      + "\"time\":\"" + JsonEscape(TimeText()) + "\""
      + "}";
   FileWriteString(handle, payload);
   FileClose(handle);
}

void WriteReceipt(
   string receiptPath,
   string receiptId,
   string commandId,
   string status,
   string rawRequestHash,
   string brokerMode,
   bool liveMode,
   int brokerTicket,
   double filledPrice,
   double filledVolume,
   double slippagePips,
   int errorCode,
   string message
)
{
   string core = "{"
      + "\"schema\":\"" + CAS_RECEIPT_SCHEMA + "\","
      + "\"receipt_id\":\"" + JsonEscape(receiptId) + "\","
      + "\"command_id\":\"" + JsonEscape(commandId) + "\","
      + "\"status\":\"" + JsonEscape(status) + "\","
      + "\"created_at\":\"" + JsonEscape(TimeText()) + "\","
      + "\"raw_request_hash\":\"" + JsonEscape(rawRequestHash) + "\","
      + "\"terminal_name\":\"" + MT4_TERMINAL_NAME + "\","
      + "\"terminal_build\":\"" + TerminalBuildText() + "\","
      + "\"account_id_hash\":\"" + AccountIdHash() + "\","
      + "\"server\":\"" + JsonEscape(AccountServer()) + "\","
      + "\"broker_mode\":\"" + JsonEscape(brokerMode) + "\","
      + "\"live_mode\":" + BoolJson(liveMode) + ","
      + "\"live_trading_allowed\":" + BoolJson(LiveTradingAllowed) + ","
      + "\"broker_ticket\":" + IntegerToString(brokerTicket) + ","
      + "\"filled_price\":" + PriceJson(filledPrice) + ","
      + "\"filled_volume\":" + DoubleToString(filledVolume, 2) + ","
      + "\"slippage_pips\":" + DoubleToString(slippagePips, 3) + ","
      + "\"commission\":0.0,"
      + "\"swap\":0.0,"
      + "\"error_code\":" + IntegerToString(errorCode) + ","
      + "\"message\":\"" + JsonEscape(message) + "\","
      + "\"account_snapshot\":" + AccountSnapshotJson();

   string responseHash = "mql4-" + SimpleHash(core);
   string payload = core + ",\"raw_response_hash\":\"" + responseHash + "\"}";

   int handle = FileOpen(receiptPath, FILE_WRITE | FILE_TXT | FILE_ANSI | FileScopeFlag());
   if(handle == INVALID_HANDLE)
      return;
   FileWriteString(handle, payload);
   FileClose(handle);
}

bool EnsureMailboxFolders()
{
   FolderCreate(MailboxRoot, FileScopeFlag());
   FolderCreate(MailboxRoot + "\\commands", FileScopeFlag());
   FolderCreate(MailboxRoot + "\\receipts", FileScopeFlag());
   FolderCreate(MailboxRoot + "\\archive", FileScopeFlag());
   return true;
}

int FileScopeFlag()
{
   if(UseCommonFiles)
      return FILE_COMMON;
   return 0;
}

string ReadTextFile(string path)
{
   int handle = FileOpen(path, FILE_READ | FILE_TXT | FILE_ANSI | FileScopeFlag());
   if(handle == INVALID_HANDLE)
      return "";
   int size = (int)FileSize(handle);
   string content = "";
   if(size > 0)
      content = FileReadString(handle, size);
   FileClose(handle);
   return content;
}

string JsonString(string json, string key)
{
   return JsonRawValue(json, key);
}

double JsonNumber(string json, string key, double fallback)
{
   string raw = JsonRawValue(json, key);
   if(raw == "")
      return fallback;
   return StrToDouble(raw);
}

int JsonInt(string json, string key, int fallback)
{
   string raw = JsonRawValue(json, key);
   if(raw == "")
      return fallback;
   return (int)StrToInteger(raw);
}

bool JsonBool(string json, string key, bool fallback)
{
   string raw = JsonRawValue(json, key);
   if(raw == "")
      return fallback;
   if(StringFind(raw, "true") >= 0 || StringFind(raw, "True") >= 0 || raw == "1")
      return true;
   if(StringFind(raw, "false") >= 0 || StringFind(raw, "False") >= 0 || raw == "0")
      return false;
   return fallback;
}

string JsonObject(string json, string key)
{
   string marker = "\"" + key + "\"";
   int keyPos = StringFind(json, marker);
   if(keyPos < 0)
      return "";
   int colon = StringFind(json, ":", keyPos + StringLen(marker));
   if(colon < 0)
      return "";
   int start = FindNextChar(json, "{", colon + 1);
   if(start < 0)
      return "";

   int depth = 0;
   bool inString = false;
   bool escaped = false;
   for(int i = start; i < StringLen(json); i++)
   {
      string ch = StringSubstr(json, i, 1);
      if(inString)
      {
         if(escaped)
         {
            escaped = false;
            continue;
         }
         if(ch == "\\")
         {
            escaped = true;
            continue;
         }
         if(ch == "\"")
            inString = false;
         continue;
      }
      if(ch == "\"")
      {
         inString = true;
         continue;
      }
      if(ch == "{")
         depth++;
      if(ch == "}")
      {
         depth--;
         if(depth == 0)
            return StringSubstr(json, start, i - start + 1);
      }
   }
   return "";
}

string JsonRawValue(string json, string key)
{
   string marker = "\"" + key + "\"";
   int keyPos = StringFind(json, marker);
   if(keyPos < 0)
      return "";
   int colon = StringFind(json, ":", keyPos + StringLen(marker));
   if(colon < 0)
      return "";

   int start = SkipWhitespace(json, colon + 1);
   if(start >= StringLen(json))
      return "";

   string first = StringSubstr(json, start, 1);
   if(first == "\"")
      return ParseJsonQuotedString(json, start);

   int end = start;
   while(end < StringLen(json))
   {
      string ch = StringSubstr(json, end, 1);
      if(ch == "," || ch == "}" || ch == "]" || ch == "\r" || ch == "\n")
         break;
      end++;
   }
   return Trim(StringSubstr(json, start, end - start));
}

string ParseJsonQuotedString(string json, int quoteStart)
{
   string value = "";
   bool escaped = false;
   for(int i = quoteStart + 1; i < StringLen(json); i++)
   {
      string ch = StringSubstr(json, i, 1);
      if(escaped)
      {
         if(ch == "n")
            value += "\n";
         else if(ch == "r")
            value += "\r";
         else if(ch == "t")
            value += "\t";
         else
            value += ch;
         escaped = false;
         continue;
      }
      if(ch == "\\")
      {
         escaped = true;
         continue;
      }
      if(ch == "\"")
         break;
      value += ch;
   }
   return value;
}

int SkipWhitespace(string text, int start)
{
   int i = start;
   while(i < StringLen(text))
   {
      int code = StringGetCharacter(text, i);
      if(code != 32 && code != 9 && code != 10 && code != 13)
         break;
      i++;
   }
   return i;
}

int FindNextChar(string text, string needle, int start)
{
   for(int i = start; i < StringLen(text); i++)
   {
      if(StringSubstr(text, i, 1) == needle)
         return i;
   }
   return -1;
}

string Trim(string value)
{
   int start = 0;
   int end = StringLen(value) - 1;
   while(start <= end)
   {
      int codeStart = StringGetCharacter(value, start);
      if(codeStart != 32 && codeStart != 9 && codeStart != 10 && codeStart != 13)
         break;
      start++;
   }
   while(end >= start)
   {
      int codeEnd = StringGetCharacter(value, end);
      if(codeEnd != 32 && codeEnd != 9 && codeEnd != 10 && codeEnd != 13)
         break;
      end--;
   }
   if(end < start)
      return "";
   return StringSubstr(value, start, end - start + 1);
}

string ToMt4Symbol(string casSymbol)
{
   string out = casSymbol;
   StringReplace(out, "/", "");
   StringReplace(out, "_", "");
   StringReplace(out, "-", "");
   return out + SymbolSuffix;
}

int ToMt4Operation(string orderType, string direction)
{
   bool isLong = (direction == "LONG" || direction == "BUY");
   bool isShort = (direction == "SHORT" || direction == "SELL");
   if(!isLong && !isShort)
      return -1;
   if(orderType == "LIMIT")
      return isLong ? OP_BUYLIMIT : OP_SELLLIMIT;
   if(orderType == "STOP")
      return isLong ? OP_BUYSTOP : OP_SELLSTOP;
   return isLong ? OP_BUY : OP_SELL;
}

double EffectiveOrderPrice(string symbol, int operation, double requestedPrice)
{
   if(operation != OP_BUY && operation != OP_SELL && requestedPrice > 0.0)
      return NormalizeDouble(requestedPrice, (int)MarketInfo(symbol, MODE_DIGITS));

   double price = requestedPrice;
   if(price <= 0.0)
   {
      if(operation == OP_SELL || operation == OP_SELLLIMIT || operation == OP_SELLSTOP)
         price = MarketInfo(symbol, MODE_BID);
      else
         price = MarketInfo(symbol, MODE_ASK);
   }
   return NormalizeDouble(price, (int)MarketInfo(symbol, MODE_DIGITS));
}

double PipSize(string symbol)
{
   double point = MarketInfo(symbol, MODE_POINT);
   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   if(digits == 3 || digits == 5)
      return point * 10.0;
   return point;
}

string AccountSnapshotJson()
{
   return "{"
      + "\"balance\":" + DoubleToString(AccountBalance(), 2) + ","
      + "\"equity\":" + DoubleToString(AccountEquity(), 2) + ","
      + "\"margin\":" + DoubleToString(AccountMargin(), 2) + ","
      + "\"margin_free\":" + DoubleToString(AccountFreeMargin(), 2) + ","
      + "\"currency\":\"" + JsonEscape(AccountCurrency()) + "\","
      + "\"leverage\":" + IntegerToString(AccountLeverage())
      + "}";
}

string AccountIdHash()
{
   return "mt4-" + SimpleHash(IntegerToString(AccountNumber()) + "|" + AccountServer());
}

string TerminalBuildText()
{
   return IntegerToString((int)TerminalInfoInteger(TERMINAL_BUILD));
}

string TimeText()
{
   return TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS);
}

string BoolJson(bool value)
{
   if(value)
      return "true";
   return "false";
}

string PriceJson(double value)
{
   return DoubleToString(value, 8);
}

string FileBaseName(string fileName)
{
   int pos = StringFind(fileName, ".json");
   if(pos > 0)
      return StringSubstr(fileName, 0, pos);
   return fileName;
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
