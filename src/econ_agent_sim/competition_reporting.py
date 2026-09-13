"""Canonical two-firm statements, allocations and full-precision evidence.

The report has plural ``firms`` and ``households`` plus consolidated ``economy``
accounts. Monetary flows retain their original period prices; physical sales
shares divide summed quantities. Prices and funding conditions describe the
selected closing period, even in a cumulative report.
"""

from collections.abc import Sequence
from dataclasses import asdict
from math import fsum

from econ_agent_sim.economy_1_0 import TOLERANCE, Economy10Period

_FIRM_FLOWS = (
    "production_value", "gross_operating_surplus", "net_operating_profit",
    "investment_quantity", "investment_value", "depreciation_quantity",
    "depreciation_value", "holding_gain",
)
_FIRM_STOCKS = (
    "capital", "capital_value", "capital_price", "equity",
    "retained_earnings", "revaluation_reserve",
)


def _close(left: float, right: float, scale: float = 0.0) -> bool:
    return abs(left - right) <= TOLERANCE * max(abs(left), abs(right), abs(scale))


def _selected_periods(periods, cumulative):
    history = (periods,) if isinstance(periods, Economy10Period) else tuple(periods)
    if not history:
        raise ValueError("A report needs at least one completed period.")
    if not all(isinstance(period, Economy10Period) for period in history):
        raise ValueError("Use Economy 1.0 periods for this report.")
    selected = history if cumulative else history[-1:]
    last = selected[-1]
    households = {entry.id: entry for entry in last.households}
    firms = {entry.id: entry for entry in last.firms}
    for index, period in enumerate(selected):
        if (
            {entry.id: entry for entry in period.households} != households
            or {entry.id: entry for entry in period.firms} != firms
            or period.ownership != last.ownership
        ):
            raise ValueError("A cumulative report needs unchanged settings and ownership.")
        if index:
            previous = selected[index - 1]
            if (
                period.number != previous.number + 1
                or period.opening_cash != previous.closing_cash
                or any(
                    period.firm_accounts[key].capital_open
                    != previous.firm_accounts[key].capital_close
                    or period.firm_accounts[key].equity_open
                    != previous.firm_accounts[key].equity_close
                    for key in firms
                )
            ):
                raise ValueError("A cumulative report needs consecutive linked periods.")
    return selected


