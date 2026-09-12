# Economy 0.9 — Investment and Growth

Status: implemented, 12 September 2026. The user also authorized
major UI adjustments that improve usability on small phone screens. The model
and accounting rules below remain the implementation contract; Economy 0.8
stays independently available.

Design baseline: Economy 0.8 at GitHub main commit
`19e53b053e382a50f4ad9bb0c8bde6bc02beff52`. This document is the synthesis of
separate economics, accounting, mobile UX, and independent verification reviews.

## 1. Product decision

Keep the familiar households, one representative firm, one good, and money.
Add productive capital that persists, wears out, and can be replenished by using
some current production for investment. The central experiment is the trade-off
between current consumption and future productive capacity.

The important refinement to the original roadmap is that **retaining cash is
not itself investment**. The firm must actually produce and install something.
Use one dual-purpose good X: households consume it, or the firm installs it as
capital. One X becomes one capital unit, available from the next period.

The new policy control is **Reinvest surplus (%)**, not “Invest output (%)” or
“Reinvest net profit (%)”. It sets the fraction of production value left after
wages, BEFORE capital wear, used to make new capital. Actual dividends are
separately limited by net operating profit and available cash.

Do not represent the story as “net profit = investment + dividends”. That would
confuse physical investment, depreciation, noncash income, and dividend timing.

## 2. Scope and deliberate limitations

Preserve from 0.8:

- Household current-period Cobb–Douglas preferences over consumption, real
  closing money, and leisure, entered as three positive relative scores.
- Endogenous labor, goods price, and wage; price-taking representative firm.
- Equal fixed household ownership, linked periods, and explicit funded payments.
- One fixed total quantity of settlement money, with no borrowing or creation.
- Set up / Results / Ask why / Reset, period selection, cumulative accounts,
  full-precision CSV, and explanations based on the submitted run.

Add capital, own-account investment, physical depreciation, and economic
capital/equity accounts. Capital is owned by the firm, not rented from households.
The operating surplus therefore includes the return to owned capital; it is not
pure economic profit after paying a capital rental charge. A funding constraint
can also create a financing-scarcity return.

Do not add a capital-goods supplier, bank, loans, interest, share market,
government, shocks, technological change, population growth, inventories for
resale, capital resale/scrapping markets, or intertemporal utility optimization.
Households consume every unit of X they buy. The firm carries productive capital,
not unsold X. No household goods stock persists.

The reinvestment rate is an owner policy chosen by the user and fixed within a
run. It is not a discovered optimal saving rate. Labor is optimized conditional
on that policy. This is a monetary educational model with growth-model building
blocks, not a full Solow, Ramsey, or business-accounting implementation.

## 3. Settings and notation

| Setting | Default | Proposed control |
| --- | ---: | --- |
| Households | 2 | Existing count control |
| Initial household money | 1 each | Existing +/- input |
| Consume / keep money / leisure scores | 1 : 1 : 1 | Existing relative scores, step 0.10 |
| Initial firm operating money, B0 | 1 | Existing +/- input |
| Initial productive capital, K1 | 1 | +/- input, step 0.10 |
| Productivity, A | 2 | Existing +/- input |
| Reinvestment rate, r | 40% | Percentage +/- input, step 10 percentage points |
| Capital wear, delta | 10% | Percentage +/- input, step 5 percentage points |
| Labor exponent, theta | 0.5 | Fixed, explained in Ask why |

Engine domain: positive finite A, K1, B0 and priority scores; nonnegative
household money with positive aggregate household cash; `0 <= r < 1` and
`0 <= delta < 1`. Initial release controls offer r and delta from 0% to 90%.
These conservative UI bounds are not a proof of safe infinite-horizon numerical
behavior. Reject nonfinite values and unsupported endpoints explicitly.

For this chapter, use `Q = A * K^(1-theta) * L^theta`. Equivalently the textbook
notation is `Q = A * K^alpha * L^(1-alpha)`, with alpha = 1-theta. The default
capital and labor exponents are both 0.5. Productivity 2 means output 2 with
ONE capital unit and ONE full unit of total labor, not with arbitrary inputs.

Initial capital is a real endowment, not bought with imaginary startup cash.
Initial money totals include household and firm money. Capital units must not
be added to Money as if they were the same unit.

## 4. The period sequence

Opening money and capital are exactly the preceding closing stocks. The first
period instead uses the submitted endowments and has no prior profit dividend.

