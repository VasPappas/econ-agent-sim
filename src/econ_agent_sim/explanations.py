"""Free explanations based on the same submitted-run data as Results and chat."""


def built_in_explanations(context):
    if context.get("model") == "firms_wages":
        return firm_explanations(context)
    if context.get("model") == "work_leisure":
        return work_explanations(context)
    if context.get("model") == "production_consumption":
        return production_explanations(context)
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


def firm_explanations(context):
    """Explain Economy 0.8 from the settled period's own accounts."""
    price = context["prices"]["X"]
    wage = context["wage"]
    output = context["output"]
    profit = context["profit"]
    prior = context.get("previous_run")
    total_dividends = sum(context["dividends"].values())
    total_wages = sum(context["wages"].values())
    firm = context["firm"]
    choices = " ".join(
        f"{household['name']}: work {100 * context['work'][household['name']]:.1f}% "
        f"and leisure {100 * context['leisure_time'][household['name']]:.1f}%."
        for household in context["households"]
    )
    answers = {
        "What happens each period?": (
            "The firm first distributes the previous period's profit to its equal owners. "
            "Households then choose labor, consumption and liquid money while the wage and "
            "goods price clear both markets. The firm pays funded wages, produces X, sells "
            "all of it, and keeps current profit for distribution at the start of the next "
            "period. Goods are consumed; money carries forward."
        ),
        "How were the wage and price found?": (
            f"The wage is {wage:.4f} Money per full unit of work and X costs {price:.4f} "
            f"Money per unit. At those values, households supply exactly the labor the firm "
            f"hires and demand all {output:.4f} X it produces. The firm takes both prices as "
            "given. It hires until value marginal product equals the wage, unless its funded "
            "wage budget binds first."
        ),
        "Why did households work this much?": (
            f"{choices} Each household balances consumption and final purchasing power "
            "against forgone leisure. The three submitted scores are normalized into relative "
            "utility weights; they are not prescribed percentages of time or cash. A household "
            "with sufficient cash can optimally choose no work."
        ),
        "Where did the profit go?": (
            f"This period the firm received {firm['sales_received']:.4f} Money in sales, paid "
            f"{total_wages:.4f} in wages and earned {profit:.4f} in current profit. It remains "
            "in the firm's closing cash and is paid to owners only at the start of the next "
            f"period. Dividends paid now were {total_dividends:.4f}; they came from the prior "
            f"period{'s profit' if prior else '—there was none in Period 1'}."
        ),
        "Was any money created?": (
            f"Total Money is {context['totals']['opening']['Money']:.4f} at opening and "
            f"{context['totals']['closing']['Money']:.4f} at closing. Dividends, wages and "
            "purchases are transfers among households and the firm. Production creates X, "
            "not Money; the firm cannot borrow or overdraw."
        ),
        "Why is there only one firm?": (
            "The displayed firm is a representative price-taking producer—an educational "
            "aggregation, not a strategic monopoly or monopsony. This chapter isolates labor, "
            "wages, production, profit and ownership before adding competing firms, capital, "
            "credit or entry."
        ),
    }
    if transfer := context.get("selected_transfer"):
        answers = {
            "Explain this transfer": (
                f"This {transfer['kind'].replace('_', ' ')} moves "
                f"{transfer['quantity']:.4f} {transfer['asset']} from "
                f"{transfer['sender']} to {transfer['receiver']}. It is one physical ledger "
                "leg; closing accounts include every transfer and the period's consumption."
            ),
            **answers,
        }
    return answers