def competition_report(
    periods: Economy10Period | Sequence[Economy10Period], cumulative: bool = False
) -> dict:
    """Build detached statements for a snapshot or history through a chosen date."""
    selected = _selected_periods(periods, cumulative)
    first, last = selected[0], selected[-1]
    count = len(selected)
    allocation_maps = [
        {(item.household_id, item.firm_id): item for item in period.allocations}
        for period in selected
    ]

    def household_flow(field, identity):
        return fsum(getattr(period, field)[identity] for period in selected)

    def firm_flow(field, identity):
        return fsum(getattr(period.firm_accounts[identity], field) for period in selected)

    def allocation_flow(field, household_id, firm_id):
        return fsum(
            getattr(entries[household_id, firm_id], field)
            for entries in allocation_maps
        )

    household_reports = []
    for household in last.households:
        identity = household.id
        relationships = []
        for firm in last.firms:
            opening = allocation_maps[0][identity, firm.id]
            closing = allocation_maps[-1][identity, firm.id]
            relationships.append({
                "entity_id": firm.id, "name": firm.name,
                "work": allocation_flow("work", identity, firm.id),
                "wages_received": allocation_flow("wages", identity, firm.id),
                "dividends_received": allocation_flow("dividends", identity, firm.id),
                "purchases_paid": allocation_flow("purchases", identity, firm.id),
                "consumed_x": allocation_flow("consumption", identity, firm.id),
                "ownership": closing.ownership_share,
                "ownership_value_open": opening.ownership_value_open,
                "ownership_value_close": closing.ownership_value_close,
            })
        ownership_open = fsum(item["ownership_value_open"] for item in relationships)
        ownership_close = fsum(item["ownership_value_close"] for item in relationships)
        total_work = household_flow("work", identity)
        report = {
            "name": household.name, "entity_id": identity,
            "opening_money": first.opening_cash[identity],
            "closing_money": last.closing_cash[identity],
            "wages_received": household_flow("wages", identity),
            "dividends_received": household_flow("dividends", identity),
            "purchases_paid": household_flow("purchases", identity),
            "net_cash_change": last.closing_cash[identity] - first.opening_cash[identity],
            "consumed_x": household_flow("consumption", identity),
            "consumed": household_flow("consumption", identity),
            "total_work": total_work,
            "average_work": total_work / count,
            "average_leisure": household_flow("leisure", identity) / count,
            # The same fixed share belongs to this household in EACH firm.
            "ownership": relationships[0]["ownership"],
            "ownership_value_open": ownership_open,
            "ownership_value_close": ownership_close,
            "assets_open": first.opening_cash[identity] + ownership_open,
            "assets_close": last.closing_cash[identity] + ownership_close,
            "parameters": {
                "scores": household.scores, "weights": household.weights,
                "alpha": household.alpha,
            },
            "firms": relationships,
        }
        report["income_received"] = report["wages_received"] + report["dividends_received"]
        household_reports.append(report)

    firms = []
    for specification in last.firms:
        identity = specification.id
        opening = first.firm_accounts[identity]
        closing = last.firm_accounts[identity]
        report = {
            "name": specification.name, "entity_id": identity,
            "productivity": specification.productivity, "theta": specification.theta,
            "produced_x": firm_flow("output", identity),
            "sold_x": firm_flow("sales_quantity", identity),
            "work_used": firm_flow("work", identity),
            "total_work": firm_flow("work", identity),
            "opening_money": first.opening_cash[identity],
            "closing_money": last.closing_cash[identity],
            "sales_received": firm_flow("sales_received", identity),
            "wages_paid": firm_flow("wage_bill", identity),
            "dividends_paid": firm_flow("dividends_paid", identity),
            "net_cash_change": last.closing_cash[identity] - first.opening_cash[identity],
            "contributed_equity": closing.contributed_equity,
            "protected_operating_float": specification.money,
            "operating_cash": closing.operating_cash,
            "next_dividend_budget": closing.next_dividend_budget,
            "funding_binding": closing.funding_binding,
            "funding_period": last.number,
            "parameters": asdict(specification),
        }
        for field in _FIRM_STOCKS:
            report[f"{field}_open"] = getattr(opening, f"{field}_open")
            report[f"{field}_close"] = getattr(closing, f"{field}_close")
        for field in _FIRM_FLOWS:
            report[field] = firm_flow(field, identity)
        report["cash_operating_surplus"] = report["sales_received"] - report["wages_paid"]
        report["investment_output_share"] = report["investment_quantity"] / report["produced_x"]
        report["assets_open"] = report["equity_open"]
        report["assets_close"] = report["equity_close"]
        report["allocations"] = []
        for household in household_reports:
            relationship = next(item for item in household["firms"] if item["entity_id"] == identity)
            report["allocations"].append({
                "household_id": household["entity_id"], "name": household["name"],
                "work": relationship["work"],
                "wages_paid": relationship["wages_received"],
                "dividends_paid": relationship["dividends_received"],
                "sold_x": relationship["consumed_x"],
                "sales_received": relationship["purchases_paid"],
                "ownership": relationship["ownership"],
                "ownership_value_open": relationship["ownership_value_open"],
                "ownership_value_close": relationship["ownership_value_close"],
            })
        firms.append(report)

    def total(field):
        return fsum(entry[field] for entry in firms)

    for report in firms:
        report["sales_share"] = report["sold_x"] / total("sold_x")
        report["production_share"] = report["produced_x"] / total("produced_x")
        report["revenue_share"] = report["sales_received"] / total("sales_received")

    economy = {
        "opening_money": fsum(first.opening_cash.values()),
        "closing_money": fsum(last.closing_cash.values()),
        "produced_x": total("produced_x"),
        "consumed_x": fsum(entry["consumed_x"] for entry in household_reports),
        "sales_received": total("sales_received"),
        "output_value": total("production_value"),
        "wages": total("wages_paid"), "dividends": total("dividends_paid"),
        "net_income": total("wages_paid") + total("net_operating_profit"),
        "household_cash_saving": fsum(entry["net_cash_change"] for entry in household_reports),
        "firm_net_saving": total("net_operating_profit") - total("dividends_paid"),
        "total_work": total("work_used"),
        "average_work": fsum(entry["average_work"] for entry in household_reports) / len(household_reports),
        "average_leisure": fsum(entry["average_leisure"] for entry in household_reports) / len(household_reports),
        "household_count": len(household_reports), "firm_count": len(firms),
    }
    for field in (*_FIRM_FLOWS, "capital_open", "capital_close", "capital_value_open", "capital_value_close"):
        economy[field] = total(field)
    economy["assets_open"] = economy["opening_money"] + economy["capital_value_open"]
    economy["assets_close"] = economy["closing_money"] + economy["capital_value_close"]
    checks = _report_checks(selected, household_reports, firms, economy)
    transfers = [asdict(item) for period in selected for item in period.transfers]
    events = [asdict(item) for period in selected for item in period.events]
    rows = _account_rows(selected)
    rows.extend({"record_type": "transfer", **entry} for entry in transfers)
    rows.extend({"record_type": "event", **entry} for entry in events)
    return {
        "model": "competition", "scope": "cumulative" if cumulative else "period",
        "label": f"Periods {first.number}–{last.number}" if count > 1 else f"Period {last.number}",
        "period_count": count, "through_period": last.number,
        "price": last.price, "wage": last.wage, "real_wage": last.wage / last.price,
        "price_wage_period": last.number, "households": household_reports,
        "firms": firms, "economy": economy, "checks": checks,
        "transfers": transfers, "events": events, "rows": rows,
        "policies": {
            "markets": "Both firms take the same goods price and wage. Each funds its own payroll before receiving current sales.",
            "matching": "Work and purchases are allocated proportionally across equal-wage firms selling the same good.",
            "investment": "Each firm's fixed share of output value minus wages, before capital wear, becomes its own capital next period.",
            "dividend": "Each firm separately pays previous-period positive net operating profit, limited to cash above its initial operating float; past retained losses are not a payout gate.",
            "valuation": "Capital uses the current X replacement price; initial capital uses the first solved price. Holding gains remain separate from operating profit.",
            "ownership": "Equal fixed shares in each firm's equity; ownership is not spendable cash. Consolidated assets eliminate both ownership claims.",
            "sales_share": "Share of sales means physical X sold to households, divided by all household X sales in this report range; it is not share of production.",
            "cumulative": "Flows sum at each period's original price. Stocks use first opening and selected closing. Prices and funding conditions describe the selected period; household work and leisure are period averages.",
        },
    }