1. Compute and pay the cash-limited dividend based on the previous period.
2. Jointly solve wage, household labor, consumption, output, investment, and price.
3. Pay wages from actual post-dividend firm money, without an overdraft.
4. Households supply the agreed labor; the firm produces using OPENING capital.
5. Households pay for and receive their X; the firm sets aside the remaining X.
6. Households consume their purchases. Opening capital loses delta of its units;
   the set-aside output becomes new capital for the next period.
7. Close cash, physical capital, income, equity, and the informational next
   dividend budget. Append only a fully validated period snapshot.

The market solution is simultaneous. This order describes settlement and stock
timing, not a sequence of guessed prices or retrospective behavior changes.
Investment has no current-period production effect and no immediate depreciation.
Compute and validate before committing; a failure must leave history unchanged.

## 5. Households

Normalize each household's scores into a_i, b_i, g_i, which sum to one. Let
eta_i = a_i/(a_i+b_i), h_i be opening money, d_i its dividend, and z_i=h_i+d_i.

At p>0 and w>0, maximize

`U_i = c_i^a_i * (m_i/p)^b_i * (1-l_i)^g_i`

subject to `p*c_i + m_i = z_i + w*l_i`, `0 <= l_i < 1`.

The 0.8 solution remains:

`l_i = max(0, (1-g_i) - g_i*z_i/w)`

`c_i = eta_i * (z_i+w*l_i)/p`

`m_i = (1-eta_i) * (z_i+w*l_i)`.

Ownership value is not spendable in this budget and is not another component
of current utility. Households do not anticipate future dividends. A household
may choose no work while consuming from cash and dividends.

## 6. Investment and the firm's operating choice

Define total output value V=pQ, wage bill W=wL, and gross operating surplus
G=V-W. The owner's policy is

`I = r*G/p`.

The firm installs I physical units of its own production. It sells the remainder
to households; C=Q-I and cash sales S=pC. Consequently,

`S = (1-r)*V + r*W`

`S-W = (1-r)*G`.

For fixed r<1 and given prices, maximizing current cash surplus subject to the
investment policy is equivalent to maximizing pQ-wL. This gives a clear static
objective; no forecast, discount factor, future asset-price solution, or claimed
lifetime optimum is needed. Only profitable operating choices are used, so
investment is nonnegative and consumption remains positive.

Let B_t be actual firm cash after dividends. The firm faces `wL <= B_t`.
At its solution,

`W = min(theta*V, B_t)`.

When funding does not bind, the value of marginal product equals the wage.
When it binds, the value of marginal product can exceed the wage. Do not label
the latter an unconstrained optimum. At fixed opening K, depreciation is
independent of the labor choice and does not alter this hiring condition.

The realized investment share of OUTPUT is `I/Q = r*(1-W/V)`, not r. It equals
`r*(1-theta)` only when funding is unconstrained. This distinction is mandatory
in the UI, tutor, report, and acceptance tests.

## 7. A unique scalar equilibrium, not a new multidimensional optimizer

Using the household equations, define

`W_i(w) = max(0, (1-g_i)*w - g_i*z_i)`

`W(w) = sum_i W_i(w)`

`S(w) = sum_i eta_i*(z_i+W_i(w))`

`kappa = theta / (1-r*(1-theta))`.

Since theta<1 and r<1, kappa<1. Solve the single positive wage equation

`W(w) = min(kappa*S(w), B_t)`.

Recover

`L = W/w`, `Q = A*K^(1-theta)*L^theta`

`V = (S-r*W)/(1-r)`, `p = V/Q`

`G = V-W`, `I = r*G/p`, `C = S/p`.

Both goods and labor markets then clear. The scalar reduction follows by
substituting the cash-sales identity into the firm's first-order condition or
funding cap. It is our derivation for this monetary model, not a textbook wage
rule. On any active-set interval, W-kappa*S has positive slope equal to a sum
of `(1-kappa*eta_i)*(1-g_i)` over working households. W-B_t increases once
work starts. With positive aggregate z, the combined residual starts negative
and eventually turns positive, yielding a unique positive root.

Normalize monetary quantities in the solve by Z=sum(z_i); solve for w/Z.
Bracket dynamically, set convergence tolerances relative to economically
relevant scales, and verify the recovered conditions independently. A fixed
absolute wage tolerance can fail after severe losses move most cash to the firm.
Do not round prices, balances, or quantities to display precision internally.

## 8. Depreciation, net profit, and funded dividends

Physical capital obeys

