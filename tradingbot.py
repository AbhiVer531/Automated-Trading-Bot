from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime, timedelta as Timedelta
from alpaca_trade_api import REST
from finbert_utils import estimate_sentiment

# data from my Alpaca Paper Trading Account
API_KEY = "PKJ7CL0IDGE77T086RAR"
API_SECRET = "YZyAwTrqxd89pBumXkQqmTybmrV8o2P6JZ0fLceT"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY" : API_KEY,
    "API_SECRET" : API_SECRET,
    "PAPER" : True
}

# backbone of trading bot; trading logic 
class MLTrader(Strategy):
    # runs once upon start
    def initialize(self, symbol:str = "SPY", cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    # sets the amount that bot will purchase 
    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price)
        return cash, last_price, quantity
    
    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, start=three_days_prior, end=today)
        news = [event.__dict__["_raw"]["headline"] for event in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment


    # run for every pass/new data from data source
    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
            if sentiment == "positive" and probability>.999:
                if self.last_trade == "sell":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price = last_price*1.20,
                    stop_loss_price = last_price*.95
                )
                self.submit_order(order)
                self.last_trade = "buy"
            elif sentiment == "negative" and probability>.999:
                if self.last_trade == "buy":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket",
                    take_profit_price = last_price*.8,
                    stop_loss_price = last_price*1.05
                )
                self.submit_order(order)
                self.last_trade = "sell"


start_date = datetime(2020,1,1)
end_date = datetime(2023,12,31)

broker = Alpaca(ALPACA_CREDS)

# create instance of strategy 
strategy = MLTrader(name='mlstrat', broker=broker, parameters={"symbol":"SPY", "cash_at_risk":.5})

# set up back testing
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters = {"symbol":"SPY"}
)

#trader = Trader()
#trader.add_strategy(strategy)
#trader.run_all()