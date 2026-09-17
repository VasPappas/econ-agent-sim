# Selecting a market equilibrium

The current model solves a household consumption–money–leisure problem and
competitive firm labor demand. Consumption targets preserve strict concavity
of each household's own decision, but they do **not** guarantee that the whole
economy has only one equilibrium. Aggregating different households and firms
can produce more than one price and wage pair that clears both markets.

## A reproduced example

The exact supported settings are retained in
`tests/test_market_selection.py::multiple_equilibrium_economy`.
They contain three heterogeneous households and two separately funded firms.
The independently certified first-period outcomes include:

| Candidate | Price of X | Wage |
| --- | ---: | ---: |
| 1 | 32.7595471752 | 290.910187596 |
| 2 | 75.2892191646 | 295.845286755 |
| 3 | 571.8438592953 | 241.090887705 |

For every candidate, the household marginal conditions, firm marginal
conditions or binding cash constraint, goods clearing and labor clearing hold.
Independent reconstruction from the original audit's values had maximum
relative discrepancies below `1.1e-13`. Thus multiplicity is an economic
property of this configuration, not an accounting discrepancy.

The retired Economy 1.1 search selected the third candidate as a consequence
of its search bracket. The current model makes its selection convention
explicit and records it in the solution diagnostics.

## Selection convention

1. In the first period, compute the otherwise identical economy's equilibrium
   with all consumption targets set to zero and firms using percentage policies
   (the same investment-budget fractions). Use its price as the reference.
2. In later periods, use the previous accepted period's price as the reference.
3. Among the detected, numerically validated candidates, select the one with
   the smallest `abs(log(candidate_price / reference_price))`.
4. If two candidates are equally close, prefer the lower price deterministically.

Logarithmic distance measures a proportional price change. Changing the unit
of money therefore does not change the selected real allocation. This rule
also avoids an arbitrary nominal anchor such as a price of one.

For the example, the target-free first-period reference is `32.7582236117`,
so the current convention selects the first candidate. A later reference
near 80 selects the second; a reference near 600 selects the third. The rule
does not label one candidate socially best or more economically stable.

Previous-price continuation is a modeling convention for comparative
experiments. It can still switch branches if one disappears or another
becomes closer. It is not an implementation of price adjustment through time.
In particular, the slope of a computational residual parameterized by firm
payroll is not by itself a proof of stability under an economic adjustment
process. Such a claim would require specifying and analyzing that process.

## Search bounds and limits

The firm-payroll parameter is normalized by aggregate available household
money. For a trial parameter, let `B` be aggregate payroll and let `S` be the
value of goods firms offer after investment. Household spending lies between
`D0 = sum(alpha_i * available_cash_i)` and `1 + B`, where available cash sums
to one and `alpha_i` is the household's consumption share relative to money.

Consequently `S < D0` rules out clearing at the low end, while `S - B > 1`
rules out clearing at the high end. The relevant firm expressions increase
with the payroll parameter, providing economically derived finite search
bounds. The numerical search samples this interval on a logarithmic scale,
includes firm funding breakpoints, and refines detected sign-change brackets.

This is a finite search, **not a proof that every root has been found**.
Very close pairs of roots or a root that only touches zero without changing
sign can evade a sign-change scan. For target-aware or forward-investment searches the diagnostics
therefore record `root_search_complete = False`. A count of one means one
candidate was found, not that uniqueness has been proved.

When all targets are zero and every firm uses the percentage policy, the model
retains its specialized Cobb–Douglas solution. Forward-looking firms require
the general search even with zero targets.

## Forward-looking investment

The user-cost criterion can have a flat optimal-investment interval. Goods
clearing selects within it, allocating additional retention across indifferent
firms in proportion to their interval capacities. Stable IDs resolve roundoff.
Every final allocation must pass an independent investment certificate; the
solver never treats a sign jump between incompatible firm choices as a root.

The budget caps retention below 100% of surplus. Thus total production value
bounds offered sales above at the low search end, and the corresponding
percentage-policy sales bound them below at the high end. These bounds bracket
the search without assuming a monotone variable-investment goods residual.

With default symmetric firms, zero consumption targets, forward-looking policies
and a 75% required return per period (10% wear), tests reproduce three clearing
prices: approximately 0.816496580928, 0.927694406546 and 0.999697006181. The middle
case uses a nonzero investment from each firm's flat optimum. These parameters
are illustrative, not an empirical calibration.

## Reporting and saved experiments

The diagnostics record the detected candidate prices, candidate count,
selected candidate, reference price, selection rule and search method.
When several candidates are found, the application should explain that the
reported run follows this explicit selection convention. Detailed candidate
prices belong in technical evidence rather than routine household cards.

This convention can change outcomes relative to the retired solver. Saved
experiments must identify the engine rules used to create their results.
Historical files must not silently replay using a different selection rule.

## Regression evidence

The regression case checks all three recorded equilibria, household utility
derivatives reconstructed independently of the solver, firm funding and
optimality, and physical goods and labor clearing. It also checks first-period
selection, previous-price continuation, input-order independence and currency
unit invariance. These complement the full-period ledger and accounting tests;
passing a market residual alone is not sufficient certification.
