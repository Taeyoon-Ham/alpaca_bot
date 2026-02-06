import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

ORDER_ID = "6ed50102-aa74-4dfb-875c-e38393a7db48"  # <- 본인 주문 id

trading = TradingClient(
    os.environ["APCA_API_KEY_ID"],
    os.environ["APCA_API_SECRET_KEY"],
    paper=True,
)

o = trading.get_order_by_id(ORDER_ID)
print("id:", o.id)
print("symbol:", o.symbol)
print("status:", o.status)
print("qty:", o.qty, "filled:", o.filled_qty)
print("filled_avg_price:", getattr(o, "filled_avg_price", None))
print("created_at:", o.created_at)