def production_explanations(context):
    totals = context["period_totals"]
    prior = context["previous_run"]
    comparison = (f"Compared with Period {prior['number']}, the price changed "
                  f"{context['price_x_change_percent']:+.2f}%. " if prior
                  else "This is the first period of this simulation. ")
    answers = {
        "What happens each period?": (
            "Opening balances carry over from the previous period. Agents produce their fixed "
            "quantity of X, trade, then consume all X they hold. Money carries forward; goods "
            "are not stored. Starting X is a one-time stock, not an amount restored each period. "
            "Production is automatic: there is no work decision, wage, input cost or firm yet."
        ),
        "Where did the goods go?": (
            f"{totals['opening']['X']:.4f} opening X + {totals['produced']['X']:.4f} produced "
            f"− {totals['consumed']['X']:.4f} consumed = {totals['closing']['X']:.4f} remaining. "
            "Trading redistributes goods; production adds them and consumption removes them. "
            "Consumed goods provide this period's utility; they have not vanished through an accounting error."
        ),
        "Why did the price move?": (
            f"X clears at {context['prices']['X']:.4f} Money per unit. {comparison}"
            "The price uses available goods after production, carried money and consumption preferences. "
            "These are successive periods under fixed settings, not independent experiments. "
            "Prices can remain steady and trades can fade as balances adjust."
        ),
        "Why keep money instead of consuming more?": (
            "Each period agents maximize consumption^α × final Money^(1−α). They value "
            "money directly; they do not forecast future prices or optimize lifetime consumption. "
            "α is the desired consumption share of total wealth, including the value of goods "
            "available after production—not a fraction of starting cash spent. Money carries "
            "forward, but the preference for holding it remains an explicit assumption."
        ),
        "Was money created?": (
            f"Money: {totals['opening']['Money']:.4f} → {totals['closing']['Money']:.4f}. "
            "Production creates goods, not money. Buyers pay sellers from existing balances. "
            "There is no borrowing, banking, interest or money creation."
        ),
    }
    if not context["trades"]:
        answers = {"Why is there no trade?": (
            "After production, each agent already holds their desired consumption quantity and "
            "money balance at the clearing price. Production and consumption still happen. "
            "In the baseline, each produces and consumes 1 X while retaining 1 Money."
        ), **answers}
    if trade := context.get("selected_trade"):
        answers = {"Explain this trade": (
            f"In {context['label']}, trade {trade['ordinal']}: {trade['seller']} sells "
            f"{trade['quantity']:.4f} X to {trade['buyer']} for {trade['payment']:.4f} Money. "
            "Both agents then consume all their post-trade X. The receipt describes this "
            "exchange only; period closing stocks also include production and consumption."
        ), **answers}
    return answers


def work_explanations(context):
    answers = production_explanations(context)
    answers["What happens each period?"] = (
        "Agents choose work and keep the rest of their time for leisure. Productivity × work "
        "gives their output of X. They trade, consume all post-trade X, and carry money forward. "
        "Starting X is supplied only once. Work and the clearing price are solved together, "
        "not chosen in separate unrelated steps. Agents work for themselves: no employer, "
        "wage or monetary production cost is modeled. Work costs leisure."
    )
    prior = context["previous_run"]
    comparison = (f"Compared with Period {prior['number']}, the price changed "
                  f"{context['price_x_change_percent']:+.2f}%. " if prior
                  else "This is the first period. ")
    answers["Why did the price move?"] = (
        f"X clears at {context['prices']['X']:.4f} Money per unit. {comparison}"
        "The price balances consumption demand with opening goods plus chosen production. "
        "Carried money affects both demand and willingness to work. Productivity and the three "
        "priorities matter too. Higher productivity does not necessarily mean more work: "
        "agents may choose more leisure, and prices also adjust. Successive periods use "
        "the same submitted settings; only carried balances and resulting choices change."
    )
    answers["Why keep money instead of consuming more?"] = (
        "Agents value consumption, real final money (Money divided by the price of X), "
        "and leisure through Cobb–Douglas utility. The three scores are relative: the app "
        "normalizes them into utility weights, so they do not need to total 100. The consume "
        "and money weights divide realized wealth; this is not a share of initial cash spent. "
        "Money is valued directly as an assumption: agents do not forecast prices or optimize "
        "consumption over future periods."
    )
    if not context["trades"]:
        answers["Why is there no trade?"] = (
            "At the clearing price, each agent's opening goods plus chosen output already "
            "match their desired consumption, and their money already matches their desired "
            "holding. No exchange is needed. Work and consumption can still happen. In the "
            "default baseline, each works 50%, produces and consumes 1 X, and keeps 1 Money."
        )
    choices = " ".join(
        f"{agent['name']}: work {100 * context['effort'][agent['name']]:.1f}%, "
        f"leisure {100 * context['leisure_time'][agent['name']]:.1f}%, "
        f"output {context['produced'][agent['name']]:.4f} X."
        for agent in context["agents"]
    )
    return {"Why did agents choose this much work?": (
        f"{choices} Each agent balances the benefit of more goods and money against "
        "giving up leisure, taking the market price as given. An agent with enough existing "
        "resources can optimally choose no work. The leisure priority becomes a utility weight, "
        "not the fraction of time spent resting. Equal priority scores give each objective a "
        "one-third weight; with productivity 2, the baseline then yields 50% work."
    ), **answers}


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
