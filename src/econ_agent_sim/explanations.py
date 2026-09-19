"""Deterministic explanations of the current forward-looking economy."""

from econ_agent_sim.reporting import build_report

MODEL_PASSPORT = (
    "Two identical households and two identical price-taking firms share one good "
    "and one wage. Households plan consumption, work and money saving over an "
    "infinite horizon. Firms choose investment and owner distributions using their "
    "owners’ valuation of future income. The model uses log consumption, log "
    "leisure and log real money balances, with Cobb–Douglas production. These are "
    "textbook ingredients with explicit financing restrictions: firms pay "
    "dividends and wages before sales, invest their own output and cannot borrow "
    "or resell capital. Total money is fixed at 1; each household owns half of "
    "each firm. Capital and cash carry forward. Prices and choices form a "
    "deterministic perfect-foresight equilibrium: everyone’s forecasts agree with "
    "the solved path. This is not a simulation of learning or proof of "
    "self-regulation. The solver supports zero investment and zero dividends, "
    "but paths requiring firms to retain unspent opening cash are unsupported. "
    "There are no banks, shocks, inventory, unemployment through rationing or "
    "heterogeneity. This is an illustrative teaching model, not a calibrated forecast."
)

QUESTIONS = (
    "What does this model assume?",
    "How do households plan ahead?",
    "How do firms choose investment?",
    "Why can investment or dividends be zero?",
    "How do payments stay funded?",
    "What can a wage buy?",
    "Why did capital change?",
    "Who owns the firms?",
    "Why are profit, cash and capital value different?",
    "How should I read cumulative results?",
    "Why are the households and firms identical?",
    "Does this show a self-regulating economy?",
    "What do the controls mean?",
    "Why can a set of settings be unsupported?",
)


def amount(value: float, places: int = 4) -> str:
    """Keep small nonzero values distinguishable from an economic boundary."""
    if value and (abs(value) < 10 ** -places or abs(value) >= 1e9):
        return f"{value:.3e}"
    return f"{value:,.{places}f}"