def _report_checks(periods, households, firms, economy):
    checks = {
        "periods": all(all(period.checks.values()) for period in periods),
        "money": _close(economy["opening_money"], economy["closing_money"]),
        "goods": _close(economy["produced_x"], economy["consumed_x"] + economy["investment_quantity"]),
        "capital": _close(economy["capital_open"] + economy["investment_quantity"], economy["capital_close"] + economy["depreciation_quantity"]),
        "income": _close(economy["production_value"], economy["net_income"] + economy["depreciation_value"]),
        "saving": _close(economy["household_cash_saving"] + economy["firm_net_saving"], economy["investment_value"] - economy["depreciation_value"], economy["production_value"]),
        "household_cash": all(_close(h["opening_money"] + h["income_received"], h["closing_money"] + h["purchases_paid"]) for h in households),
        "firm_cash": all(_close(f["opening_money"] + f["sales_received"], f["closing_money"] + f["wages_paid"] + f["dividends_paid"]) for f in firms),
        "capital_value": all(_close(f["capital_value_open"] + f["investment_value"] + f["holding_gain"], f["capital_value_close"] + f["depreciation_value"], f["capital_value_open"]) for f in firms),
        "equity": all(_close(f["equity_open"] + f["net_operating_profit"] + f["holding_gain"], f["equity_close"] + f["dividends_paid"], f["equity_open"]) for f in firms),
        "equity_components": all(_close(f["contributed_equity"] + f["retained_earnings_close"] + f["revaluation_reserve_close"], f["equity_close"], f["contributed_equity"]) for f in firms),
        "ownership": _close(fsum(h["ownership_value_close"] for h in households), fsum(f["equity_close"] for f in firms)),
    }
    household_fields = ("wages_received", "dividends_received", "purchases_paid", "consumed_x", "ownership_value_open", "ownership_value_close")
    firm_fields = ("wages_paid", "dividends_paid", "sales_received", "sold_x")
    checks["allocations"] = all(
        _close(h[field], fsum(entry[field] for entry in h["firms"]))
        for h in households for field in household_fields
    ) and all(
        _close(f[field], fsum(entry[field] for entry in f["allocations"]))
        for f in firms for field in firm_fields
    ) and all(
        _close(h["total_work"], fsum(entry["work"] for entry in h["firms"]))
        for h in households
    ) and all(
        _close(f["work_used"], fsum(entry["work"] for entry in f["allocations"]))
        for f in firms
    )
    return checks


