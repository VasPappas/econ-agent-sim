"""Current-model explanations and compact, authoritative AI context."""

from dataclasses import asdict

MODEL_PASSPORT = (
    "Households choose consumption, closing money and leisure for the current "
    "period. They do not forecast or optimize lifetime utility. Relative "
    "preference scores form Cobb–Douglas-style log utility, with a custom smooth "
    "urgency term below an optional consumption target. Two price-taking firms "
    "share one goods price and one wage. Markets clear each period; firm payroll "
    "must be funded from cash before current sales. Reinvestment is a selected "
    "share of output value minus wages, before wear; it is not an optimized "
    "lifetime investment plan. New capital works next period. Dividends pay "
    "preceding-period positive net profit only when cash exceeds the firm's "
    "initial operating float. Household ownership shares are equal and fixed. "
    "Money and capital carry forward. There is no borrowing, money creation, "
    "unemployment from rationing or unsold inventory. These textbook building "
    "blocks and explicit custom rules make a teaching model, not a forecast."
)


def amount(value: float, places: int = 4) -> str:
    """Show meaningful small values without rounding them to a false zero."""
    if value == 0:
        return f"{0:.{places}f}"
    if abs(value) < 10 ** -places or abs(value) >= 1e9:
        return f"{value:.3e}"
    return f"{value:,.{places}f}"


def _market_explanations(period, report: dict) -> dict[str, str]:
    scope = report["label"]
    firms = report["firms"]
    economy = report["economy"]
    sales = "; ".join(
        f"{firm['name']} produced {amount(firm['produced_x'])} X, sold "
        f"{amount(firm['sold_x'])} X and supplied {firm['sales_share']:.1%} of sales"
        for firm in firms
    )
    constrained = [
        account.name for account in period.firm_accounts.values()
        if account.funding_binding
    ]
    funding = (
        f"In Period {period.number}, available cash limits hiring at "
        f"{', '.join(constrained)}. "
        if constrained else
        f"In Period {period.number}, cash does not restrict either firm's desired hiring. "
    )
    dividends = "; ".join(
        f"{account.name}: {amount(account.next_dividend_budget)} Money"
        for account in period.firm_accounts.values()
    )
    capital = "; ".join(
        f"{firm['name']}: {amount(firm['capital_open'])} opening capital + "
        f"{amount(firm['investment_quantity'])} added − "
        f"{amount(firm['depreciation_quantity'])} worn out = "
        f"{amount(firm['capital_close'])} closing capital"
        for firm in firms
    )
    return {
        "Why do both firms pay the same wage?": (
            f"In Period {period.number}, the common wage is {amount(period.wage)} "
            f"Money per work unit and X costs {amount(period.price)} Money. "
            "Both firms hire the same kind of labor and sell the same good. "
            "Households have no preference for a particular employer or seller. "
            "The model finds a wage and price that clear both markets together; "
            "each firm takes them as given when choosing how much work to hire. "
            "It does not model wage bargaining or rival firms setting prices. "
            "A work unit is one household working for a full period."
        ),
        "Why does one firm sell more?": (
            f"For {scope}: {sales}. Productivity, opening capital and available "
            "payroll cash affect how much each firm produces. Its reinvestment "
            "policy affects how much is left to sell. Households divide their "
            "purchases in proportion to each firm's goods available for sale. "
            "This is an allocation rule for identical goods, not brand loyalty. "
            "A larger sales share alone does not establish better household welfare."
        ),
        "Why are production and sales shares different?": (
            "Produced X includes goods the firm keeps as its own new capital. "
            "Sold X includes only household purchases. Share of sales means "
            "the firm's sold X divided by all firms' sold X. For example, equally "
            "productive and capitalized firms satisfying the unconstrained hiring "
            "condition can produce equal output but sell 40% and 60% of household "
            "purchases when their reinvestment policies are 80% and 20%. "
            "In cumulative reports, shares divide summed physical sales; they "
            "are not averages of period percentages or shares of cumulative Money receipts."
        ),
        "Why might a more productive firm not hire more?": (
            funding + "Every firm must pay wages from its own cash after dividends, "
            "before receiving this period's sales. It cannot borrow or use the "
            "other firm's money. Productivity also changes the common market "
            "price and households' work choices, so more productivity does not "
            "guarantee more work or a higher nominal wage. A binding funding limit "
            "can stop hiring while an extra unit of labor would still be profitable."
        ),
        "What can a wage buy?": (
            f"In Period {period.number}, one work unit earns {amount(period.wage)} "
            f"Money. At {amount(period.price)} Money per X, that buys "
            f"{amount(period.wage / period.price)} X. A falling Money wage can "
            "still buy more if the price of X falls faster. These are the selected "
            "period's rates, even in cumulative view; prices and wages are never "
            "added across periods. Household outcomes also depend on work, "
            "leisure, ownership income and their own priorities."
        ),
        "Where does new capital come from?": (
            f"In {scope}, firms produced {amount(economy['produced_x'])} X. "
            f"Households consumed {amount(economy['consumed_x'])} X and firms "
            f"installed {amount(economy['investment_quantity'])} X as capital. "
            "Each firm retains some of its own output; it does not pay itself "
            "or buy capital from the other firm. Reinvestment is a share of "
            "output value minus wages, before capital wear. It is not a share of "
            "all output or net profit. New capital becomes productive next period."
        ),
        "Why did capital change?": (
            f"For {scope}: {capital}. Capital grows when additions exceed wear. "
            "Wear applies to each period's opening capital. Reinvestment and wear "
            "percentages use different bases, so equal percentages do not keep "
            "capital constant. A higher reinvestment policy keeps more goods from "
            "current consumption and does not guarantee higher long-run consumption."
        ),
        "Who receives each firm's dividends?": (
            f"Each of the {len(period.households)} households owns an equal share "
            "of each firm. Every firm decides its dividend separately: it is "
            "limited to the preceding period's positive net profit and cash above "
            "that firm's original operating float. A loss at one firm does not "
            "block the other firm's eligible dividend. Past retained losses "
            "remain recorded but do not veto a later funded profit dividend. "
            f"After Period {period.number}, the next dividend budgets are "
            f"{dividends}. These are future budgets, not cumulative payments. "
            "First-period dividends are zero."
        ),
        "Why are profit, cash and capital value different?": (
            "Cash sales minus wages is cash operating surplus. Profit also "
            "includes the value of output retained as new capital and deducts "
            "capital wear. These capital flows are not Money payments. Capital "
            "is valued at the current price of X; a price change creates a "
            "separate holding gain or loss, not operating profit or spendable "
            "cash. Ownership values are claims on those same firm assets, so "
            "the whole-economy accounts eliminate them rather than counting them twice."
        ),
        "How should I read cumulative results?": (
            f"You are viewing {scope}. Cumulative production, consumption, wages, "
            "profit and dividends add the actual flows from the included periods. "
            "Money flows retain each period's original prices. Cash and capital "
            "show the first opening and selected closing stocks. Firm work is "
            "summed in work-periods; household work and leisure percentages are "
            "averages. Price, wage, hiring limits and next dividend budgets refer "
            "only to the selected period."
        ),
        "How do household priorities work?": (
            "Consume, Keep money and Leisure are relative importance scores. "
            "For example, 2 : 1 : 1 gives consumption twice the weight of either "
            "other goal. Multiplying all three scores by the same number changes "
            "nothing. They are not fixed spending or time percentages. Households "
            "choose consumption, work and closing Money at the current price and "
            "wage. A stronger consumption preference can also induce more work. "
            "Scores stay fixed; a separate smooth term adds urgency only below "
            "the consumption target. Ownership value is not spendable cash."
        ),
    }



