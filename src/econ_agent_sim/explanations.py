"""Deterministic explanations derived from the selected model result, without AI."""


def built_in_explanations(result, selected_index, trade_index=None):
    period = result.periods[selected_index]
    previous = result.periods[selected_index - 1] if selected_index else None
    price = period.prices['X']
    prices = (
        f"X clears at {price:.4f} Money per unit. Y is the reference good: "
        "its price is fixed at 1. This does not mean demand for Y is unchanged. "
    )
    if previous:
        old = previous.prices['X']
        change = 100 * (price / old - 1)
        direction = 'rose' if change > 0.0001 else 'fell' if change < -0.0001 else 'was unchanged'
        prices += f"Compared with the previous experiment, X's price {direction} ({change:+.2f}%). "
        prior = {a.name: a for a in previous.population}
        weighted_change = sum(a.alpha * (a.y - prior[a.name].y) for a in period.population)
        if abs(weighted_change) > 1e-9:
            prices += (
                "The redistribution shifted Y toward agents allocating a "
                + ('larger' if weighted_change > 0 else 'smaller')
                + " share of goods wealth to X. With total goods unchanged, "
                "that changes aggregate demand and the clearing price."
            )
        else:
            prices += "This redistribution did not change preference-weighted Y holdings."
    else:
        prices += "This is the baseline; no redistribution has been applied yet."
    total = sum(s['Money'] for s in period.opening_stocks.values())
    money = (
        f"The economy starts and finishes with {total:.4f} Money in total. "
        "Each payment moves existing money from buyer to seller; none is created. "
        "Money does not enter goods demand or limit purchases in this model. "
        "Prices are determined before settlement, and each experiment starts with fresh opening money."
    )
    answers = {"Why did X change but not Y?": prices, "Was any money created?": money}
    if trade_index is not None and 0 <= trade_index < len(period.trades):
        t = period.trades[trade_index]
        answers = {
            "Explain this trade": (
                f"In trade {trade_index + 1} of {len(period.trades)}, {t.seller} sells "
                f"{t.quantity:.4f} {t.good} to {t.buyer}. In return, {t.buyer} pays "
                f"{t.payment:.4f} Money to {t.seller}. The unit price is {t.unit_price:.4f}. "
                "Quantity × unit price gives the payment, allowing for rounding. "
                "These are the two legs of this trade only. Closing balances include all trades."
            ), **answers,
        }
    return answers
