# Economy 1.0 — Two firms, one market

Status: implementation completed, 13 September 2026. The approved design below
is implemented in the separate 1.0 engine, reporting, workspace and versioned
experiment modules. Independent implementation checks cover the economic model,
funded ledger, cumulative accounts, saved-file restoration and UI interactions.
Deployment and live inspection are recorded in the release note below.

Based on Economy 0.9.1 at main commit
`288bf63292d5460b0d2c0813083f0f76dbcf60e1`. Synthesized from separate economics,
accounting, mobile UX and independent verification reviews. Earlier economies
and their saved experiments remain available.

## 1. Product decision

Add a second firm producing the same good X and hiring from the same households.
There is one market price for X and one wage per unit of work. Each firm owns its
capital, funds its payroll, chooses labor, retains physical output for investment,
and pays eligible dividends from its own accounts.

The central experiment is: start with two equal firms, change one firm's
productivity or reinvestment policy, and see how sales, production, employment,
capital and household outcomes change over time.

These firms are price takers. They optimize at the common price and wage; the
markets determine those prices simultaneously. Two finite firms do not by
themselves establish perfect competition as an empirical claim. We deliberately
assume price-taking behavior, as in 0.9. This release models allocation across
firms, not strategic price setting, Cournot output restriction, bargaining,
advertising, brand preference or a competition-induced markup reduction.

Keep exactly two firms in the first UI, two to twenty households, and up to 100
linked periods. Retain the existing consumption/real-money/leisure preferences,
own-account investment, wear, delayed funded dividends, period/cumulative
reports, baseline comparisons and portable experiment files.

Defer borrowing, banking, interest, bankruptcy, entry/exit, ownership trading,
inter-firm capital purchases, inventories, strategic pricing and exogenous shocks.
The reinvestment rate remains a fixed owner policy, not an optimized lifetime
saving rule. All purchased household X is consumed in its period.

## 2. A baseline with unchanged total resources

Split the existing firm's starting resources into two equal halves. Do not give
both new firms the full old endowment.

| Setting | Firm A | Firm B |
| --- | ---: | ---: |
| Starting Money / protected dividend float | 0.50 | 0.50 |
| Starting productive capital | 0.50 | 0.50 |
| Productivity A | 2.00 | 2.00 |
| Reinvest surplus | 40% | 40% |
| Capital wear | 10% | 10% |
| Labor exponent theta | 0.5, fixed | 0.5, fixed |

The two default households each start with 1 Money and relative preference
scores 1:1:1. Each household owns half of EACH firm. Starting totals remain
3 Money and 1 capital unit. Capital is endowed, not bought through a fictitious
startup payment.

Because production has constant returns jointly in capital and labor, this
proportional split mathematically reproduces the 0.9 aggregate baseline path.
The firms each receive half the previous firm's work, output, cash, profit and
capital. This is an acceptance requirement, not a hardcoded outcome. Merely
splitting a firm already assumed to be a price taker must not create a windfall.

Preserve the current numeric input bounds and steps: household Money 0–1,000,000;
positive relative scores 0.01–100 with +/- step 0.10; firm Money 0.01–1,000,000;
capital 0.10–1,000,000; productivity 0.10–100; reinvestment 0–90%, step 10
percentage points; wear 0–90%, step 5 percentage points. Inputs remain editable
directly. Firm inputs are independent; editing A never silently edits B.

The mathematical domain requires finite positive firm productivity, capital and
post-dividend cash, positive household preference scores, positive aggregate
household available cash, and 0 <= r, delta < 1. Unsupported numeric states must
fail atomically. UI bounds are not a guarantee of safe infinite-horizon arithmetic.

## 3. Within-period decisions

All opening stocks equal the preceding closing stocks; period one uses the
frozen submitted starting settings. Policies and ownership stay fixed within a
run. A setup change starts a new run rather than rewriting a completed period.

### Households

Normalize each household's three scores to a_i, b_i, g_i summing to one. Let
eta_i = a_i/(a_i+b_i), h_i be opening cash and z_i its cash after dividends from
both firms. At common p > 0 and w > 0, the household maximizes

