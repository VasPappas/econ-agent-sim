"""Free explanations and compact, authoritative context for the two-firm model."""

from dataclasses import asdict

from econ_agent_sim.investment_explanations import amount


def competition_explanations(period, report: dict) -> dict[str, str]:
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
        "Why does splitting the default firm change nothing overall?": (
            "The two default firms each receive half the old firm's money and "
            "capital, with identical productivity and policies. Their production "
            "technology has constant returns when capital and work scale together. "
            "The combined default path therefore matches the one-firm economy. "
            "The old firm already took price and wage as given, so splitting it "
            "does not remove a monopoly markup. Change one firm's productivity "
            "or policy to explore differences between firms."
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
            "wage. Ownership value cannot be spent and does not enter that choice."
        ),
    }


def _table(records: list[dict]) -> dict:
    """Preserve every field while avoiding repeated keys in the AI allowance."""
    columns = sorted({key for record in records for key in record})
    return {"columns": columns, "values": [
        [record.get(column) for column in columns] for record in records
    ]}


def competition_context(period, report: dict, run_id, *, comparison=None) -> dict:
    compact = {
        key: value for key, value in report.items()
        if key not in {"rows", "transfers", "events", "households", "firms"}
    }
    compact["firms"] = [
        {key: value for key, value in firm.items() if key != "allocations"}
        for firm in report["firms"]
    ]
    compact["households"] = _table([
        {key: value for key, value in household.items()
         if key not in {"firms", "parameters"}}
        for household in report["households"]
    ])
    compact["household_parameters"] = _table([
        {"entity_id": household["entity_id"],
         "alpha": household["parameters"]["alpha"],
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
        "model": "competition", "label": report["label"],
        "revision": str(run_id), "report": compact,
        "firm_settings": [asdict(firm) for firm in period.firms],
        "selected_period": {
            "number": period.number, "price": period.price, "wage": period.wage,
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
    if comparison is not None:
        context["baseline_comparison"] = {
            key: value for key, value in comparison.items()
            if key != "settings_changes"
        }
        grouped = {}
        named_entities = {
            item["entity_id"]: item["name"]
            for item in [*report["households"], *report["firms"]]
        }
        for change in comparison["settings_changes"]:
            group = grouped.setdefault(change["entity_id"], {
                "entity_id": change["entity_id"],
                **({"entity": change["entity"]}
                   if named_entities.get(change["entity_id"]) != change["entity"]
                   else {}),
                "changes": [],
            })
            group["changes"].append({
                key: value for key, value in change.items()
                if key not in {"entity_id", "entity"}
            })
        context["baseline_comparison"]["changed_settings"] = [
            {**group, "changes": _table(group["changes"])}
            for group in grouped.values()
        ]
    return context