def _account_rows(periods):
    """Export period stocks and flows without revaluing cumulative evidence."""
    rows = []
    for period in periods:
        common = {
            "record_type": "account", "period": period.number,
            "price": period.price, "wage": period.wage,
            "money_unit": "Money", "goods_unit": "X units",
            "capital_unit": "capital units", "labor_unit": "work periods",
        }
        for household in period.households:
            relationships = [item for item in period.allocations if item.household_id == household.id]
            ownership_open = fsum(item.ownership_value_open for item in relationships)
            ownership_close = fsum(item.ownership_value_close for item in relationships)
            rows.append({
                **common, "account_type": "household", "entity": household.name,
                "entity_id": household.id, "opening_money": period.opening_cash[household.id],
                "closing_money": period.closing_cash[household.id],
                "wages_received": period.wages[household.id],
                "dividends_received": period.dividends[household.id],
                "purchases_paid": period.purchases[household.id],
                "consumed_x": period.consumption[household.id],
                "work_fraction": period.work[household.id],
                "leisure_fraction": period.leisure[household.id],
                "ownership_value_open": ownership_open,
                "ownership_value_close": ownership_close,
                "assets_open": period.opening_cash[household.id] + ownership_open,
                "assets_close": period.closing_cash[household.id] + ownership_close,
                **{f"{key}_priority": value for key, value in household.scores.items()},
                **{f"{key}_weight": value for key, value in household.weights.items()},
            })
        for firm in period.firms:
            account = period.firm_accounts[firm.id]
            rows.append({
                **common, **asdict(account), "account_type": "firm", "entity": firm.name,
                "entity_id": firm.id, "opening_money": account.opening_cash,
                "closing_money": account.closing_cash, "produced_x": account.output,
                "sold_x": account.sales_quantity, "work_used": account.work,
                "wages_paid": account.wage_bill, "protected_operating_float": firm.money,
                "productivity": firm.productivity, "theta": firm.theta,
                "reinvestment_rate": firm.reinvestment_rate,
                "depreciation_rate": firm.depreciation_rate,
            })
        rows.extend({
            **common, "record_type": "allocation", **asdict(item)
        } for item in period.allocations)
    return rows
