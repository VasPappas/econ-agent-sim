"""Dated book accounts for the current symmetric monetary economy.

The solver's records are per household / per firm. Reports make the two copies
explicit and consolidate only once. Capital is valued at the goods replacement
price; its revaluation is separate from operating profit and never creates cash.
"""

import csv
import io
from math import fsum, isclose

from econ_agent_sim.domain import MODEL_ID
from econ_agent_sim.engine import Run

_FIRM_FLOWS = (
    "produced_x", "sold_x", "work_used", "sales_received", "wages_paid",
    "dividends_paid", "production_value", "investment_quantity", "investment_value",
    "depreciation_quantity", "depreciation_value", "net_operating_profit", "holding_gain",
)


def _selected(run, period_number, cumulative):
    if not isinstance(run, Run) or not run.solution.converged:
        raise ValueError("Reports need a successfully solved current-model run.")
    if type(period_number) is not int or not 1 <= period_number <= len(run.periods):
        raise ValueError("Choose a completed positive whole period for this run.")
    if type(cumulative) is not bool:
        raise ValueError("Cumulative must be true or false.")
    return run.periods[:period_number] if cumulative else run.periods[period_number - 1:period_number]


def _firm_period(run, period):
    previous_price = (
        run.periods[period.number - 2].goods_price
        if period.number > 1 else period.goods_price
    )
    price = period.goods_price
    wear = run.settings.depreciation * period.capital
    wages = period.money_wage * period.labor
    return {
        "opening_money": period.firm_cash,
        "closing_money": period.next_firm_cash,
        "capital_open": period.capital,
        "capital_close": period.next_capital,
        "capital_price_open": previous_price,
        "capital_price_close": price,
        "capital_value_open": previous_price * period.capital,
        "capital_value_close": price * period.next_capital,
        "equity_open": period.firm_cash + previous_price * period.capital,
        "equity_close": period.next_firm_cash + price * period.next_capital,
        "produced_x": period.output,
        "sold_x": period.consumption,
        "work_used": period.labor,
        "sales_received": price * period.consumption,
        "wages_paid": wages,
        "dividends_paid": period.distribution,
        "production_value": price * period.output,
        "investment_quantity": period.investment,
        "investment_value": price * period.investment,
        "depreciation_quantity": wear,
        "depreciation_value": price * wear,
        "net_operating_profit": fsum((price * period.output, -wages, -price * wear)),
        "holding_gain": (price - previous_price) * period.capital,
    }


def _close(left, right):
    return isclose(left, right, rel_tol=1e-8, abs_tol=1e-10)


