import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

print("=== START test_alpaca.py ===", flush=True)

# .env 로드
loaded = load_dotenv()
print("dotenv loaded:", loaded, flush=True)

# 환경변수 존재 확인(값은 출력하지 않음)
print("has KEY:", "APCA_API_KEY_ID" in os.environ, flush=True)
print("has SECRET:", "APCA_API_SECRET_KEY" in os.environ, flush=True)

trading = TradingClient(
    os.environ["APCA_API_KEY_ID"],
    os.environ["APCA_API_SECRET_KEY"],
    paper=True,
)

acct = trading.get_account()
print("status:", acct.status, flush=True)
print("cash:", acct.cash, flush=True)
print("buying_power:", acct.buying_power, flush=True)

print("=== END test_alpaca.py ===", flush=True)
