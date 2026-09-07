"""Free explanations based on the same submitted-run data as Results and chat."""


def built_in_explanations(context):
    price = context["prices"]["X"]
    previous = context["previous_run"]
    prices = (
        f"X clears at {price:.4f} Money per unit. Y is the reference good: "
        "its price is fixed at 1. This does not mean demand for Y is unchanged. "
    )
    if previous:
        change = context["price_x_change_percent"]
        direction = "rose" if change > .0001 else "fell" if change < -.0001 else "was unchanged"
        prices += (
            f"Compared with Run {previous['number']}, X's price {direction} ({change:+.2f}%). "
            f"The previous price was {previous['prices']['X']:.4f}. "
        )
    else:
        prices += "This is your first run; there is no previous result to compare. "
    prices += (
        "The clearing price depends on starting goods and spending preferences across all agents. "
        "Changing quantities, preferences, or population can change demand and supply. "
        "When several inputs change, the comparison alone does not isolate one cause."
    )
    total = context["totals"]["opening"]["Money"]
    final = context["totals"]["closing"]["Money"]
    money = (
        f"The economy starts with {total:.4f} Money and finishes with {final:.4f} Money in total. "
        "Each payment moves existing money from buyer to seller; none is created. "
        "Money does not enter goods demand or limit purchases in this model. "
        "Prices are determined before settlement, and each run starts with fresh opening money."
    )
    answers = {"Why did the price move?": prices, "Was any money created?": money}
    if not context["trades"]:
        answers = {"Why is there no trade?": (
            "At the clearing prices, each agent already holds their desired bundle, "
            "within the model's numerical tolerance. No exchange is needed. "
            "Two agents with 1 X, 1 Y and equal spending preferences are such a case at equal prices."
        ), **answers}
    trade = context.get("selected_trade")
    if trade is not None:
        answers = {"Explain this trade": (
            f"In trade {trade['ordinal']} of {len(context['trades'])}, {trade['seller']} sells "
            f"{trade['quantity']:.4f} {trade['good']} to {trade['buyer']}. In return, "
            f"{trade['buyer']} pays {trade['payment']:.4f} Money to {trade['seller']}. "
            f"The unit price is {trade['unit_price']:.4f}. "
            "Quantity × unit price gives the payment, allowing for rounding. "
            "These are the two legs of this trade only. Closing balances include all trades."
        ), **answers}
    return answers