def built_in_explanations(period, report):
    economy = report["economy"]
    answers = {
        "How does my consumption target work?": (
            "The target is an amount of X per household per period. Below it, "
            "an extra unit of consumption becomes more valuable as the gap grows. "
            "The household chooses work, consumption and closing money together; "
            "money and leisure still matter. At or above the target, the extra "
            "urgency disappears. A target of zero switches this feature off. "
            "This is a flexible target, not a guaranteed minimum or Stone–Geary utility."
        ),
        "Why can a household fall below its target?": (
            "A target changes preferences; it does not create goods or income. "
            "Prices, wages, available capital, firm funding and the household's "
            "priorities still determine consumption. A household may choose "
            "some money and leisure while consuming below its target. "
            "Accounting checks can all pass even when targets are not met."
        ),
        "How are target gaps counted?": (
            f"In {report['label']}, household targets add to "
            f"{amount(economy['needed_x'])} X and target gaps add to "
            f"{amount(economy['shortfall_x'])} X. Each household's target gap is "
            "the positive gap between its target and actual consumption in that "
            "period. Extra consumption by another household, or in a later "
            "period, never cancels that gap. Cumulative target gaps are a record, "
            "not a debt and not extra demand carried into the next period."
        ),
    }
    market_answers = _market_explanations(period, report)
    market_answers["How should I read cumulative results?"] += (
        " Consumption targets and target gaps are counted separately for every "
        "household and period. They are physical X quantities, not money flows."
    )
    answers.update(market_answers)
    answers["What does this model assume?"] = MODEL_PASSPORT
    candidates = period.solution.get("candidate_count", 1)
    reference = (
        "the previous period's price" if period.number > 1
        else "the clearing price for the same economy with consumption targets off"
    )
    answers["Can there be more than one clearing price?"] = (
        f"For Period {period.number}, the search found {candidates} candidate "
        "clearing price(s). Strongly different household preferences and targets "
        "can allow several prices to satisfy the model's market conditions. "
        f"The run selects the candidate closest in proportional terms to {reference}. "
        "A numerical tie selects the lower price. This is an explicit selection "
        "convention, not a proof of economic stability. The search samples a "
        "range of prices and can miss additional roots; finding one candidate "
        "does not establish uniqueness. With all targets off, the model uses "
        "its analytical target-free solution."
    )
    answers["Why did setting a target change nothing?"] = (
        "If the ordinary choice already reaches the target, no extra urgency "
        "is needed and the result is unchanged. The default 0.50 X target is "
        "below default first-period consumption. Try raising one target to "
        "1.00 X and compare with a saved baseline. A target of zero reproduces "
        "ordinary consumption–money–leisure preferences."
    )
    return answers