def explain(question: str, run, period_number: int, cumulative: bool = False) -> str:
    """Explain actual selected results without external services or invented data."""
    if question not in QUESTIONS:
        raise ValueError("Choose one of the built-in economic questions.")
    report = build_report(run, period_number, cumulative)
    economy, firm, household = report["economy"], report["firms"][0], report["households"][0]
    row = run.periods[period_number - 1]
    settings = run.settings
    answers = {
        QUESTIONS[0]: MODEL_PASSPORT,
        QUESTIONS[1]: (
            "Each household balances consumption and leisure today against future "
            "consumption, leisure and the services of its liquid money. A higher "
            "patience factor gives future utility more weight. Money saving is "
            "the change in household cash; it is not a loan to firms. Owners also "
            "benefit from investment through their fixed ownership claims and "
            "future payouts. "
            f"In {report['label']}, each household consumes {amount(household['consumed_x'])} "
            f"X and its cash changes by {amount(household['net_cash_change'])} Money."
        ),
        QUESTIONS[2]: (
            "A firm chooses how much of its output to retain as capital by comparing "
            "the value of future owner distributions with resources forgone today. "
            "It considers capital wear, future prices, wages and cash funding. "
            "Both households agree on those valuations because they are identical. "
            "There is no separate hurdle-rate control or fixed investment percentage. "
            f"In Period {period_number}, each firm invests {amount(row.investment)} X; "
            f"wear removes {amount(settings.depreciation * row.capital)} capital units. "
            "Installed capital works from the next period."
        ),
        QUESTIONS[3]: (
            "Investment cannot be negative: firms cannot sell their installed capital. "
            "A firm may choose zero investment while existing capital wears down. "
            "Dividends cannot be negative either, so a firm may suspend them while "
            "using cash for wages. These are allowed choices, not automatic failures. "
            f"In Period {period_number}, each firm’s investment is {amount(row.investment)} "
            f"X and dividend is {amount(row.distribution)} Money. Dividends are owner "
            "distributions and need not equal current or previous accounting profit."
        ),
        QUESTIONS[4]: (
            "Each firm first pays dividends from opening cash, then pays wages, "
            "then receives household purchases. Households receive dividends and "
            "wages before buying goods. Each household works half its hours for "
            "each firm, buys half its consumption from each, and receives half "
            "each firm’s dividend. Every payment moves existing money; none creates "
            "a loan or a new deposit. Total cash remains 1 Money. "
            f"In Period {period_number}, each firm opens with {amount(row.firm_cash)}, "
            f"pays {amount(row.distribution)} in dividends and "
            f"{amount(row.money_wage * row.labor)} in wages, then receives "
            f"{amount(row.goods_price * row.consumption)} from sales."
        ),
        QUESTIONS[5]: (
            f"In Period {period_number}, one full household-period of work earns "
            f"{amount(report['wage'])} Money. X costs {amount(report['price'])} Money, "
            f"so that wage buys {amount(report['real_wage'])} X. Actual work is a "
            "fraction of a full period. A nominal wage alone does not describe "
            "purchasing power. Price and wage always describe the selected period, "
            "including in cumulative view."
        ),
        QUESTIONS[6]: (
            f"For each firm in {report['label']}: {amount(firm['capital_open'])} "
            f"opening capital + {amount(firm['investment_quantity'])} investment − "
            f"{amount(firm['depreciation_quantity'])} wear = "
            f"{amount(firm['capital_close'])} closing capital. Wear applies to each "
            "period’s opening stock. Retaining output as investment leaves less "
            "for household consumption today. It transfers no money to another "
            "firm and is distinct from purchasing an existing asset."
        ),
        QUESTIONS[7]: (
            "Each household owns 50% of each firm, throughout the run. Because "
            "there are two identical firms, one household’s combined ownership "
            "claim equals one whole firm’s book equity. "
            f"At the close of Period {period_number}, this is "
            f"{amount(household['ownership_value_close'])} Money per household. "
            "That claim cannot be spent, sold or borrowed against. Whole-economy "
            "assets count cash and physical capital once, eliminating the duplicate "
            "ownership claims. Book equity is not a traded share price or the "
            "solver’s shadow valuation."
        ),
        QUESTIONS[8]: (
            "Operating profit equals the current-price value of all output, "
            "minus wages and capital wear. Output kept as investment is included "
            "in that value but creates no sales receipt. Cash changes with sales, "
            "wages and dividends. Capital is valued at the current goods price; "
            "a price change produces a separate holding gain or loss, never cash "
            "or operating profit. Each firm’s book equity changes by profit minus "
            "dividends plus holding gains. "
            f"For each firm in {report['label']}, profit is "
            f"{amount(firm['net_operating_profit'])} and holding gain is "
            f"{amount(firm['holding_gain'])} Money. Initial opening capital is "
            "valued at the first solved price; later opening values use the "
            "previous period’s price."
        ),
        QUESTIONS[9]: (
            f"You are viewing {report['label']}. Production, consumption, investment, "
            "wear, wages, dividends and profits add the actual flows in the selected "
            "range. Each monetary flow keeps its original period price. Cash and "
            "capital show the first opening and selected closing stock; stocks "
            "are never summed. Household work and leisure are period averages. "
            "Prices and wages belong to the selected closing period. Firm and "
            "household cards are per entity; the economy totals include both. "
            f"Economy consumption in this range is {amount(economy['consumed_x'])} X."
        ),
        QUESTIONS[10]: (
            "This first dynamic model deliberately uses two identical households "
            "and two identical firms. Each entity’s decisions are therefore the "
            "same, while separate accounts show who pays and receives money. "
            "There is one common goods price and wage, no brand preference or "
            "bargaining, and equal fixed ownership. This symmetry also gives the "
            "owners a common valuation of future payouts. It does not model "
            "inequality, business rivalry or different household circumstances."
        ),
        QUESTIONS[11]: (
            "It shows a competitive equilibrium under perfect foresight: choices "
            "are jointly solved so markets clear and expected outcomes match "
            "the resulting path. It does not show prices discovering equilibrium "
            "through trial and error, firms learning, or an economy recovering "
            "from unexpected shocks. Convergence on a displayed path is not proof "
            "of stability under a decentralized adjustment process. Those "
            "mechanisms require separate future modeling choices."
        ),
        QUESTIONS[12]: (
            "Four structural parameters govern behavior: patience weights future "
            "utility, depreciation removes a fraction of opening capital each "
            "period, leisure weight measures its utility relative to consumption, "
            "and money weight measures the service value of real cash balances. "
            "The other two inputs set starting capital per firm and the firms’ "
            "combined share of the fixed 1 Money stock. They are initial conditions, "
            "not ongoing rules. Productivity is fixed at 1 and the production "
            "capital exponent at 0.5. A period has no calibrated calendar length."
        ),
        QUESTIONS[13]: (
            "The current solver checks equilibrium conditions along a long "
            "transition and checks agreement after extending that horizon. It "
            "supports zero investment and zero dividends, but currently requires "
            "each firm’s opening cash to be fully used for dividends and payroll. "
            "If the optimum requires retaining some opening cash, that regime is "
            "explicitly unsupported. Numerical convergence can also fail. Neither "
            "case is reported as an economic collapse or replaced by an invented "
            "path. Change the settings to obtain a supported, verified experiment."
        ),
    }
    return answers[question]
