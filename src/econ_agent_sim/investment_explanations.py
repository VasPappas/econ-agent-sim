"""Scope-aware, free explanations for the investment economy."""

from dataclasses import asdict


def amount(value: float, places: int = 4) -> str:
    """Show meaningful small values without rounding them to a false zero."""
    if value == 0:
        return f"{0:.{places}f}"
    if abs(value) < 10 ** -places or abs(value) >= 1e9:
        return f"{value:.3e}"
    return f"{value:,.{places}f}"


def investment_explanations(period, report: dict) -> dict[str, str]:
    firm = report["firm"]
    economy = report["economy"]
    settings = period.firm
    scope = report["label"]
    added = firm["investment_quantity"]
    wear = firm["depreciation_quantity"]
    difference = firm["capital_close"] - firm["capital_open"]
    maintained = abs(difference) <= 1e-9 * max(
        firm["capital_open"], firm["capital_close"]
    )
    direction = "held steady" if maintained else "grew" if difference > 0 else "fell"
    rate = 100 * settings.reinvestment_rate
    return {
        "Where does new capital come from?": (
            f"In {scope}, the firm produced {amount(economy['produced_x'])} X. "
            f"Households consumed {amount(economy['consumed_x'])} X and the firm "
            f"installed {amount(added)} X as new capital. One X becomes one capital "
            "unit. Installation uses real production; it is not a payment or a "
            "transfer of money to another firm. New capital starts producing in "
            "the following period."
        ),
        "What does reinvesting surplus mean?": (
            f"Your setting is {rate:g}%. Surplus means the value of everything "
            "produced minus wages, before capital wear. The firm keeps that "
            "percentage of surplus value as new capital and sells the remaining "
            "goods to households. It is not the percentage of all output, or of "
            "net profit, that is invested. When payroll funding does not limit "
            f"hiring, this setting allocates {rate * (1-settings.theta):g}% of "
            "output to capital. A funding constraint can change that output share."
        ),
        "Why did capital change?": (
            f"Capital {direction}: {amount(firm['capital_open'])} at the start "
            f"to {amount(firm['capital_close'])} at the end of {scope}. "
            f"The firm added {amount(added)} units while {amount(wear)} units wore "
            "out. Capital grows only when additions exceed wear. Each period's "
            "wear applies to its opening capital; newly installed capital is "
            "available next period. Reinvestment and wear percentages have "
            "different bases, so setting them equal does not keep capital constant."
        ),
        "Why are profit, cash and dividends different?": (
            f"For {scope}, cash sales were {amount(firm['sales_received'])} Money "
            f"and wages cost {amount(firm['wages_paid'])}. Output value also "
            f"includes {amount(firm['investment_value'])} of new capital kept by "
            f"the firm. After {amount(firm['depreciation_value'])} of capital wear, "
            f"net operating profit was {amount(firm['net_operating_profit'])}. "
            "Capital additions and wear are not cash payments. At the start of "
            "the next period, dividends are limited to the preceding period's "
            "positive net profit and cash above the initial operating float. "
            f"After Period {period.number}, the next dividend budget is "
            f"{amount(period.next_dividend_budget)} Money. This is one future "
            "payment budget, never a cumulative total. Past losses remain in "
            "retained earnings but do not block a later funded profit dividend."
        ),
        "Why can more capital be worth less?": (
            "Capital units measure productive equipment. Capital value measures "
            "those units at the current price of X. More units can therefore have "
            "a lower money value if the price falls enough. We show this price "
            "effect separately as a holding gain or loss; it is not operating "
            "profit or cash. Opening capital in Period 1 is valued at that "
            "period's first solved price, with no initial holding gain. Household "
            "ownership values are claims on the same firm assets, so they are "
            "not counted again in the whole economy."
        ),
        "What can a wage buy?": (
            f"In Period {period.number}, one full unit of work earns "
            f"{amount(period.wage)} Money and one X costs {amount(period.price)}. "
            f"The real wage is therefore {amount(period.wage / period.price)} X "
            "per full unit of work. A constant money wage can buy more when X "
            "becomes cheaper. These are the selected period's prices, including "
            "when you view cumulative results; prices and wage rates are never "
            "added across periods. More capital does not guarantee more work, "
            "a higher money wage, or an improvement for every household."
        ),
        "Is more investment always better?": (
            "Investment uses goods that could be consumed today. It can increase "
            "future capacity, but extra capital brings diminishing returns and "
            "more capital wear. A higher reinvestment rate can even reduce "
            "long-run consumption. Try separate runs at 70% and 90% with the "
            "other baseline settings unchanged. Compare consumption as well as "
            "production and capital. The rate is your policy choice; the model "
            "does not calculate an optimal lifetime saving plan."
        ),
        "How do household priorities work?": (
            "Consume, Keep money and Leisure are relative importance scores. "
            "For example, 2 : 1 : 1 means consumption has twice the weight of "
            "either other goal. Multiplying all three scores by the same number "
            "changes nothing. These are utility weights, not fixed percentages "
            "of work time or starting cash. Each household chooses its work, "
            "consumption and closing cash at the current wage and price. Firm "
            "ownership value cannot be spent and does not enter this choice."
        ),
    }


def investment_context(period, report: dict, run_id, *, comparison=None) -> dict:
    """Use the same report as Results without duplicating the unbounded ledger."""
    context = {
        "model": "investment_growth",
        "label": report["label"],
        "revision": str(run_id),
        "report": {
            key: value for key, value in report.items()
            if key not in {"rows", "transfers", "events"}
        },
        "selected_period": {
            "number": period.number,
            "price": period.price,
            "wage": period.wage,
            "next_dividend_budget": period.next_dividend_budget,
        },
        "firm_settings": asdict(period.firm),
        "selected_transfer": None,
        "scope_rule": (
            "Report flows cover its labeled scope at each period's own price. "
            "Stocks use first opening and last closing; wage and price refer "
            "only to the selected period. The next dividend is a future budget."
        ),
    }
    if comparison is not None:
        context["baseline_comparison"] = {
            key: value for key, value in comparison.items()
            if key != "settings_changes"
        }
        # Compact rows retain every changed setting within the shared AI budget.
        context["baseline_comparison"]["changed_setting_columns"] = [
            "entity", "setting", "baseline", "current", "unit",
        ]
        context["baseline_comparison"]["changed_settings"] = [
            [entry[key] for key in ("entity", "label", "baseline", "current", "unit")]
            for entry in comparison["settings_changes"]
        ]
    return context
