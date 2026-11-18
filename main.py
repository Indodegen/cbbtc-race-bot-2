# SPDX-License-Identifier: MIT
"""Recovery rider bot for the make.fun BTC race (agent-fun/bars-replay/v1).

Strategy in one paragraph: wait for the market to prove a leg is under
way, then ride it. The bot stays flat until the close has recovered
70 bps above the trailing 120-bar low, buys $1,000 of CBBTC in full,
and holds with a wide 200 bps trailing stop below the highest close
since entry, a 250 bps hard stop below the entry close, and a 160 bps
take-profit above the entry close. After an exit it waits in cooldown
until the close has pulled back 150 bps below the exit close before it
may buy again, so it never chases its own exit or re-enters on noise.
After 1,321 closes it locks in any remaining gain of 30 bps or more
instead of gambling the last two hours. All decisions use exact integer
arithmetic on closes only; no float, no clock, no environment, no file
reads, no randomness, so two runs on the same data produce byte-identical
action logs.

Why this shape: the dev window is a net-down day (-2.79%, $65,074 to
$63,261) whose money lives in a few slow up-legs of 150-165 bps spread
over 16-170 bars, separated by pullbacks of 50-65 bps and two sharp
down-legs of -249/-264 bps. Fast signals drown in the 1-minute noise
(standard deviation 6.7 bps, legs of 40-65 bps of counter-move inside
every up-leg): the house ema-cross baseline whipsaws into 80 trades
and -$148.17. A recovery trigger 70 bps off the 120-bar low only fires
once a leg is genuinely under way; a 200 bps trailing stop is wide
enough to survive the counter-moves inside a leg; a 160 bps
take-profit banks the leg before it rolls over; and a 150 bps
cooldown pullback keeps the bot out of the chop between legs and out
of the long final grind down. The same parameters stayed positive on
the dev window, its time reversal, and +/-75 and +/-150 bps drifted
copies of it, and lost far less than buy-and-hold on block-bootstrapped
reshuffles of it -- so the edge is the slow-leg structure, not one
lucky leg.
"""

import json
import sys

PROTOCOL = "agent-fun/bars-replay/v1"
SYMBOL = "CBBTC"

# --- strategy parameters (all in basis points, 1 bp = 0.01%) ---
LOOKBACK = 120            # trailing low is the min close of the last N closes
RECOVERY_BPS = 70         # buy when close is this far above the trailing low
SIZE_QUOTE_UNITS = 1_000_000_000   # $1,000 per leg (micro-USDC)
TAKE_PROFIT_BPS = 160     # sell when close is this far above the entry close
TRAIL_BPS = 200           # sell when close is this far below the peak close
STOP_BPS = 250            # sell when close is this far below the entry close
COOLDOWN_BPS = 150        # after an exit, wait for a pullback this far below it
END_CLOSES = 1321         # late lock-in: from this many closes on...
END_TAKE_PROFIT_BPS = 30  # ...sell a leg already this far above its entry close
MAX_SLIPPAGE_BPS = 150    # fill guard vs the latest close (1-min moves stay well under this)
MIN_NOTIONAL = 1_000_000   # $1 (from hello.fees, kept as a floor, never binding here)