`K_next = (1-delta)*K + I`.

Current-price capital wear is Dep=p*delta*K. Net operating profit is

`N = V-W-Dep = G-Dep`.

It can be negative even when cash sales exceed wages. Wear reduces real assets
but is not a payment to anyone. The recommended dividend policy is

`D_t = min(max(N_previous, 0), max(F_open-B0, 0))`, with D1=0.

Each household receives D_t/n. Afterward `B_t=F_open-D_t` drives wage funding.
B0 is the original protected OPERATING FLOAT when making dividends; it is not
a minimum balance at every moment, a money injection, or an automatic reset.
The firm may spend that cash on funded wages before sales replenish it.
Post-dividend operating cash and closing cash may exceed B0 over time.

Next period's dividend budget is computed from current net profit and closing
cash with the same rule. It is informational, not another payment, payable,
or liability deducted from current equity.

Retained earnings still record every profit, loss, and actual dividend:

`RE_close = RE_open + N-D`.

Negative past retained earnings do not veto a later profitable period's funded
dividend. Previously retained noncash earnings do not create an automatic future
payout entitlement. This is a simple economic payout policy, not a simulation
of statutory distributable reserves or company-law restrictions.

### Alternatives examined and rejected

- Distributing all cash surplus maintains 0.8's constant operating float, but
  can distribute capital rather than net income. It would require a different
  “owner distribution” story.
- Requiring accumulated retained earnings to be positive before every dividend
  was independently found to create a permanent payout lock after some initial
  depreciation losses. With otherwise default settings and K1=100, retained
  earnings approach about -0.172884, dividends never restart, and household
  money decays toward zero despite physical capital recovering. This was not
  a numerical error. The selected previous-period net-profit rule avoids that
  additional historical-loss gate without erasing any loss from the accounts.

Even under the selected policy, a large initial loss can leave most money at
the firm and a small amount circulating with households. Do not imply that
nominal balances recover to the initial distribution or add money to force it.

## 9. Economic balance sheets and valuation

Use one disclosed economic valuation system: productive capital at the current
replacement price of X. This is not a traded share price, guaranteed resale
value, or historical-cost/IFRS statement. No second capitalization-cost ledger
or depreciation method is added in 0.9.

For t>1, opening capital value is p_previous*K and closing capital value is
p*K_next. The holding gain/loss is

`HG = (p-p_previous)*K`.

Then

`capital_value_close - capital_value_open = p*I-Dep+HG`.

At period one, value the endowed opening capital at the first solved price p1
and set HG1=0. Do not fabricate a prior price, setup-date capital purchase, or
initial income. The first valuation is recorded in the submitted run and never
recomputed using a later price when viewing history.

Firm equity E=firm money+capital value, with no debt:

`E_close-E_open = N-D+HG`.

Track initial contributed equity, accumulated retained earnings, and a separate
revaluation reserve; their sum must equal equity. Holding gains are not earned
operating profit, cash, investment, or part of the profit ceiling for dividends.

Each household owns 1/n of firm equity. Its reported assets may include money
and ownership value, clearly separated. For consolidated economy assets,
eliminate those ownership claims against firm equity. Never add the households'
share values to the full firm assets again.

Show total money and physical capital separately at economy level. If a combined
value is ever needed, label it “Assets within this model”, not an unqualified
national-net-worth claim: the issuer of the initial money is outside this model.

## 10. Reporting and stock-flow contract

### Cash and real-resource identities

`Q = sum(c_i)+I`

`K_next-K = I-delta*K`

`F_close = F_open-D-W+S`

`h_i_close = h_i_open+d_i+w*l_i-p*c_i`

Total household plus firm money is conserved after EVERY monetary transfer.
Production, installation, consumption, wear, and revaluation are distinct
noncash events, not Money transfers. In particular there is no Firm-to-Firm
purchase, hidden capital supplier, or mysterious “investment spending” outflow.

### Economy income

`V = p*C+p*I = W+G`

`V-Dep = W+N`

`household cash saving + firm net saving = (W+D-S)+(N-D) = p*I-Dep`.

Dividends are an internal distribution and cancel on consolidation; they must
not be added to current wages and profit as another source of economy income.
Own-use capital adds to production value but not cash sales. Investment is an
asset addition, not an expense deducted again after already charging wages.

### Period and cumulative scope

Sum real and monetary flows across selected periods, using EACH period's own
price: output, consumption, investment, wear, cash sales, wages, net income,
paid dividends, pI, Dep, and holding gains. Opening/closing money, capital,
retained earnings, and equity use first opening and selected closing snapshots.