def _table(records: list[dict]) -> dict:
    """Preserve every field while avoiding repeated keys in the AI allowance."""
    columns = sorted({key for record in records for key in record})
    return {"columns": columns, "values": [
        [record.get(column) for column in columns] for record in records
    ]}



def build_context(period, report: dict, run_id, *, comparison=None) -> dict:
    compact = {
        key: value for key, value in report.items()
        if key not in {"rows", "transfers", "events", "households", "firms"}
    }
    compact["firms"] = _table([
        {key: value for key, value in firm.items() if key != "allocations"}
        for firm in report["firms"]
    ])
    compact["households"] = _table([
        {key: value for key, value in household.items()
         if key not in {"firms", "parameters"}}
        for household in report["households"]
    ])
    compact["household_parameters"] = _table([
        {"entity_id": household["entity_id"],
         "alpha": household["parameters"]["alpha"],
         "consumption_target": household["parameters"]["consumption_target"],
         **{f"{key}_score": value
            for key, value in household["parameters"]["scores"].items()},
         **{f"{key}_weight": value
            for key, value in household["parameters"]["weights"].items()}}
        for household in report["households"]
    ])
    # Keep one complete copy of bilateral results, instead of repeating it in
    # every firm and household. These are exactly the selected report's values.
    compact["household_firm_allocations"] = _table([
        {**{key: value for key, value in allocation.items() if key != "name"},
         "firm_id": firm["entity_id"]}
        for firm in report["firms"] for allocation in firm["allocations"]
    ])
    context = {
        "model": "tiny_economy", "label": report["label"],
        "revision": str(run_id), "report": compact,
        "firm_settings": [asdict(firm) for firm in period.firms],
        "selected_period": {
            "number": period.number, "price": period.price, "wage": period.wage,
            "market_selection": {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in period.solution.items()
                if key in {"candidate_count", "candidate_prices", "selected_candidate",
                           "selection_rule", "reference_price", "root_search_complete"}
            },
            "firm_next_dividend_budgets": {
                key: account.next_dividend_budget
                for key, account in period.firm_accounts.items()
            },
        },
        "selected_transfer": None,
        "scope_rule": (
            "Report flows use original period prices. Stocks use first opening "
            "and selected closing. Price, wage, cash constraints and next dividend "
            "budgets refer to the selected period. Tables use columns and values; "
            "each value row follows the column order. Allocation household_id "
            "refers to the named household record. Sales shares use physical X."
        ),
    }
    context["target_rule"] = (
        "Flexible current-period target, not Stone–Geary or a guarantee. "
        "With normalized a,d,g, utility is a*log(C)+d*log(M)+g*log(leisure). "
        "Below target b>0 it additionally subtracts C/b-1-log(C/b); at or above "
        "b or when b=0 this term is absent. Strength is fixed at 1. Targets do not "
        "alter balances directly. Target gaps sum max(b-C,0) per household-period "
        "without offsets and do not change future preferences."
    )
    if comparison is not None:
        baseline = {
            key: value for key, value in comparison.items()
            if key not in {"settings_changes", "metrics", "firms"}
        }
        baseline["metrics"] = _table(comparison.get("metrics", []))
        baseline["firms"] = [
            {**firm, "metrics": _table(firm.get("metrics", []))}
            for firm in comparison.get("firms", [])
        ]
        # Describe each setting once; retain all values at full precision.
        fields = list(dict.fromkeys(
            (change["label"], change["unit"])
            for change in comparison["settings_changes"]
        ))
        baseline["setting_fields"] = [
            {"id": index, "label": label, "unit": unit}
            for index, (label, unit) in enumerate(fields)
        ]
        baseline["changed_settings"] = _table([
            {"entity_id": change["entity_id"],
             "field_id": fields.index((change["label"], change["unit"])),
             "baseline": change["baseline"], "current": change["current"]}
            for change in comparison["settings_changes"]
        ])
        context["baseline_comparison"] = baseline
    return context
