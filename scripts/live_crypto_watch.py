"""Watch live crypto prices and the order book in the terminal (PROP-010 phase 5).

Coinbase's public WebSocket: no key, no account. Display only.

    uv run python scripts/live_crypto_watch.py                 # BTC-USD for 20 seconds
    uv run python scripts/live_crypto_watch.py ETH-USD --seconds 60
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys
import time

from quant_brain.market.live_crypto import stream


async def watch(products: list[str], seconds: float) -> None:
    end = time.monotonic() + seconds
    last_print = 0.0
    events = stream(products)
    async with contextlib.aclosing(events):
        async for event in events:
            kind = event["type"]
            if kind == "status":
                print(f"[{event['state'].upper()}] {event['detail']}")
            elif kind == "book" and time.monotonic() - last_print >= 1:
                last_print = time.monotonic()
                print(f"{event['product']}  bid {event['best_bid']:,.2f}  ask {event['best_ask']:,.2f}  "
                      f"mid {event['mid']:,.2f}  spread {event['spread']:.2f} ({event['spread_bps']:.3f} bps)")
            elif kind == "candle":
                print(f"1-min bar {event['product']}: O {event['open']:,.2f} H {event['high']:,.2f} "
                      f"L {event['low']:,.2f} C {event['close']:,.2f} vol {event['volume']:.4f}")
            if time.monotonic() >= end:
                return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("products", nargs="*", default=["BTC-USD"])
    parser.add_argument("--seconds", type=float, default=20)
    args = parser.parse_args()
    asyncio.run(watch(args.products, args.seconds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
