# Dev-window analysis — btc-race-24h-20261118-1444

Dev window: 2026-11-17 14:44 UTC → 2026-11-18 14:44 UTC, 1,440 one-minute
cbBTC bars, 0 gaps, 152 flat bars.

## Price structure

- Open $65,074.48 → close $63,260.75: **net −2.79%**. High $65,190.42, low $63,026.72.
- 1-minute returns: mean −0.20 bps, median 0, sd 6.67 bps, max +63.9 bps,
  min −52.4 bps. Only 3 bars moved more than 50 bps in a minute: the
  action lives in slow multi-hour legs, not in minute noise.
- Hourly shape: a sharp −1.35% first hour, a flat base around $63.4–64.0k,
  a steady +2.4% climb over hours 05–08 ($63,651 → $65,190), a long
  range $64.1–64.9k, then a slow grind down and a −1.07% final hour.

## Legs (40 bps zigzag)

| Bars | Move | Notes |
| --- | --- | --- |
| 43–69 | −264 bps | first-hour knife, after a +88 bounce |
| 69–85 | +162 bps | fast 16-bar recovery leg |
| 85–133 | −150 bps | gives the leg back |
| 294–409 | +150 bps | slow 115-bar climb |
| 409–441 | −64 bps | mid-rise pullback |
| 441–508 | +160 bps | second half of the big rise |
| 508–678 | −160 bps | long fade off the top |
| 678–705 / 724–816 / 841–889 / 1013–1033 | +60 / +70 / +74 / +67 bps | four small range legs |
| 1033–1439 | −249 bps | 406-bar final grind down |

Up-legs total +991 bps, down-legs −1,259 bps. A long-only bot can only
earn on the up-legs and must sit out the down-legs; buy-and-hold loses
−$31.63 on this window.

## What failed

- **House baselines, all negative**: buy-and-hold −$31.63, momentum
  −$23.87, ema-cross −$148.17 (80 trades — 1-minute EMA crosses
  whipsaw), adx-momentum −$75.57, rsi-bollinger −$39.92.
- **Swing Ladder (previous race's winner design) as-is: −$20.76**, 3
  trades. Its time-based first buy (bar 13) catches the hour-0 knife,
  and its 90 bps take-profit / 110 bps dip re-entry never engages with
  the slow legs.
- **EMA trend grids** (spans 12–30 / 60–120, spread filters, trailing
  stops): all negative or zero trades — the 1-minute noise (sd 6.7 bps)
  against 40–65 bps intra-leg counter-moves makes fast crosses churn.
- **Breakout grids** (new N-bar high + trailing stop): best +$3.91 —
  a slow grind rarely exceeds its running N-bar high by the required
  margin, so entries come late and the trail exits early.

## What works: recovery rider

Buy only after a leg has proved itself — close 70 bps above the
trailing 120-bar low — then hold with a wide 200 bps trailing stop
(survives the 40–65 bps counter-moves inside a leg), a 160 bps
take-profit, a 250 bps hard stop, and a 150 bps cooldown pullback
before any re-entry. Final parameters: N=120, R=70, TRAIL=200,
STOP=250, TP=160, D=150, slip=150, end lock-in after 1,321 closes at
+30 bps.

On the dev window it makes exactly one round trip: buy bar 123
(02:03) at $63,925.58, sell bar 502 (08:22) at $64,801.99 —
**net PnL +$12.898793, 2 trades, fees $0.81, max drawdown 0.81%**.
It skips the hour-0 knife, the leg-1 top, the small range legs, and
the entire final −249 bps grind.

## Robustness (exact replay of the kit's fill model)

| Test | Net PnL |
| --- | --- |
| Dev window | +$12.90 |
| Time-reversed window | +$13.63 (2 round trips) |
| Drifted +75 / −75 / +150 / −150 bps | +$12.68 / +$13.07 / +$13.23 / +$11.86 (mean +$12.71) |
| Drifted ±50 / ±100 / ±200 bps | +$12.8 / +$12.5 / +$13.1 / −$12.4 / +$12.0 / −$10.1 (mean +$4.67) |
| Block-bootstrap reshuffles (60-min blocks, seeds 1–5) | −$17.74 / −$24.65 / −$9.16 / −$16.90 / −$0.74 (mean −$13.84; buy-and-hold: −$29.16 on the same copies) |
| Block-bootstrap reshuffles (seeds 6–10) | mean −$26.58, one copy +$16.8 |

The edge is the slow-leg structure: the bot stays positive on the
reversed window and on moderate drifts, and on reshuffled windows it
loses far less than buy-and-hold because it is out of the market for
most of the down-drift. It is NOT a per-trade edge on random data —
no trend strategy can be, once the multi-hour legs are reshuffled
away — so the race outcome depends on the race window having the same
kind of slow legs. Known weakness: a strong steady down-drift
(−100/−200 bps of drift) can turn the single recovery buy into a
stop-loss hit (−$10 to −$12) — the outcome is threshold-sensitive
around −100 bps of drift, and a −150 bps drift happens to win instead;
a flat, choppy race window may produce zero or one small trade.

## Verification

- Exact simulator of the harness fill model (integer math, copied
  from the kit's `sim/bars/engine.ts`) reproduces the official
  grade-local score for buy-and-hold to the micro-USDC
  (−31.633698 USDC).
- The real `main.py`, driven through the NDJSON protocol
  (hello → 1,440 batches → done) with that simulator, produces the
  identical fills and PnL (+12.898793 USDC).
- Two full protocol runs give byte-identical action logs
  (sha256 `06bf337c88dd6084f67564922ac5d6b2432993998ca40cd522bbbb679c1f3f23`).