Never sum prices, wages per labor unit, stocks, or scheduled future payouts.
Displayed price/wage are the selected period's; cumulative work/leisure are
averages, with total work-periods available in details. Cumulative nominal output
is sum(p_t*Q_t), not the last price times cumulative physical output.

Both capital bridges must hold cumulatively, including revaluation in the
monetary one. Reports, tutor context, and CSV consume one canonical report
contract. Setup drafts must never change historical report parameters.

## 11. Phone-first interface

Preserve 0.8's card palette, compact controls, restrained type, hierarchy, stable
expanders, one-line navigation, and existing report switch. Do not add another
tab, replay, timeline table, chart gallery, or duplicate household-account card.

### Setup

Household cards stay unchanged. The firm card adds Starting capital, Reinvest
surplus (%), and Capital wear (%) alongside operating money and productivity.
Use short section labels inside the existing card, not nested settings menus.

Investment caption:

> Surplus is output value minus wages, before capital wear. Keep 40% of that
> value as new capital.

Capital caption:

> Some X is consumed. Some becomes capital that produces from the next period.

Starting totals: “2 households · 3 Money · 1.00 capital”. Show equal ownership
once. No initial monetary capital value until the first market price is known.

### Results

Keep headline price, wage, and output. In cumulative mode explicitly identify
price and wage as selected-period values. Add only one neutral physical-capital
consequence sentence, such as “Investment exceeded wear; capital grew.”

Whole economy: Produced / Consumed / Added to capital, followed by a compact
capital opening-to-closing line and total Money. Show net economy income with
its wages/net-firm-profit breakdown; disclose the gross-output/depreciation
bridge in the existing details rather than another full always-open statement.

Households: preserve money, consumed X, work/leisure, and priorities. Put the
fixed ownership share and current-value ownership assets in their existing
account disclosure, not a second outcomes block. Ownership is not spendable cash.

Firm: keep one self-contained card with:

1. Produced / Sold to households / Added to capital in three compact rows.
2. Capital: opening - wear + added = next-period capital, in capital units.
3. A compact income statement: output value - wages = surplus; - wear value =
   net operating profit. Label the output value as including own-use capital;
   disclose the cash sales plus pI bridge in account details.
4. Existing cash disclosure, extended with balance/equity and revaluation detail.
5. A calm “Next-period dividend: … M” line. If zero, “No dividend available for
   next period”; do not assume that means no profit.

Cash details contain ONLY actual cash flows. Equity details contain capital
valuation, holding gains/losses, contributed equity and retained earnings.
Technical terms belong in disclosures and Ask why, not repeated captions under
every household. Tiny nonzero prices/payments must not be displayed misleadingly
as exact zero; retain an adaptive small-value notation and full-precision CSV.

Ask why adds:

- Where did the new capital come from?
- What does “Reinvest surplus” mean?
- Why did capital fall even though the firm invested?
- Why is profit different from cash and dividends?
- Why can capital value fall while capital units rise?
- Did wages rise in Money, or in what they can buy?
- Is more investment always better?

All built-in explanations remain free. AI explanations use the same selected
scope/valuation/payout metadata, clearly identify model assumptions, and do not
claim the user has chosen optimal investment or simulate unmodeled credit.

## 12. Baseline and worked multi-period example

Default settings from section 3 produce the following derived values. They are
not hardcoded targets or forced paths. Displayed rounding is only for readability.

| Quantity | Period 1 | Period 2 | Period 10 |
| --- | ---: | ---: | ---: |
| Opening capital | 1.000000 | 1.250823 | 3.611988 |
| Labor, total | 0.769231 | 0.769231 | 0.769231 |
| Wage, M per work unit | 1.181818 | 1.181818 | 1.181818 |
| Price, M per X | 1.036523 | 0.926789 | 0.545388 |
| Produced, X | 1.754116 | 1.961807 | 3.333738 |
| Consumed, X | 1.403293 | 1.569446 | 2.666990 |
| Added capital | 0.350823 | 0.392361 | 0.666748 |
| Capital wear, units | 0.100000 | 0.125082 | 0.361199 |
| Closing capital | 1.250823 | 1.518102 | 3.917537 |
| Net operating profit, M | 0.805439 | 0.793166 | 0.712097 |
| Dividends actually paid, M | 0.000000 | 0.545455 | 0.545455 |

