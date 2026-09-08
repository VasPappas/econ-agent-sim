"""Free explanations based on the same submitted-run data as Results and chat."""


def built_in_explanations(context):
    if context.get("model") == "money_in_utility":
        return money_explanations(context)
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


def money_explanations(context):
    price = context["prices"]["X"]
    previous = context["previous_run"]
    comparison = (f"Compared with Run {previous['number']}, the price changed "
                  f"{context['price_x_change_percent']:+.2f}%. " if previous
                  else "This is your first calculated result. ")
    answers = {
        "Why do agents hold money?": (
            "We explicitly assume agents value both X and their final money balance: "
            "utility is X^α × Money^(1−α). This is money in utility. "
            "There is no future purchase or production in this one-shot model; "
            "the value of holding money is assumed, not derived."
        ),
        "Why did the price move?": (
            f"X clears at {price:.4f} Money per unit. {comparison}"
            "The price depends on starting goods, money and preferences across all agents. "
            "There is no Y in this economy. Changing several inputs at once does not isolate one cause."
        ),
        "What does the preference mean?": (
            "At price p, wealth is p × starting X + starting Money. "
            "An agent wants α of this wealth in the good, and 1−α as money. "
            "This is a share of total wealth, not of initial cash. Net buyers pay from "
            "their starting money; net sellers receive money. No agent can borrow."
        ),
        "Was any money created?": (
            f"Total Money: {context['totals']['opening']['Money']:.4f} → "
            f"{context['totals']['closing']['Money']:.4f}. Payments transfer existing money. "
            "No money is created and no borrowing occurs. Independent runs use the starting balances you choose."
        ),
    }
    if not context["trades"]:
        answers = {"Why is there no trade?": "Each agent already holds their desired combination of X and Money, within numerical tolerance. Two agents with 1 X, 1 Money and equal preferences are such a case at price 1.", **answers}
    if trade := context.get("selected_trade"):
        answers = {"Explain this trade": f"Trade {trade['ordinal']}: {trade['seller']} sells {trade['quantity']:.4f} X to {trade['buyer']} for {trade['payment']:.4f} Money. Price × quantity is the payment. Final balances include all trades, not just this one.", **answers}
    return answers
