import os
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

print("=== START order_spy ===", flush=True)

load_dotenv()
print("dotenv loaded:", True, flush=True)
print("has KEY:", "APCA_API_KEY_ID" in os.environ, flush=True)
print("has SECRET:", "APCA_API_SECRET_KEY" in os.environ, flush=True)

trading = TradingClient(
    os.environ["APCA_API_KEY_ID"],
    os.environ["APCA_API_SECRET_KEY"],
    paper=True,
)

print("connected trading client", flush=True)

order = MarketOrderRequest(
    symbol="SPY",
    qty=1,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
)

resp = trading.submit_order(order)
print("submitted order id:", resp.id, flush=True)
print("status:", resp.status, flush=True)

print("=== END order_spy ===", flush=True)
