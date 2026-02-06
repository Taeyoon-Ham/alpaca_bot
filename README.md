# Regime-Aware Core–Overlay Portfolio (SPY Core + Gated Overlay) — Research → Execution (Alpaca Paper)

This repository is an execution-ready prototype that bridges **strategy research** and **real-world portfolio operations**.

The design goal is straightforward:
- **Keep market beta (SPY) as the durable baseline**
- Add a **small, conditional overlay** only when market structure is favorable
- Implement **risk guards, turnover limits, and operational safety** so the strategy can be run repeatedly without accidental overtrading

This project was built to demonstrate practical capability across:
1) **Systematic research** (signals, gates, evaluation, walk-forward discipline)  
2) **Execution engineering** (target-weight rebalancing, order placement, safety controls, logs)

> Status: **Paper trading only** (Alpaca Paper). No live capital.

---

## Why this exists (motivation)

In practice, **beating SPY consistently is hard**. Many “alpha” overlays look good in a backtest but fail in live conditions due to:
- regime shifts (signals decay)
- crowding (diversification breakdown)
- high turnover (costs dominate)
- poor execution plumbing (overfills, duplicate orders, unintended leverage)

So this repository uses a **Core–Overlay** structure:
- **Core:** SPY = 100% baseline exposure  
- **Overlay:** small tactical sleeve across {QQQ, IWM, TLT, GLD}  
- **Gates:** overlay is only active in regimes where it has shown positive “active edge”

---

## Strategy thesis (one paragraph)

The core thesis is that the market premium is persistent but overlays are not.  
Therefore, the strategy holds SPY continuously and uses a **regime-aware overlay** that turns on only during conditions associated with better tactical outcomes—specifically when **crowding risk is low** and the overlay’s **recent active Information Ratio is positive**. The overlay is rebalanced weekly to reduce turnover, and strict **gross exposure and turnover constraints** are enforced to keep the live behavior stable and auditable.

---

## High-level rules

### Universe
- **SPY**: core benchmark and permanent holding  
- **QQQ**: growth/tech tilt (risk-on overlay)  
- **IWM**: small-cap tilt (risk-on overlay)  
- **TLT**: long-duration treasuries (risk-off overlay)  
- **GLD**: gold (diversifier)

### Core–Overlay composition
- Total weights:  
  **w_total = w_core(SPY=1.0) + k(t) * w_overlay**
- Overlay scale `k(t)` is small and time-varying (gate-controlled)

### Overlay regimes (example logic)
- **Bull + positive momentum:** allocate overlay to **QQQ/IWM**
- **Bear + defensive trend condition:** allocate overlay to **TLT/GLD**
- Otherwise: overlay is **0**

### Crowding filter
- Overlay is only allowed when **crowding score ≤ threshold** (low crowding regime)
- Threshold is computed as a quantile (e.g., 80/85/90%) and cached during search

### Performance gate (key)
Overlay is ON only if the overlay’s **recent active IR** is positive:
- Active proxy return: `r_overlay = sum(w_overlay * r_assets)`
- Rolling IR over 252 trading days:
  - If **IR ≤ 0**, set **k(t)=0**
  - If **IR > 0**, set **k(t)=k**

This gate is meant to reduce “always-on” overfitting and keep the overlay honest.

### Rebalancing
- **Weekly rebalance** (every 5 trading days)
- Weights held constant between rebalance dates (forward-filled)

---

## Risk controls (live behavior first)

This repository explicitly prioritizes operational safety over theoretical purity.

### Exposure caps
- Overlay gross cap: `sum(abs(w_overlay)) ≤ overlay_gross_cap`
- Total gross cap (core + overlay): `sum(abs(w_total)) ≤ lev_cap`
- Uses absolute weights so it remains robust even if future extensions introduce shorts

### Turnover and order-safety guards (execution layer)
The execution script enforces:
- **Dry-run mode by default** (prints a plan; no orders sent)
- `--max-notional`: per-order notional cap
- `--max-turnover`: total turnover cap (fraction of equity)
- `--max-orders`: maximum number of orders per run
- Execution logs (excluded from git)