`U_i = c_i^a_i * (m_i/p)^b_i * (1-l_i)^g_i`

subject to `p*c_i + m_i = z_i + w*l_i`, with `0 <= l_i < 1`.

The existing solution is unchanged:

`l_i = max(0, (1-g_i) - g_i*z_i/w)`

`c_i = eta_i*(z_i+w*l_i)/p`

`m_i = (1-eta_i)*(z_i+w*l_i)`.

Ownership values are not spendable balances. Households do not anticipate future
dividends or distinguish employers/suppliers in their preferences. A household
may choose zero work while consuming from its available money.

### Firms

For each firm j, opening capital K_j is fixed for current production:

`Q_j = A_j*sqrt(K_j*L_j)`

`W_j = w*L_j`, `V_j = p*Q_j`, `G_j = V_j-W_j`

`I_j = r_j*G_j/p`, `C_j = Q_j-I_j`, `S_j = p*C_j`.

C_j denotes the firm's household sales quantity; it is not its own consumption.
The cash-sales identity is `S_j = (1-r_j)*V_j+r_j*W_j`. Cash operating surplus
is `(1-r_j)*G_j`. Consequently maximizing that surplus, conditional on r_j < 1,
is equivalent to maximizing `p*Q_j-w*L_j`.

Each firm's own post-dividend cash B_j funds its wages. Its labor choice is

`L_j = min((p*A_j*sqrt(K_j)/(2*w))^2, B_j/w)`

or equivalently `W_j = min(V_j/2, B_j)`.