def _buy(client_id, notional):
    return {
        "side": "buy",
        "client_id": client_id,
        "symbol": SYMBOL,
        "notional_quote_units": str(notional),
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


def _sell(client_id, qty):
    return {
        "side": "sell",
        "client_id": client_id,
        "symbol": SYMBOL,
        "qty": str(qty),
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


class Bot:
    """One position at a time; every threshold is an exact integer comparison."""

    def __init__(self):
        self.closes = []          # every CBBTC close seen, in order
        self.bars_seen = 0
        self.entry = None         # close at which the current leg was decided
        self.peak = None          # highest close since the current leg began
        self.last_exit = None     # close at which the last sell was decided
        self.cooldown = False     # waiting for a pullback below the last exit
        self.pending_buy = False  # a buy was decided on the previous batch
        self.pending_sell = False  # a sell was decided on the previous batch
        self.next_id = 1

    def _client_id(self):
        cid = "o%d" % self.next_id
        self.next_id += 1
        return cid

    def on_batch(self, batch):
        # Latest CBBTC close of this batch (a batch with no CBBTC bar: no signal).
        close = None
        for bar in batch.get("bars") or []:
            if bar.get("symbol") == SYMBOL and bar.get("c") is not None:
                close = int(bar["c"])
        account = batch.get("account") or {}
        cash = int(account.get("cash_quote_units") or 0)
        qty = 0
        for pos in account.get("positions") or []:
            if pos.get("symbol") == SYMBOL:
                qty = int(pos.get("qty") or 0)
        if close is None:
            return []

        self.closes.append(close)
        self.bars_seen += 1

        # Resolve the buy decided on the previous batch: it filled at this
        # bar's open iff the account now holds a position.
        if self.pending_buy:
            self.pending_buy = False
            if qty == 0:
                # Rejected (e.g. max slippage): forget the leg, retry the entry.
                self.entry = None
                self.peak = None
            # else: filled; entry/peak already hold the decision close.

        # Resolve the sell decided on the previous batch: it filled at this
        # bar's open iff the account no longer holds the position.
        if self.pending_sell:
            self.pending_sell = False
            if qty > 0:
                # Rejected (e.g. max slippage): keep holding on the same
                # entry/peak; the exit levels are simply re-checked below.
                self.last_exit = None
            else:
                # Filled: the leg is closed; entry/peak are cleared below.
                self.entry = None
                self.peak = None

        if qty > 0:
            # Holding: track the peak and check the exit levels.
            if self.entry is None:
                self.entry = close
                self.peak = close
            if close > self.peak:
                self.peak = close
            exit_now = False
            if close * 10000 >= self.entry * (10000 + TAKE_PROFIT_BPS):
                exit_now = True
            elif close * 10000 <= self.peak * (10000 - TRAIL_BPS):
                exit_now = True
            elif close * 10000 <= self.entry * (10000 - STOP_BPS):
                exit_now = True
            elif (
                self.bars_seen >= END_CLOSES
                and close * 10000 >= self.entry * (10000 + END_TAKE_PROFIT_BPS)
            ):
                exit_now = True
            if exit_now:
                self.last_exit = close
                self.cooldown = True
                self.pending_sell = True
                return [_sell(self._client_id(), qty)]
            return []

        # Flat: nothing pending, so any earlier leg is fully closed.
        self.entry = None
        self.peak = None
        if self.cooldown:
            # Wait for a real pullback below the last exit before re-entering.
            if self.last_exit is not None and close * 10000 <= self.last_exit * (
                10000 - COOLDOWN_BPS
            ):
                self.cooldown = False
            else:
                return []
        if len(self.closes) > LOOKBACK:
            low = min(self.closes[-LOOKBACK - 1 : -1])
            if (
                close * 10000 >= low * (10000 + RECOVERY_BPS)
                and cash >= MIN_NOTIONAL
            ):
                self.entry = close
                self.peak = close
                self.pending_buy = True
                return [_buy(self._client_id(), min(SIZE_QUOTE_UNITS, cash))]
        return []


def main():
    bot = Bot()
    out = sys.stdout
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        kind = msg.get("type")
        if kind == "hello":
            if msg.get("protocol") != PROTOCOL:
                raise ValueError("unexpected protocol: %r" % (msg.get("protocol"),))
            continue
        if kind == "batch":
            orders = bot.on_batch(msg)
            out.write(
                json.dumps(
                    {"type": "reply", "seq": msg["seq"], "orders": orders},
                    separators=(",", ":"),
                )
                + "\n"
            )
            out.flush()
        elif kind == "done":
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
