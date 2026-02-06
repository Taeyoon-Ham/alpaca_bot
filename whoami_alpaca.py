import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

trading = TradingClient(
    os.environ["APCA_API_KEY_ID"],
    os.environ["APCA_API_SECRET_KEY"],
    paper=True,
)

acct = trading.get_account()
print("account_number:", getattr(acct, "account_number", None))
print("status:", acct.status)
print("currency:", getattr(acct, "currency", None))
print("cash:", acct.cash)