Period-one cash sales are 1.454545, wages 0.909091, operating cash surplus
0.545455, and firm closing cash 1.545455. New capital value is 0.363636 and
capital wear value is 0.103652. Initial firm equity is 2.036523, closing equity
2.841962, and the increase equals net operating profit because initial dividend
and holding gain are zero. Each household works 38.4615%, consumes 0.701646 X,
and closes with 0.727273 Money. The next dividend budget is 0.545455, not the
full 0.805439 net profit.

For this symmetric baseline, the unconstrained branch keeps labor and nominal
cash flows constant while capital grows. Its positive steady state has capital
12.307692, output 6.153846, and consumption 4.923077. This follows from
`I=r*(1-theta)*Q=delta*K` with the baseline labor solution. Prices fall and the
real wage w/p rises; the nominal wage does not have to rise.

The app must not extrapolate perpetual percentage growth from this transition,
or guarantee global convergence for all heterogeneous setups. With delta=0,
positive investment can keep increasing capital; with r=0 and delta>0, capital
shrinks. Maintenance means I=delta*K, not matching the numerical percentages
of reinvestment and depreciation, which have different denominators.

Useful counterexample: with otherwise default settings in the payroll-bound
branch, r=70% has steady capital 61.25, output 14, and consumption 7.875; r=90% has
capital 180, output 24, and consumption only 6. More capital and output do not
necessarily mean greater sustainable consumption, let alone greater utility.
No “always invest more” recommendation or optimal-rate badge belongs in 0.9.

## 13. Architecture and build boundaries

Add an independent chapter and pure Python engine. Do not retrofit capital
into the 0.8 period type or call the 0.8 advance function with a changed A:
cash sales, physical output, profit, and dividends now have different meanings.
Reuse neutral finite-number/formatting helpers, preference logic where safe,
chat protections, and the read-only results-component pattern. Avoid a broad
shared-engine refactor during this release.

Proposed public boundaries:

- Immutable household/firm settings for a submitted run.
- `Economy09Period`: complete opening, settlement, physical, income, valuation,
  closing, and diagnostic snapshot.
- `advance_investment_period(...)`: deterministic, no Streamlit/session state.
- `investment_report(periods, cumulative=False)`: shared human/UI/CSV/tutor data.
- Separate 0.9 setup page, result component, and built-in explanations.

Period fields must distinguish `production_value`, `sales_received`,
`gross_operating_surplus`, `net_operating_profit`, `investment_quantity/value`,
`depreciation_quantity/value`, `capital_open/close`, `capital_price_open/close`,
`holding_gain`, `equity_open/close`, `retained_earnings_open/close`,
`revaluation_reserve_open/close`, actual `dividends_paid`, operating float,
post-dividend funding, and `next_dividend_budget`. Avoid an ambiguous catch-all
`profit` field inherited from earlier chapters.

Keep real transfer kinds (dividend, wage, goods payment, goods delivery).
Record physical/accounting events separately for production, consumption,
capital installation, wear, and revaluation. Full evidence exports need explicit
units, event types, periods, valuation prices, and stable party identifiers.

All historical snapshots and submitted parameters are authoritative; editing
the draft changes neither history nor scheduled payments until a new run starts.
The Python engine must remain independent of Streamlit for a future API/mobile
frontend. No API migration, user accounts, database, or app-store work here.

## 14. Acceptance gate before deployment

1. Independently derive the default period and later-period transitions above.
2. Verify household budgets, preference normalization, labor FOCs/zero-work
   corners, and funded firm KKT conditions without calling solver internals.
3. Check goods allocation Q=C+I, physical capital continuity, and investment
   available only next period, with wear charged only on opening capital.
4. Reconstruct every cash transfer in order; no payer overdrawn, no money
   creation, no self-sale, and no phantom investment cash outflow.
5. Verify net profit, cash surplus, funded prior-period dividends, and first-
   period zero payout. Negative net profit schedules no dividend next period.
6. Verify capital valuation, first-price initialization, equity/retained earnings/
   holding-gain bridges, and consolidation of household ownership claims.
7. Check cumulative flows at original prices and both stock bridges; never sum
   balances or recompute opening valuation from the selected closing price.
8. Cover r=0, delta=0, near-upper-domain settings, heterogeneous priorities,
   zero-cash individuals, zero-work choices, funding-bound firms, capital loss,
   negative net profit, and later dividends despite past retained losses.
9. Reproduce the rejected accumulated-loss-policy trap and confirm the selected
   rule resumes payouts for K1=100 (about period seven in the default example).