def build_report(run: Run, period_number: int, cumulative: bool = False) -> dict:
    """Report dated flows, first opening stocks and selected closing stocks.

    Prices/wages are always those of ``period_number``. In cumulative view,
    money flows retain their original prices; work and leisure are averages.
    Solver shadow values are not used to value book equity.
    """
    selected = _selected(run, period_number, cumulative)
    first, last = selected[0], selected[-1]
    count = len(selected)
    firm_periods = [_firm_period(run, row) for row in selected]
    opening, closing = firm_periods[0], firm_periods[-1]
    firm = {field: fsum(row[field] for row in firm_periods) for field in _FIRM_FLOWS}
    for stem in ("capital", "capital_price", "capital_value", "equity"):
        firm[f"{stem}_open"] = opening[f"{stem}_open"]
        firm[f"{stem}_close"] = closing[f"{stem}_close"]
    firm.update(
        opening_money=first.firm_cash,
        closing_money=last.next_firm_cash,
        net_cash_change=last.next_firm_cash - first.firm_cash,
        assets_open=opening["equity_open"], assets_close=closing["equity_close"],
        sales_share=.5, production_share=.5,
        average_work=firm["work_used"] / count,
        zero_investment_periods=sum(row.investment == 0 for row in selected),
        zero_dividend_periods=sum(row.distribution == 0 for row in selected),
        funding_period=last.number,
        opening_funding_slack=fsum((last.firm_cash, -last.distribution,
                                   -last.money_wage * last.labor)),
    )
    firm["cash_operating_surplus"] = firm["sales_received"] - firm["wages_paid"]
    firms = [dict(firm, entity_id=f"firm_{letter.lower()}", name=f"Firm {letter}")
             for letter in ("A", "B")]
    household = {
        "opening_money": first.household_cash,
        "closing_money": last.next_household_cash,
        "net_cash_change": last.next_household_cash - first.household_cash,
        "wages_received": firm["wages_paid"],
        "dividends_received": firm["dividends_paid"],
        "purchases_paid": firm["sales_received"],
        "consumed_x": fsum(row.consumption for row in selected),
        "total_work": firm["work_used"],
        "average_work": firm["work_used"] / count,
        "average_leisure": fsum(1 - row.labor for row in selected) / count,
        "ownership": .5,
        # Each household owns half of BOTH identical firms.
        "ownership_value_open": firm["equity_open"],
        "ownership_value_close": firm["equity_close"],
        "assets_open": first.household_cash + firm["equity_open"],
        "assets_close": last.next_household_cash + firm["equity_close"],
    }
    household["income_received"] = household["wages_received"] + household["dividends_received"]
    households = [dict(household, entity_id=f"household_{number}", name=f"Household {number}")
                  for number in (1, 2)]
    economy = {field: 2 * firm[field] for field in _FIRM_FLOWS}
    for field in ("capital_open", "capital_close", "capital_value_open", "capital_value_close"):
        economy[field] = 2 * firm[field]
    economy.update(
        opening_money=2 * (first.household_cash + first.firm_cash),
        closing_money=2 * (last.next_household_cash + last.next_firm_cash),
        consumed_x=2 * household["consumed_x"],
        total_work=2 * household["total_work"],
        average_work=household["average_work"], average_leisure=household["average_leisure"],
        household_cash_open=2 * first.household_cash,
        household_cash_close=2 * last.next_household_cash,
        firm_cash_open=2 * first.firm_cash,
        firm_cash_close=2 * last.next_firm_cash,
        household_cash_saving=2 * household["net_cash_change"],
        firm_net_saving=2 * (firm["net_operating_profit"] - firm["dividends_paid"]),
        household_count=2, firm_count=2,
    )
    economy["net_income"] = economy["wages_paid"] + economy["net_operating_profit"]
    economy["assets_open"] = economy["opening_money"] + economy["capital_value_open"]
    economy["assets_close"] = economy["closing_money"] + economy["capital_value_close"]
    checks = {
        "money": _close(economy["opening_money"], 1.) and _close(economy["closing_money"], 1.),
        "goods": _close(economy["produced_x"], economy["consumed_x"] + economy["investment_quantity"]),
        "capital": _close(firm["capital_open"] + firm["investment_quantity"],
                          firm["capital_close"] + firm["depreciation_quantity"]),
        "household_cash": _close(household["opening_money"] + household["income_received"],
                                 household["closing_money"] + household["purchases_paid"]),
        "firm_cash": _close(firm["opening_money"] + firm["sales_received"],
                            firm["closing_money"] + firm["wages_paid"] + firm["dividends_paid"]),
        "capital_value": _close(firm["capital_value_open"] + firm["investment_value"] + firm["holding_gain"],
                                firm["capital_value_close"] + firm["depreciation_value"]),
        "equity": _close(firm["equity_open"] + firm["net_operating_profit"] + firm["holding_gain"],
                         firm["equity_close"] + firm["dividends_paid"]),
        "income": _close(economy["production_value"], economy["net_income"] + economy["depreciation_value"]),
        "saving": _close(economy["household_cash_saving"] + economy["firm_net_saving"],
                         economy["investment_value"] - economy["depreciation_value"]),
        "ownership": _close(fsum(h["ownership_value_close"] for h in households),
                            fsum(f["equity_close"] for f in firms)),
        "consolidation": _close(fsum(h["assets_close"] for h in households), economy["assets_close"]),
    }
    report = {
        "model": MODEL_ID, "scope": "cumulative" if cumulative else "period",
        "label": f"Periods 1–{last.number}" if cumulative and count > 1 else f"Period {last.number}",
        "period_count": count, "through_period": last.number,
        "price": last.goods_price, "wage": last.money_wage,
        "real_wage": last.money_wage / last.goods_price,
        "price_wage_period": last.number,
        "households": households, "firms": firms, "economy": economy, "checks": checks,
    }
    report["rows"] = _account_rows(report)
    return report


def _account_rows(report):
    common = {
        "model": report["model"], "period": report["through_period"],
        "scope": report["scope"], "price": report["price"], "wage": report["wage"],
        "money_unit": "Money", "goods_unit": "X", "work_unit": "household-periods",
    }
    return [
        *[{**common, "account_type": "household", **entry} for entry in report["households"]],
        *[{**common, "account_type": "firm", **entry} for entry in report["firms"]],
        {**common, "account_type": "economy", "entity_id": "economy", "name": "Economy",
         **report["economy"]},
    ]


def export_csv(run: Run, period_count: int) -> str:
    """Export every visible period, with float round-trip precision and units."""
    _selected(run, period_count, False)
    rows = [entry for number in range(1, period_count + 1)
            for entry in build_report(run, number)["rows"]]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
