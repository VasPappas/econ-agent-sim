"""Reproduce the design's three feasible-plan examples; not an optimizer.

No app/engine imports or external dependencies. All prices and wages equal one,
so cash and dividends below are also real units of X. Each candidate uses funded
static hiring for three periods, then the shared no-investment continuation.
"""

from math import fsum, sqrt

BETA = 0.95
DEPRECIATION = 0.10
HORIZON = 3
TAIL_TOLERANCE = 1e-10


def step(capital, cash, productivity, protected, policy):
    labor = min(productivity**2 * capital / 4, cash)
    output = productivity * sqrt(capital * labor)
    gross_surplus = output - labor
    if policy == "zero":
        investment = 0.0
    elif policy == "replace":
        investment = min(DEPRECIATION * capital, output)
    elif policy == "surplus":
        investment = max(0.0, gross_surplus)
    else:
        raise ValueError(f"Unknown illustrative plan: {policy}")
    closing_cash = cash - labor + output - investment
    profit = gross_surplus - DEPRECIATION * capital
    dividend = min(max(profit, 0.0), max(closing_cash - protected, 0.0))
    next_capital = (1 - DEPRECIATION) * capital + investment
    next_cash = closing_cash - dividend
    return next_capital, next_cash, dividend, {
        "labor": labor, "output": output, "investment": investment,
        "next_capital": next_capital, "closing_cash": closing_cash,
        "next_dividend": dividend,
    }


def value(productivity, opening_cash, policy):
    capital, cash = 10.0, opening_cash
    discounted_dividends = []
    first_decision = None
    gamma = productivity**2 / 4
    for period in range(10_000):
        if period >= HORIZON:
            remaining_bound = (
                BETA ** (period + 1) * gamma * capital
                / (1 - BETA * (1 - DEPRECIATION))
            )
            if remaining_bound <= TAIL_TOLERANCE:
                return fsum(discounted_dividends), first_decision, remaining_bound
        capital, cash, dividend, decision = step(
            capital, cash, productivity, opening_cash,
            policy if period < HORIZON else "zero",
        )
        if first_decision is None:
            first_decision = decision
        discounted_dividends.append(BETA ** (period + 1) * dividend)
    raise ArithmeticError("Illustrative dividend tail did not meet its error bound.")


def main():
    for label, productivity, cash in (
        ("Cash-poor firm", 1.0, 0.1),
        ("Replacement case", 0.7, 10.0),
        ("Expansion case", 1.2, 1.0),
    ):
        candidates = {
            policy: value(productivity, cash, policy)
            for policy in ("zero", "replace", "surplus")
        }
        winner = max(candidates, key=lambda policy: candidates[policy][0])
        scores = ", ".join(
            f"{policy}={result[0]:.6f}" for policy, result in candidates.items()
        )
        print(f"{label}: {scores}; best illustrated plan={winner}")
        print("  First decision: " + ", ".join(
            f"{key}={number:.6f}" for key, number in candidates[winner][1].items()
        ))
        print(f"  Maximum omitted-tail bound: {max(r[2] for r in candidates.values()):.3g}")


if __name__ == "__main__":
    main()
