"""Explanations of flexible targets, separate from subsistence guarantees."""

from econ_agent_sim.competition_explanations import (
    _table,
    amount,
    competition_context,
    competition_explanations,
)


def target_explanations(period, report):
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
        "How are shortfalls counted?": (
            f"In {report['label']}, household targets add to "
            f"{amount(economy['needed_x'])} X and shortfalls add to "
            f"{amount(economy['shortfall_x'])} X. Each household's shortfall is "
            "the positive gap between its target and actual consumption in that "
            "period. Extra consumption by another household, or in a later "
            "period, never cancels that gap. Cumulative shortfalls are a record, "
            "not a debt and not extra demand carried into the next period."
        ),
        "Does the target change my preference weights?": (
            "Your Consume, Keep money and Leisure scores stay fixed. They "
            "describe the underlying trade-offs. A separate smooth preference "
            "term adds urgency only while consumption is below the target. "
            "The displayed percentages are not spending or time allocations. "
            "Multiplying all three scores by the same number changes nothing."
        ),
    }
    inherited = competition_explanations(period, report)
    inherited.pop("Why does splitting the default firm change nothing overall?", None)
    inherited["How do household priorities work?"] = answers[
        "Does the target change my preference weights?"
    ]
    inherited["How should I read cumulative results?"] += (
        " Consumption targets and shortfalls are counted separately for every "
        "household and period. They are physical X quantities, not money flows."
    )
    answers.update(inherited)
    answers["Why did setting a target change nothing?"] = (
        "If the ordinary choice already reaches the target, no extra urgency "
        "is needed and the result is unchanged. The default 0.50 X target is "
        "below default first-period consumption. Try raising one target to "
        "1.00 X and compare with a saved baseline. A target of zero reproduces "
        "Economy 1.0's household behavior."
    )
    return answers


def target_context(period, report, run_id, *, comparison=None):
    context = competition_context(period, report, run_id, comparison=comparison)
    context["model"] = "consumption_target"
    parameters = context["report"]["household_parameters"]
    parameters["columns"].append("consumption_target")
    for values, household in zip(parameters["values"], report["households"]):
        values.append(household["parameters"]["consumption_target"])
    context["report"]["firms"] = _table(context["report"]["firms"])
    if comparison is not None:
        baseline = context["baseline_comparison"]
        baseline["metrics"] = _table(baseline.get("metrics", []))
        baseline["firms"] = [
            {**firm, "metrics": _table(firm.get("metrics", []))}
            for firm in baseline.get("firms", [])
        ]
        # Describe each setting once, preserving every changed value at full
        # precision even with twenty households and long household names.
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
    context["target_rule"] = (
        "Economy 1.1 uses a flexible current-period target, not Stone–Geary "
        "or a guarantee. With normalized a,d,g, utility is a*log(C)+d*log(M)"
        "+g*log(leisure). Below target b>0 it additionally subtracts "
        "C/b-1-log(C/b); above b or when b=0 this term is absent. "
        "Strength is fixed at 1. Targets never alter balances directly. "
        "Shortfalls sum max(b-C,0) per household-period without offsets. "
        "Cumulative shortfalls do not change future preferences."
    )
    return context
