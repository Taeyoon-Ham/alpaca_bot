import os
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest

load_dotenv()

trading = TradingClient(
    os.environ["APCA_API_KEY_ID"],
    os.environ["APCA_API_SECRET_KEY"],
    paper=True,
)

# status를 아예 지정하지 않는다 (버전 호환 100%)
req = GetOrdersRequest(
    limit=50,
)

orders = trading.get_orders(req)

print("ORDERS:", len(orders))
for o in orders:
    print(
        "created:", o.created_at,
        "| id:", o.id,
        "|", o.symbol, o.side,
        "| qty:", o.qty,
        "| status:", o.status,
        "| type:", o.order_type,
        "| tif:", o.time_in_force,
        "| filled:", o.filled_qty,
    )
