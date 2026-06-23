from cas_forex.mt_history_import import parse_mt_history_text, summarize_imported_history


def test_mt_history_import_parses_csv_and_detects_bursts():
    text = """Ticket,Symbol,Type,Lots,Open Time,Open Price,Close Time,Close Price,Profit
1,GBPUSD,buy,0.50,2023.05.03 20:49:31,84.521,2023.05.03 21:10:00,84.289,85.73
2,GBPUSD,buy,0.50,2023.05.03 20:49:31,84.523,2023.05.03 21:10:00,84.288,86.84
3,GBPUSD,buy,2.50,2023.05.03 20:49:31,84.250,2023.05.03 21:20:00,84.133,216.43
4,EURUSD,sell,0.22,2017.12.15 20:45,1.17626,2017.12.15 21:00,1.17536,19.80
5,EURNZD,buy,1.00,2023.05.03 20:08:51,1.77243,2023.05.03 20:25:00,1.77237,-3.75
"""

    trades = parse_mt_history_text(text, source_name="history-mt5.csv")
    report = summarize_imported_history(trades, source_name="history-mt5.csv")

    assert report["closed_trade_count"] == 5
    assert report["winning_trades"] == 4
    assert report["losing_trades"] == 1
    assert report["by_symbol"]["GBP/USD"]["trades"] == 3
    assert report["bursts"]["multi_trade_bursts"] == 1
    assert report["bursts"]["max_orders_same_timestamp"] == 3
    assert report["broker_accept_status"] == "NOT LICENSED"


def test_mt_history_import_parses_html_table():
    text = """
    <table>
      <tr><th>Ticket</th><th>Symbol</th><th>Type</th><th>Size</th><th>Open Price</th><th>Close Price</th><th>Profit</th></tr>
      <tr><td>7</td><td>EURUSD</td><td>sell</td><td>1.00</td><td>1.07446</td><td>1.07391</td><td>55.00</td></tr>
      <tr><td>8</td><td>EURUSD</td><td>buy</td><td>1.00</td><td>1.07332</td><td>1.07281</td><td>-51.00</td></tr>
    </table>
    """

    trades = parse_mt_history_text(text, source_name="statement-mt4.html")
    report = summarize_imported_history(trades, source_name="statement-mt4.html")

    assert [trade.symbol for trade in trades] == ["EUR/USD", "EUR/USD"]
    assert report["platform_guess"] == "MT4"
    assert report["by_symbol"]["EUR/USD"]["wins"] == 1
    assert report["by_symbol"]["EUR/USD"]["losses"] == 1

