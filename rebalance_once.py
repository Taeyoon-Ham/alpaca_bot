import os
import math
import json
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest


# ===================
# USER CONFIG (전략 연결 전 임시 목표 비중)
# ===================
PAPER = True
UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD"]

# 테스트용(원하면 여기만 바꾸면 됨)
TARGET_WEIGHTS = {
    "SPY": 0.80,
    "QQQ": 0.20,
    "IWM": 0.00,
    "TLT": 0.00,
    "GLD": 0.00,
}
# ===================


@dataclass
class OrderPlan:
    symbol: str
    side: str               # "buy" / "sell"
    qty: int
    price: float
    notional: float


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_dirs() -> Path:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def load_last_run_stamp() -> dict:
    p = Path("logs") / "last_run.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_last_run_stamp(stamp: dict) -> None:
    p = Path("logs") / "last_run.json"
    p.write_text(json.dumps(stamp, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, rec: dict) -> None:
    line = json.dumps(rec, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_env_or_raise(key: str) -> str:
    v = os.environ.get(key, "").strip()
    if not v:
        raise RuntimeError(f"Missing {key} in environment (.env).")
    return v


def get_latest_price(data_client: StockHistoricalDataClient, symbol: str) -> float:
    req = StockLatestTradeRequest(symbol_or_symbols=symbol)
    latest = data_client.get_stock_latest_trade(req)
    trade = latest[symbol]
    return float(trade.price)


def fetch_positions(trading: TradingClient) -> Dict[str, float]:
    pos = {p.symbol: float(p.qty) for p in trading.get_all_positions()}
    return pos


def compute_target_qty(
    equity: float,
    weights: Dict[str, float],
    prices: Dict[str, float],
) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for sym, w in weights.items():
        w = float(w)
        if w <= 0.0:
            out[sym] = 0
            continue
        px = float(prices[sym])
        dollars = equity * w
        out[sym] = int(math.floor(dollars / px))
    return out


def build_plan(
    universe: List[str],
    weights: Dict[str, float],
    positions: Dict[str, float],
    prices: Dict[str, float],
    target_qty: Dict[str, int],
    min_notional: float,
) -> List[OrderPlan]:
    plans: List[OrderPlan] = []

    for sym in universe:
        now_qty = float(positions.get(sym, 0.0))
        tgt_qty = int(target_qty.get(sym, 0))
        delta = int(tgt_qty - now_qty)

        if delta == 0:
            continue

        px = float(prices[sym])
        notional = abs(delta) * px
        if notional < float(min_notional):
            continue

        side = "buy" if delta > 0 else "sell"
        plans.append(OrderPlan(symbol=sym, side=side, qty=abs(delta), price=px, notional=notional))

    return plans


def risk_checks(
    plans: List[OrderPlan],
    equity: float,
    max_notional_per_order: float,
    max_turnover_frac: float,
    max_orders: int,
) -> Tuple[bool, List[str]]:
    """
    Returns (ok, reasons_if_blocked)
    """
    reasons: List[str] = []

    if len(plans) == 0:
        return True, reasons

    if len(plans) > int(max_orders):
        reasons.append(f"Too many orders: {len(plans)} > max_orders={max_orders}")

    # per-order notional cap
    for p in plans:
        if p.notional > float(max_notional_per_order):
            reasons.append(
                f"Order notional too large: {p.symbol} {p.side} qty={p.qty} notional={p.notional:.2f} > max_notional={max_notional_per_order}"
            )

    # total turnover cap
    total_turnover = sum(p.notional for p in plans)
    if equity > 0 and (total_turnover / equity) > float(max_turnover_frac):
        reasons.append(
            f"Total turnover too large: {total_turnover:.2f} / {equity:.2f} = {total_turnover/equity:.2%} > max_turnover={max_turnover_frac:.2%}"
        )

    ok = (len(reasons) == 0)
    return ok, reasons


def submit_orders(
    trading: TradingClient,
    plans: List[OrderPlan],
) -> List[dict]:
    submitted = []
    for p in plans:
        side_enum = OrderSide.BUY if p.side == "buy" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=p.symbol,
            qty=p.qty,
            side=side_enum,
            time_in_force=TimeInForce.DAY,
        )
        resp = trading.submit_order(req)
        submitted.append(
            {
                "symbol": p.symbol,
                "side": p.side,
                "qty": p.qty,
                "id": str(resp.id),
                "status": str(resp.status),
            }
        )
    return submitted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submit", action="store_true", help="Actually submit orders (default: dry-run).")
    parser.add_argument("--min-notional", type=float, default=20.0, help="Skip orders smaller than this notional USD.")
    parser.add_argument("--max-notional", type=float, default=2000.0, help="Max notional per single order (USD).")
    parser.add_argument("--max-turnover", type=float, default=0.10, help="Max total turnover as fraction of equity. ex) 0.10=10%")
    parser.add_argument("--max-orders", type=int, default=5, help="Max number of orders per run.")
    parser.add_argument("--allow-multi-run-today", action="store_true", help="Allow multiple submits in the same UTC day.")
    args = parser.parse_args()

    load_dotenv()
    logs_dir = ensure_dirs()
    log_path = logs_dir / "trade_log.jsonl"

    key = get_env_or_raise("APCA_API_KEY_ID")
    sec = get_env_or_raise("APCA_API_SECRET_KEY")

    trading = TradingClient(key, sec, paper=PAPER)
    data_client = StockHistoricalDataClient(key, sec)

    acct = trading.get_account()
    equity = float(acct.portfolio_value)
    now = utc_now()

    # 중복 실행 방지 (제출일 기준)
    stamp = load_last_run_stamp()
    today_str = str(date.today())  # local date (PC 기준)
    utc_day = str(now.date())      # UTC date 기준

    # 실전에서는 UTC 기준이 보통 더 안전합니다.
    # 여기서는 UTC 기준으로 "오늘 이미 submit 했는지"를 차단합니다.
    if args.submit and (not args.allow_multi_run_today):
        last_submit_utc_day = stamp.get("last_submit_utc_day")
        if last_submit_utc_day == utc_day:
            print(f"[BLOCKED] Already submitted today (UTC day={utc_day}). Use --allow-multi-run-today to override.")
            return

    # 가격 조회
    prices: Dict[str, float] = {}
    for sym in UNIVERSE:
        # 목표 0이어도 prices를 다 받아두면 이후 매도 등에서도 깔끔합니다.
        prices[sym] = get_latest_price(data_client, sym)

    # 포지션
    positions = fetch_positions(trading)
    for sym in UNIVERSE:
        positions.setdefault(sym, 0.0)

    # 목표 수량
    target_qty = compute_target_qty(equity, TARGET_WEIGHTS, prices)

    # 주문 계획
    plans = build_plan(
        universe=UNIVERSE,
        weights=TARGET_WEIGHTS,
        positions=positions,
        prices=prices,
        target_qty=target_qty,
        min_notional=args.min_notional,
    )

    # 출력 (항상)
    print("UTC now:", now.isoformat())
    print("equity (portfolio_value):", round(equity, 2))

    print("\n--- CURRENT POSITIONS ---")
    for sym in UNIVERSE:
        print(sym, "qty=", positions.get(sym, 0.0))

    print("\n--- TARGET QTY ---")
    for sym in UNIVERSE:
        print(sym, "target_qty=", target_qty.get(sym, 0))

    print("\n--- PLAN ---")
    if not plans:
        print("No orders required.")
    else:
        total_turnover = sum(p.notional for p in plans)
        for p in plans:
            print(
                p.symbol,
                p.side,
                "qty=",
                p.qty,
                "px=",
                round(p.price, 4),
                "notional=",
                round(p.notional, 2),
            )
        print("TOTAL_TURNOVER:", round(total_turnover, 2), "USD")
        if equity > 0:
            print("TURNOVER / EQUITY:", f"{(total_turnover/equity):.2%}")

    # 리스크 체크
    ok, reasons = risk_checks(
        plans=plans,
        equity=equity,
        max_notional_per_order=args.max_notional,
        max_turnover_frac=args.max_turnover,
        max_orders=args.max_orders,
    )

    if not ok:
        print("\n[BLOCKED BY RISK CHECKS]")
        for r in reasons:
            print("-", r)

        # 로그 남김
        append_jsonl(
            log_path,
            {
                "ts_utc": now.isoformat(),
                "mode": "dry-run" if not args.submit else "submit",
                "blocked": True,
                "reasons": reasons,
                "equity": equity,
                "plans": [p.__dict__ for p in plans],
                "positions": positions,
                "target_qty": target_qty,
            },
        )
        return

    # 제출 여부
    if not args.submit:
        print("\n[DRY RUN] No orders submitted. Use --submit to place orders.")
        append_jsonl(
            log_path,
            {
                "ts_utc": now.isoformat(),
                "mode": "dry-run",
                "blocked": False,
                "equity": equity,
                "plans": [p.__dict__ for p in plans],
                "positions": positions,
                "target_qty": target_qty,
            },
        )
        return

    # 실제 주문 제출
    print("\n--- SUBMIT ---")
    submitted = submit_orders(trading, plans)
    for s in submitted:
        print("submitted:", s["symbol"], s["side"], "qty=", s["qty"], "| id:", s["id"], "| status:", s["status"])

    # 로그 + 스탬프 저장
    append_jsonl(
        log_path,
        {
            "ts_utc": now.isoformat(),
            "mode": "submit",
            "blocked": False,
            "equity": equity,
            "plans": [p.__dict__ for p in plans],
            "submitted": submitted,
            "positions": positions,
            "target_qty": target_qty,
        },
    )

    save_last_run_stamp(
        {
            "last_submit_utc_day": utc_day,
            "last_submit_ts_utc": now.isoformat(),
            "paper": PAPER,
        }
    )

    print("\nDone. Logs written to:", str(log_path))


if __name__ == "__main__":
    main()