10. Currency rescaling changes money, wage, price, nominal equity/income, and
    reserve proportionally but not physical allocation. Rescaling an agent's
    three scores together leaves its preferences and outcomes unchanged.
11. For r=0, delta=0, K1=1 and matched remaining settings, reproduce 0.8's
    allocations and cash flows over linked periods; additional equity reporting
    must not enter households' spendable budgets.
12. Demonstrate the high-investment/lower-consumption counterexample. Tutor
    and visual interpretation must agree with computed outcomes.
13. Handle unsupported/nonfinite inputs and solver failure atomically. Use
    scale-aware numerics; never invent small balances or capital to continue.
14. Verify setup persistence, reset, actual 320/375/390 px layouts, touch targets,
    no horizontal overflow, and expansion/scroll stability on +/- changes.
15. Run regression tests for all earlier chapters, component rendering tests,
    lint, and a clean live baseline/linked-period/cumulative/Ask why smoke test.
    Resolve the restored local pyarrow/test-environment problem before claiming
    a full regression pass. Deploy matching Python/report/component versions
    together and restart cleanly to avoid cached-module NaN displays.

Design-only arithmetic performed during this review: lead checked 6,000 linked
heterogeneous periods, the economic reviewer 5,000, and the independent verifier
7,500. These separate checks exercised constrained wages, physical resources,
money, profit, and valuation identities; they are not product tests, UI checks,
a proof of every long-run outcome, or an implemented release. A further 20
linked periods matched the actual 0.8 engine in the no-investment/no-wear limit,
and 90 linked periods passed currency and relative-priority scaling checks.
The build must turn the specification into reproducible committed acceptance
tests.

## 15. References and approval boundary

The standard building blocks—one good usable for consumption or capital,
Cobb–Douglas production, capital accumulation, and replacement at a steady
state—are supported by [Daron Acemoglu's MIT growth lectures](https://ocw.mit.edu/courses/14-452-economic-growth-fall-2016/2b68057aa4e74410d00ae89a0c49752f_MIT14_452F16_Lec2and3.pdf).
Their representative-household assumptions and capital-rental setup are not
being imported wholesale into this monetary model.

[BEA's NIPA glossary](https://www.bea.gov/resources/methodologies/nipa-handbook/pdf/glossary.pdf)
defines own-account investment as production of fixed assets for one's own use
and distinguishes gross operating surplus from capital consumption and net
operating surplus. This supports the terminology, not our dividend rule.

[The OECD's explanation of output for own final use](https://www.oecd.org/en/publications/oecd-handbook-on-the-compilation-of-household-distributional-results-on-income-consumption-and-saving-in-line-with-national-accounts-totals_5a3b9119-en/full-report/component-12.html)
supports market-price valuation where comparable prices exist. Our identical
dual-use X provides a simple observable price proxy; installed capital is not
being promised a realizable resale value.

The surplus-reinvestment policy, scalar monetary equilibrium, payout policy,
cash reserve, valuation initialization, and baseline are explicit design choices
and derivations of this application.

Approved scope: build this bounded one-good, own-account-capital model, with
40% surplus reinvestment and 10% wear as the initial experiment, current-price
economic accounts, and cash-limited prior-period net-profit dividends. Keep
Economy 0.8 independently available throughout.

## 16. Implementation and validation

The release adds an independent engine and immutable snapshots, canonical reports
and explicit-unit account/transfer/event exports. Setup puts the firm's resource
and investment choices first. Results show the physical consumption/investment
split, compact capital and income statements, and household preferences. Detailed
cash, ownership, and valuation accounts use disclosures. A ten-period advance is
atomic: a failed candidate leaves the previously accepted history intact.

Local verification: 230 Python tests, all three JavaScript component suites, and
Ruff pass. Independent economic checks include loss recovery with resumed
dividends, currency scaling, the no-investment Economy 0.8 limit, and cumulative
accounts valued at each original period's price. UI tests cover saved drafts,
expander state, scope, reset, and failed batch advances. The renderer is tested
against real engine reports, including tiny nonzero values and complete CSVs.

Actual 320/375/390px device rendering has not been verified: the available cloud
browser has no viewport emulation. Layouts use flexible columns, readable type
and 44px controls; phone interaction still needs device review. Desktop live
inspection verified the baseline, ten-period advance, cumulative firm accounts,
and scope-aware built-in explanations. GitHub CI passed for the release.
