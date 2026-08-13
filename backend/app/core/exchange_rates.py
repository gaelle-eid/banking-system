"""Live exchange rates for multi-currency accounts.

Uses open.er-api.com (free, no API key required). Rates are cached in
memory and refreshed periodically, since the upstream API only updates
once a day and we don't want a network round-trip on every transfer.

Note: for LBP specifically, this reflects the OFFICIAL/central-bank peg,
not Lebanon's real-world parallel-market rate - worth knowing if this is
ever compared against real numbers, but fine for the app's purposes.
"""
import time
from decimal import Decimal, ROUND_HALF_UP

import httpx

from app.models.models import CurrencyCode

RATES_URL = "https://open.er-api.com/v6/latest/USD"
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours - upstream data only updates daily anyway

_cache: dict = {"rates": None, "fetched_at": 0}


async def _get_usd_rates() -> dict:
    """Return a dict of {currency_code: rate_relative_to_usd}, using the
    cache if it's fresh. Falls back to a stale cache (rather than failing
    outright) if the upstream API is unreachable."""
    now = time.time()
    if _cache["rates"] and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["rates"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(RATES_URL)
            response.raise_for_status()
            data = response.json()
            if data.get("result") != "success":
                raise ValueError(f"Exchange rate API returned an error: {data}")
            _cache["rates"] = data["rates"]
            _cache["fetched_at"] = now
            return _cache["rates"]
    except Exception:
        if _cache["rates"]:
            # Stale data is better than no data for a demo/non-critical path.
            return _cache["rates"]
        raise


async def get_supported_rates() -> dict[str, Decimal]:
    """Return current USD-based rates for just the currencies this app
    supports, as Decimals."""
    rates = await _get_usd_rates()
    return {
        code.value: Decimal(str(rates[code.value]))
        for code in CurrencyCode
        if code.value in rates
    }


async def get_rate(from_currency: str, to_currency: str) -> Decimal:
    """Get the exchange rate to convert 1 unit of from_currency into
    to_currency."""
    if from_currency == to_currency:
        return Decimal("1")

    rates = await _get_usd_rates()
    if from_currency not in rates or to_currency not in rates:
        raise ValueError(f"Unsupported currency pair: {from_currency} -> {to_currency}")

    # rates are USD-based, so pivot through USD: amount_in_usd = amount / rate[from]
    # then amount_in_to = amount_in_usd * rate[to]
    from_rate = Decimal(str(rates[from_currency]))
    to_rate = Decimal(str(rates[to_currency]))
    return to_rate / from_rate


async def convert(amount: Decimal, from_currency: str, to_currency: str) -> tuple[Decimal, Decimal]:
    """Convert an amount between currencies. Returns (converted_amount, rate_used),
    both rounded sensibly - 2 decimal places for the amount, since that's
    what the ledger stores."""
    rate = await get_rate(from_currency, to_currency)
    converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return converted, rate