These controls address the most common failure mode of personal trading bots: unintended large orders.

---

## Research workflow (how parameters are selected)

This project avoids huge grid searches that are slow and fragile.

- **Random search** with:
  - hard candidate cap
  - early stopping patience
  - precomputed signals to reduce repeated work
- Selection objective favors:
  - positive active return and alpha
  - beta near 1 (keep core character)
  - lower drawdown
  - lower turnover

Important note:
- This is still a research prototype; **parameter selection can overfit** if not validated carefully.
- The project is structured to allow walk-forward and more formal cross-validation extensions.

---

## Execution workflow (paper trading)

### What “execution-ready” means here
This repository includes a functional execution loop:
1) compute target weights (strategy output)
2) translate weights to target quantities (based on account equity and latest prices)
3) compute deltas vs current positions
4) place market orders (paper) with risk guards

### Current implementation
- **Alpaca Paper** integration is validated end-to-end:
  - account connectivity
  - order submission
  - order lookup
  - positions query
  - one-shot rebalance with caps

---

## Repository layout (suggested)

The execution prototype currently includes scripts such as:
- `rebalance_once.py`: one-shot rebalancing engine (dry-run by default)
- `positions.py`: inspect holdings
- `get_order_by_id.py`: order audit by ID
- `check_orders.py`: order list checks
- `whoami_alpaca.py`: account connectivity check (no sensitive identifiers printed)

Recommended next structure (if expanding):

---

## How to run (paper)

### 1) Setup
- Create a virtual environment
- Install dependencies
- Create a `.env` file with Alpaca paper keys (never commit)

### 2) Verify connectivity
- Run `whoami_alpaca.py` / `test_alpaca.py`

### 3) Dry-run rebalance (safe)
- `python rebalance_once.py`

### 4) Submit rebalance (paper)
- `python rebalance_once.py --submit`

### 5) Inspect outcomes
- `python positions.py`
- `python get_order_by_id.py` (paste an order id)

---

## What I would discuss in an interview (talk track)

### 1) What problem this solves
Most candidates stop at backtests. I wanted to demonstrate I can:
- design a systematic strategy *and*
- build the operational layer needed to run it repeatedly with safety controls

### 2) Why SPY core + gated overlay
- SPY is a strong baseline; many overlays degrade out-of-sample  
- gating by rolling active IR prevents “always-on” exposure  
- crowding filter reduces exposure during diversification breakdown

### 3) What can fail (and how I mitigate)
- Regime misclassification → reduce overlay size and rebalance weekly  
- Crowding proxy instability → quantile thresholds + robustness checks  
- Slippage and fast markets → turnover caps + order caps + dry-run default  
- Operational mistakes → idempotent one-shot rebalance and logging

### 4) What I would improve next
- formal walk-forward + stability diagnostics
- explicit transaction-cost model + slippage estimation
- limit-order / execution scheduling for larger size
- monitoring (alerts, daily report, anomaly detection)
- broker abstraction layer (Alpaca → IBKR/Korea broker APIs)

---

## Limitations and disclaimers

- This is a **research prototype** and **paper execution** example.  
- Past backtests do not guarantee future performance.  
- Market orders can incur slippage; real fills may differ materially from backtest assumptions.  
- Use at your own risk.

---

## Roadmap (next upgrades that matter in practice)

1) **Strategy → Execution connection**
   - export daily/weekly `target_weights.json`
   - `rebalance_once.py` reads the weights file (remove hardcoded weights)

2) **Walk-forward evaluation**
   - rolling retrain windows + fixed holdout
   - parameter stability metrics

3) **Execution realism**
   - slippage model
   - partial fills
   - market-hours + liquidity checks
   - order retry/timeout/cancel logic

4) **Monitoring**
   - daily email/console summary
   - risk limit breach alerts
   - position drift detection
