"""Money serialisation (R-05).

R-05: "Money is `Decimal` / `NUMERIC(14,2)`, serialised as string. Never
`float`." A float cannot represent 0.10 exactly, so the API must not emit
one. Amounts stay `Decimal` in the database and in the service layer, and
are rendered as fixed 2-decimal strings on the way out.

The `Money` alias is used on response models. `when_used="json"` keeps the
value a `Decimal` for any Python-side consumer while the wire format is a
string, and `return_type=str` makes the generated OpenAPI schema say
`string` so the frontend types follow.
"""
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def format_money(value: Decimal) -> str:
    """Render an exact decimal amount as a fixed 2-decimal string."""
    return f"{value:.2f}"


Money = Annotated[
    Decimal,
    PlainSerializer(format_money, return_type=str, when_used="json"),
]
