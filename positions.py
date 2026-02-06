import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

trading = TradingClient(
    os.environ["APCA_API_KEY_ID"],
    os.environ["APCA_API_SECRET_KEY"],
    paper=True,
)

pos = trading.get_all_positions()
print("POSITIONS:", len(pos))
for p in pos:
    print(p.symbol, "qty=", p.qty, "avg=", p.avg_entry_price, "upl=", p.unrealized_pl)
