[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Indodegen/cbbtc-race-bot-2/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Indodegen/cbbtc-race-bot-2/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

Built for the [make.fun bounty](https://make.fun/bounty/btc-race-24h-20261118-1444) — Race a BTC trading bot live for 24 hours.

# Recovery Rider — cbBTC 24h race bot

A long-only swing bot for Coinbase Wrapped BTC (cbBTC/USDC) on the
make.fun 24-hour race. It stays flat until the close has recovered
70 bps above the trailing 120-bar low, buys $1,000 of CBBTC in full,
and holds with a wide 200 bps trailing stop below the highest close
since entry, a 250 bps hard stop below the entry close, and a 160 bps
take-profit above the entry close. After an exit it waits in cooldown
until the close has pulled back 150 bps below the exit close before it
may buy again, so it never chases its own exit or re-enters on noise.
After 1,321 closes it locks in any remaining gain of 30 bps or more
instead of gambling the last two hours.

## Why this shape

The dev window is a net-down day (−2.79%, $65,074 → $63,261) whose
money lives in a few slow up-legs of 150–165 bps spread over 16–170
bars, separated by pullbacks of 50–65 bps and two sharp down-legs of
−249/−264 bps. Fast signals drown in the 1-minute noise (standard
deviation 6.7 bps, with 40–65 bps of counter-move inside every
up-leg): the house ema-cross baseline whipsaws into 80 trades and
−$148.17, and the previous race's Swing Ladder design loses −$20.76
here. A recovery trigger 70 bps off the 120-bar low only fires once a
leg is genuinely under way; a 200 bps trailing stop is wide enough to
survive the counter-moves inside a leg; a 160 bps take-profit banks
the leg before it rolls over; and a 150 bps cooldown pullback keeps
the bot out of the chop between legs and out of the long final grind
down.

The same parameters stayed positive on the dev window, its time
reversal (+$13.63), and ±75/±150 bps drifted copies of it (mean
+$12.71), and lost far less than buy-and-hold on block-bootstrapped
reshuffles of it — so the edge is the slow-leg structure, not one
lucky leg. See ANALYSIS.md for the full breakdown.

## Dev-window result (exact local replay of the kit's fill model)

- Net PnL: **+$12.90** (12,898,793 micro-USDC)
- Trades: 2 (1 buy, 1 sell), fees $0.81, max drawdown 0.81%
- The single round trip: buy bar 123 (02:03) at $63,925.58, sell bar
  502 (08:22) at $64,801.99 — it rode the whole 294–508 rise.
- vs baselines on the same window: buy-and-hold −$31.63, momentum
  −$23.87, ema-cross −$148.17, adx-momentum −$75.57, rsi-bollinger
  −$39.92

## Implementation

`main.py` speaks `agent-fun/bars-replay/v1` directly (NDJSON on
stdin/stdout, no SDK shim): one reply per batch, exact integer
arithmetic on closes only — no floats, no wall clock, no environment,
no file reads, no randomness. Two runs on the same data therefore
produce byte-identical action logs. Its whole state is the close
history, the entry close, the peak close, the last exit close, a
cooldown flag and a bar counter.