If funding is slack, the value of marginal product equals the wage. If funding
binds, it can exceed the wage. This is the usual price-taking hiring condition
with this model's additional cash limit. The standard unconstrained condition
is described in [MIT's labor-market lecture](https://ocw.mit.edu/courses/14-01-principles-of-microeconomics-fall-2023/mit14_01_f23_lec15.pdf).

Do not pool firms' cash or replace their individual caps with a cap on total
payroll. Current goods-sale receipts arrive after wages and cannot pre-fund them.
New capital is available next period only; opening capital alone suffers wear.

## 4. One positive equilibrium with a scalar solve

The following reduction is a derivation for this application. It is not a
textbook monetary wage rule, and it must be verified against the original
household and firm conditions in the implementation.

Let `Z=sum_i z_i > 0`, normalize Money by Z, and define

`u=w/Z`, `tau=p^2/(w*Z)`, `d_j=A_j^2*K_j/4`.

For each positive trial tau:

`Wtilde_j = min(d_j*tau, B_j/Z)`

`Vtilde_j = 2*sqrt(d_j*tau*Wtilde_j)`

`Stilde_j = (1-r_j)*Vtilde_j+r_j*Wtilde_j`.

Invert total household payroll at `Wtilde=sum_j Wtilde_j` to recover u:

`Wtilde = sum_i max(0, (1-g_i)*u-g_i*z_i/Z)`.

This function is strictly increasing above its zero-payroll region. Inversion
uses an active set, not a nested iterative optimization. Sort household work
activation thresholds `g_i*(z_i/Z)/(1-g_i)`. For an active prefix H, compute

`u = (Wtilde + sum_H g_i*z_i/Z) / sum_H (1-g_i)`.

Include the next household if u exceeds its activation threshold; tied thresholds
are handled consistently, and a household exactly at its threshold supplies zero.
The resulting household payrolls are `Wtilde_i=max(0,(1-g_i)*u-g_i*z_i/Z)`.

Solve the single residual

`R(tau) = sum_j Stilde_j - sum_i eta_i*(z_i/Z+Wtilde_i(u)) = 0`.

Recover `p=Z*sqrt(tau*u)`, `w=Z*u`, `L_j=W_j/w`, and all choices and accounts.
The recovered solution clears both labor and household goods markets.

### Why the root is unique

On a fixed working-household set, the slope of household spending against total
payroll is

`k_H = sum_H eta_i*(1-g_i) / sum_H (1-g_i)`, strictly between zero and one.

For an unconstrained firm, payroll rises with tau at slope d_j while sales rise
at slope `(2-r_j)*d_j > d_j`. A constrained firm's payroll is constant, but its
sales rise strictly with tau. Thus R is continuous and strictly increasing,
including across household and firm active-set boundaries.

Define `R(0)=-sum_i eta_i*z_i/Z < 0` directly; there is no need to invert household
payroll at zero. At sufficiently large tau both payrolls are capped, so household
spending is constant while firm sales continue to grow. R eventually becomes
positive. There is exactly one positive finite root in the stated mathematical
domain, including when both firms' funding caps bind.

### Numerical contract

Normalize Money to avoid changes in precision merely from choosing a different
currency unit. Avoid forming unbounded `A_j^2*K_j` directly. One stable capacity
normalization uses `a_j=A_j*sqrt(K_j)`, `a_max=max_j a_j`,
`q_j=(a_j/a_max)^2`, and `psi=(a_max^2/4)*tau` conceptually:

`Wtilde_j=min(q_j*psi,B_j/Z)`

`Vtilde_j=2*sqrt(q_j*psi*Wtilde_j)`

`p/Z=2*sqrt(psi*u)/a_max`.

Compute stable products/square roots without materializing avoidable overflowing
intermediates; do not actually square a_max to obtain psi. Bracket dynamically
and use a safeguarded monotone solve with explicit iteration and numeric-range
limits. Reject a relative capacity that underflows rather than silently removing
a firm. The proof of a mathematical root is not a proof that every floating-point
parameter combination is representable.

Independently certify household budgets and choices, both market balances,
each firm's funding and hiring conditions, positive quantities, and stock-flow
identities. Small residuals must be bounded relative to the relevant account
scale; never round inputs, prices or balances to display precision internally.

## 5. Fractional matching and funded settlement

Once aggregate choices clear the markets, match work and household purchases
proportionally:

`l_ij = l_i*L_j/sum_k L_k`

`c_ij = c_i*C_j/sum_k C_k`.

Firm j pays household i `w*l_ij`; household i pays firm j `p*c_ij`. These are
accounting allocation rules justified by indifference between equal-wage
employers and identical goods at one price. They are not additional optimization
or brand preferences. A household may work for both firms and buy from both.
Firm order must not allocate a substantive advantage to the first listed firm.

Settlement order:

1. Compute each firm's eligible dividend from its previous profit and current
   cash; pay all dividends from the respective firms to their household owners.
2. Solve the simultaneous markets with those post-dividend balances.
3. Pay all wages from each firm's own available money.
4. Record household labor delivered to the respective firms and firm production.
5. Pay for and deliver household X from the respective firms' produced stocks.
6. Consume household purchases; record each firm's capital wear and installation.
7. Close and validate all accounts, then append one complete immutable period.

Add explicit labor-delivery service legs paired with wage-payment legs. Labor
is a period service, not a household opening balance-sheet asset or a second wage
expense. Use explicit pair/transaction IDs for Money/Labor and Money/X legs.
Dividend transfers are Money only. Production, consumption, capital wear,
installation and revaluation are separate noncash events. No firm-to-firm payment
is created for own-account investment.

With two firms and twenty households there are at most 200 transfer legs per
period, including all dividend, wage, labor and goods legs. Exact zeros may be
omitted; small genuine transactions must remain in full-precision evidence.

Actual transfer amounts are the authority for cash accounts. Use accurate sums
and bounded, paired residual allocation to reconcile matrix margins. Never
create cash, finance a firm from another firm, clip an overdraft to zero, or
silently drop a household/firm to make a check pass. Any adjustment must remain
within numerical tolerance of the certified economic choices and preserve
paired consideration. If funding or margins cannot be reconciled, reject the
candidate period without changing accepted history. Both a single advance and
a +10-period batch must be atomic.

## 6. Dividends, capital and economic accounts

Apply the existing dividend policy independently for every firm:

`D_j = min(max(N_j_previous,0), max(F_j_open-B0_j,0))`, with `D_j=0` in period one.

Each household receives `D_j/n` from firm j. B0_j is that firm's original
protected operating float for dividend decisions, not a cash injection or a
minimum balance during wage settlement. Netting firms' profits or cash before
calculating D_j is prohibited. Past retained losses are recorded but do not add
the previously rejected cumulative-loss veto on later funded dividends.

Per firm:

`Dep_j=p*delta_j*K_j`, `N_j=V_j-W_j-Dep_j`

`K_j_close=(1-delta_j)*K_j+I_j`

`F_j_close=F_j_open-D_j-W_j+S_j`.

Opening capital value uses the preceding period's price; closing capital value
uses the current replacement price. Period one initializes opening value at its
first solved price and records zero holding gain. Thereafter:

`HG_j=(p-p_previous)*K_j`

`capital_value_close-capital_value_open=p*I_j-Dep_j+HG_j`

`E_j_close-E_j_open=N_j-D_j+HG_j`.

Retained earnings increase by N_j-D_j; the revaluation reserve increases by HG_j;
contributed equity is fixed. Their sum equals closing equity. Capital valuation
and holding gains do not enter spendable cash or the dividend profit ceiling.
Next-period dividends are informational budgets, not current expenses or
liabilities to subtract again.

For each household, opening and closing ownership assets are the sum of its
fixed shares in BOTH firms' corresponding equity. Its cash bridge is

`h_i_close=h_i_open+sum_j D_j/n+w*l_i-p*c_i`.

The consolidated economy must satisfy:

`sum_j Q_j=sum_i c_i+sum_j I_j`

`sum_i h_i+sum_j F_j = constant total Money`

`sum_j (V_j-Dep_j)=sum_j W_j+sum_j N_j`

`household cash saving+sum_j(N_j-D_j)=sum_j(p*I_j-Dep_j)`.

Cancel internal dividends and eliminate household ownership claims against
both firms' equity. Do not double-count share values and firm assets. Total
Money and physical capital remain separately prominent; their combined current
value, when disclosed, is labeled “Assets within this model.” There is no market
for trading those ownership claims or installed capital in this release.

The distinctions between own-account investment, operating surplus, capital
consumption and holding gains follow standard economic-accounting terminology
in [BEA's NIPA glossary](https://www.bea.gov/resources/methodologies/nipa-handbook/pdf/glossary.pdf).
The payout rule, matching convention and settlement order are our model choices.

## 7. Market shares and cumulative reporting

Use the explicit headline label **Share of sales**, meaning physical X sold to
households. Show Produced X separately. Never assign household purchases by
total output when firms retain different fractions as investment.

| Quantity | This period | Cumulative through T |
| --- | --- | --- |
| Produced / sold / invested X | Current physical flow | Sum of each physical flow |
| Share of sales | C_j / sum_k C_k | sum_t C_jt / sum_t sum_k C_kt |
| Share of production, in detail | Q_j / sum_k Q_k | Ratio of summed output |
| Money income / cash flows | Current flow | Sum at original period prices |
| Firm work used | Work units | Total work-periods |
| Household work / leisure | Share of one time endowment | Average across periods |
| Capital, cash, equity, reserves | Opening / closing stock | First opening / selected closing |
| Price / wage / real wage | Selected period rate | Selected period rate |
| Next dividend budget | One future budget | Same selected-period future budget |

The cumulative sales share is not an arithmetic average of period shares. Within
one period physical sales share equals revenue share because all sales have the
same price. Across periods, revenue shares using original monetary receipts can
differ from physical sales shares. Do not switch meanings silently.

## 8. Phone interface

Title: **Two firms, one market.** Intro: “Two firms make the same good. They hire
from the same households, receive the same price and pay the same wage.”

Keep Set up / Results / Ask why / Reset in one row and the existing collapsed
Experiments area. No timeline, trade replay or additional main navigation tab.

### Setup

Firm A and Firm B have separate stable expanders with the five existing compact
label-and-number controls. Firm A starts open; Firm B starts closed. Explain the
equal starting resources once. Household cards remain below the firms with the
current direct three-score preferences.

Starting summary: “2 households · 2 firms · 3.00 Money · 1.00 capital.” Ownership
copy reflects household count: “Each household owns half of each firm” for two,
or the correctly formatted equal share for larger populations.

### Results

1. Shared X price and wage, followed by the familiar whole-economy production /
   consumption / investment display and income/stock summary. Output remains
   prominent there rather than duplicated as a third price tile.
2. One Firms in this economy overview with both firms always visible. Each
   compact firm summary shows Sold X and Share of sales, then a two-column grid
   of Produced X, Work used, Net profit and Closing capital. Do not use a wide
   five-column table or reorder firms by performance.
3. A closed Firm accounts disclosure reveals a Firm A / Firm B selector and the
   selected firm's existing production, income, cash, capital and equity detail.
   This avoids displaying two complete sets of statements in the main flow.
4. Household cards show consumption, work/leisure, cash and chosen preferences;
   per-firm wages, dividends, purchases and ownership belong in their disclosures.
5. Evidence combines market, funding, conservation and account checks, with
   transfer details and full-precision CSV below.

Use “Work used,” never a fractional “Workers” count. One work unit means one
household working for a full period. In cumulative firm displays use work-periods.
Show “Hiring limited by available cash” only for a certified binding constraint;
in cumulative view identify it as the selected period's condition.

Retain the cream/green/gold palette, readable values, 44px touch targets, stable
disclosures and +/- controls. Keep firm identities visible at tiny sales shares;
adaptive notation must not turn positive production into a false closure.

### Baseline comparison and explanations

Keep the six whole-economy baseline metrics from 0.9.1. Inside the selected firm
detail, a collapsed “Firm A vs baseline” can compare Produced X, Share of sales,
Net profit and Closing capital. Match stable firm ID, engine, selected period
and report scope. Sales-share changes use percentage points. A short baseline
must not be extended silently or compared against a different date.

For the new chapter, use the clearer action label **Copy baseline setup**:
“Copies the original starting settings. Your results stay unchanged until you
start a new simulation.” Preserve the existing chapter's behavior and files.
Reset clears the active run and draft and restores defaults, while keeping its
comparison baseline; Clear baseline removes that baseline explicitly. A file includes both runs,
draft edits, selected period, scope and selected firm.

Add free Ask why topics for the common wage, differences in sales, cash-limited
hiring, production versus sales shares, firm-specific dividends, and why splitting
the default firm alone leaves aggregate outcomes unchanged. The optional AI
receives the canonical selected reports and comparison data within its existing
request/context limits. No automatic paid calls are added.

Do not award a “winner” badge: higher profit, capital or sales does not establish
better household welfare. Explain that more productivity need not increase the
nominal wage, and higher reinvestment need not immediately raise sales share.

## 9. Worked examples and interpretive limits

### Equal firms, period one

Common price is 1.0365231137 M/X and common wage is 1.1818181818 M/work unit.

| Quantity | Whole economy | Each firm |
| --- | ---: | ---: |
| Work units | 0.7692307692 | 0.3846153846 |
| Produced X | 1.7541160386 | 0.8770580193 |
| Sold X | 1.4032928309 | 0.7016464154 |
| Added capital | 0.3508232077 | 0.1754116039 |
| Wages paid, M | 0.9090909091 | 0.4545454545 |
| Net operating profit, M | 0.8054385977 | 0.4027192989 |
| Closing capital | 1.2508232077 | 0.6254116039 |

Each firm closes with 0.7727272727 Money; each household closes with
0.7272727273 Money. In the proportional settlement, each household supplies
0.1923076923 work to each firm, receives 0.2272727273 wages from each, and pays
each 0.3636363636 for 0.3508232077 X. Total Money remains 3.

### Increase only Firm A's productivity to 2.4

In period one, Firm A reaches its 0.50 payroll funding limit. Common price falls
to approximately 0.9423863660, common wage to 1.1616828316, and total household
consumption rises to 1.5292261642 X. Firm A sells about 57.56% of household X.
Purchasing power per work unit rises even though the nominal wage falls.

This is a checked example, not a universal comparative-statics claim. The user's
setup, household preferences, funding limits and later capital paths matter.

### Different investment policies

With two default households, give each firm capital 0.5, productivity 2 and
starting Money 1.00, then set reinvestment to 80% and 20%. The extra opening firm
cash makes both payroll limits strictly slack in this example. First-period
production is equal while sales shares are 40% and 60%. At the unconstrained
hiring choice investment/output is r/2, so the respective sold fractions are
60% and 90% of equal output. A high reinvestment policy can sacrifice sales now
while building future productive capacity. Even equal reinvestment percentages
can yield different investment/output fractions if only one funding cap binds.

### Independent dividend eligibility

Use two default households; both firms have A=2, Money=0.5 and r=40%. Firm A has
capital 100 and wear 90%; Firm B has capital 0.5 and wear 10%. Period-one net
profits are approximately -9.132543 and +0.001775. In period two A pays no
dividend while B pays about 0.001775. Combining their profits before applying
the payout rule would incorrectly block B's eligible dividend.

### No endogenous firm exit

Positive capital, productivity and cash, together with this production function,
imply positive firm production in every finite mathematically supported state.
Gross operating and cash surpluses are positive, although capital wear can cause
net accounting losses. A firm may become tiny; it does not automatically fail,
exit, liquidate or acquire pricing power. Numerical underflow is an unsupported
numeric state, not an economic bankruptcy event. Competition does not imply zero
accounting profit when owned capital has not been charged a rental expense.

## 10. Architecture and saved-file compatibility

Add an independent 1.0 chapter and engine. Keep 0.9 and its serializer unchanged
so existing files still reopen and continue under their original engine.

Recommended boundaries:

- Frozen setup: households, two firm specifications, stable entity IDs, and
  fixed equal ownership of each firm. Labels never serve as account identity.
- `advance_competition_period(setup, previous=None)`: pure deterministic solving,
  allocation, settlement and validation; no Streamlit or file operations.
- Immutable period snapshot with plural firm states, household choices,
  employer/supplier allocations, common prices, transfers, noncash events,
  opening/closing accounts and structured diagnostics.
- `competition_report(periods, cumulative=False)`: canonical firm, household and
  consolidated reporting used by UI, CSV, comparisons and Ask why.
- Dedicated 1.0 page and results renderer; reuse neutral formatting and protected
  chat behavior without a broad refactor of the completed chapters.

Reports use `firms[]` with immutable IDs such as firm_1 and firm_2, `households[]`,
`economy`, `price`, `wage`, `real_wage`, scope metadata, checks, transfers, events,
rows and policies. Do not keep a misleading singular `firm` alias. Carry each
firm's 0.9 account meanings forward, adding work used, explicit physical sales
share, and per-household allocation evidence. Household per-firm breakdowns must
sum back to their headline totals.

Give 1.0 a distinct engine identifier and a new explicit file schema (version 2
with a model discriminator and plural firms). Preserve separate draft/submitted
settings and the optional immutable baseline. Snapshot verification includes
firm IDs, ownership, both firms' accounts and all allocation/evidence data.
Keep bounded JSON parsing, finite-number checks, file/household/period limits,
exact supported-version restoration, and atomic acceptance from 0.9.1.

An old-model file should be recognized and directed to the compatible 0.9
workspace without overwriting the current 1.0 experiment. Do not rewrite a
single firm's historical results into two firms, regenerate its fingerprints,
or compare histories produced by different engines as if they were one run.
Any future import of old starting settings must be an explicit new experiment
with disclosed resource splitting; it is outside this first implementation.

Persist selected firm, expanded cards, draft, selected period and report scope
independently of transient widget state. Restoring a file must clear conflicting
widget values before rendering the restored draft. Changing a card's displayed
values must not change its identity or collapse it.

## 11. Verification completed and implementation gate

Two separately written design prototypes verified the monotone reduction. The
independent verifier matched the actual 0.9 engine for 100 linked periods after
splitting its firm, including aggregate price, wage, production, capital, profit
and dividends. Additional arithmetic covered seven contrasting 30-period paths,
one/both cash caps, different productivity/investment/wear, losses, zero-work and
zero-cash households, currency scaling, and reversed entity ordering. Firm labor
choices were checked against sampled alternatives; household budgets and first-
order/corner conditions were checked independently. The accounting reviewer
checked the default proportional settlement separately.

These are design calculations. They do not certify an implemented 1.0 solver,
payment ledger, upload workflow or phone layout. Before release, require:

1. Reproduce the analytic equal-firm example and 0.9 aggregate path without
   hardcoded targets; swapping firm order preserves corresponding outcomes.
2. Independently verify household labor choices and budgets, both firm hiring
   conditions, and separate payroll caps in none/one/both constrained cases.
3. Replay every monetary transfer: no overdraft, pooled funding, self-payment or
   money creation; prove employer and supplier allocation row/column margins.
4. Reconcile each firm's goods, installed capital, wear, cash, profit, dividends,
   equity, retained earnings and holding gains, as well as consolidated accounts.
5. Reproduce the 80%/20% production-versus-sales example and the profitable firm's
   dividend despite the other firm's loss. Include different funding with equal r.
6. Test currency rescaling and common scaling of a household's priority scores;
   preserve physical choices and appropriately scale nominal values.
7. Verify cumulative original-price flows, endpoint stocks/rates, ratio-of-sums
   shares, household average time and firm total work-periods. Never sum future
   dividend budgets or silently substitute unlike comparison horizons.
8. Restore and continue a saved 1.0 run with both firms, baseline and a different
   unsubmitted draft. Reject corrupted/unsupported files without replacing state;
   existing 0.9 files still work in their own chapter.
9. Check context size at maximum households and cumulative evidence, correct
   firm/period/scope in Ask why, CSV escaping/units, and no false zero or closure.
10. Verify numeric failures and failed +10 advances leave complete history intact.
    Large or extreme values must not cause unbounded work or silent firm removal.
11. Inspect actual 320/375/390 px layouts, touch targets, large/tiny values, stable
    firm selection, disclosures and scroll position, reset/copy semantics, and
    actual file download/reopening. The available desktop cloud browser alone
    cannot certify phone rendering; the prior download verification gap remains.
12. Run existing regression checks, deploy matching engine/report/component
    versions together after implementation approval, and inspect the live baseline,
    asymmetric case, linked periods, cumulative accounts and saved-file workflow.

## 12. Recommended implementation sequence

First build the pure solver and immutable multi-firm state against independent
economic acceptance cases. Then complete funded pairwise settlement and canonical
accounts. Build the compact workspace and firm/baseline comparisons against that
stable report contract. Add versioned save/reopen and scoped explanations, then
perform integration, phone and live verification.

The build uses separate engine, accounting/reporting, mobile UI, experiments and
independent verification workstreams. Earlier chapters and the 0.9 file format
remain unchanged. The implemented entry point is
`advance_competition_period(households, firms, previous=None)`; specifications
carry stable IDs separately from names. Default firm IDs are `firm_a` and `firm_b`.

## 13. Implementation verification

The implemented engine passed 100 linked periods against the actual 0.9 aggregate
baseline, independent household/firm optimality and full ledger replay. Acceptance
cases cover currency and preference scaling, reordered entities, mixed funding
limits, independent dividends despite another firm's loss, unequal reinvestment,
and tiny positive firms at extreme supported setup values. A separate stress run
covered 3,000 heterogeneous periods. It caught final-payment roundoff; actual
payment and paired delivery now use the same funded representable amount.

Reporting checks cover each firm's and household's bridges, consolidation,
original-price cumulative flows and physical sales-share ratios. Saved-file
tests replay maximum-size runs, preserve different drafts and baselines, continue
deterministically and reject corrupt files atomically. UI tests exercise firm
selection, disclosures, independent edits, reset/copy behavior and failed batches.
The shared optional AI request remains bounded; repeated account fields are
represented as named-column tables without rounding calculation values.
