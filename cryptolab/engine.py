"""Aggregate spender exposure against balances, flag unrestricted approvals and rank revocation effects."""

from .common import (
    number,
    integer,
    identity,
    records,
    chronology,
    allocate,
    result,
    validate_document,
)
from decimal import Decimal


def _analyze(d):
    balances = {identity(k): integer(v) for k, v in d["balances"].items()}
    seen = set()
    exposure = {}
    lines = []
    for a in records(d["allowances"]):
        token = identity(a["token"])
        spender = identity(a["spender"])
        amount = integer(a["amount"], maximum=2**256 - 1)
        if token not in balances or (token, spender) in seen:
            raise ValueError("unknown token or duplicate allowance")
        seen.add((token, spender))
        at_risk = min(amount, balances[token])
        exposure[spender] = exposure.get(spender, 0) + at_risk
        lines.append(
            {
                "token": token,
                "spender": spender,
                "at_risk": at_risk,
                "unrestricted": amount == 2**256 - 1,
            }
        )
    by_token = {
        t: min(b, sum(a["at_risk"] for a in lines if a["token"] == t))
        for t, b in balances.items()
    }
    return {
        "allowances": lines,
        "spender_ranking": sorted(
            [{"spender": k, "exposure": v} for k, v in exposure.items()],
            key=lambda r: (-r["exposure"], r["spender"]),
        ),
        "capped_token_exposure": by_token,
    }


def analyze(document):
    validate_document(document)
    try:
        return result(_analyze(document))
    except (KeyError, TypeError, ArithmeticError, RecursionError) as error:
        raise ValueError("invalid domain input: " + str(error)) from error
