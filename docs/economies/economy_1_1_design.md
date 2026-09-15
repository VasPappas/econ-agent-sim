# Economy 1.1 — Consumption targets

Economy 1.1 adds a flexible consumption target to the two-firm Economy 1.0.
It makes consumption below a chosen target more urgent without guaranteeing
that target, creating goods or money, or changing firms' economic rules.
Economies 0.9 and 1.0 remain available with their existing saved-file engines.

## Household choice

Each household has a target `b` in units of X per period. Its three existing
priority scores are normalized to positive weights `a`, `d`, and `g`, summing
to one. Utility is

```text
a log(C) + d log(M) + g log(leisure) - penalty(C / b)

penalty(z) = z - 1 - log(z), if b > 0 and 0 < z < 1
             0, otherwise
```

The penalty strength is fixed at one. This is an explicit modeling choice,
not another user setting. It is a soft-target extension of log utility, not
Stone–Geary utility or a subsistence constraint.

Below target the marginal utility of consumption is `(a + 1) / C - 1 / b`.
At the target it joins `a / C` continuously. As consumption falls, its urgency
increases. The utility remains strictly concave on the positive domain;
the penalty diverges as positive consumption approaches zero. Money and leisure
retain positive weights, so a shortfall does not force the household to spend
all its money or work every available moment. All priority scores remain fixed.

The target is current-period only. A past shortfall is recorded for reporting
but does not become debt or increase a future target. There is no new borrowing,
transfer, rationing mechanism, or consumption guarantee.

## Conditional solution and market clearing

Given total resources `T`, target expenditure `q = p*b`, and the sum `s` of
other utility weights, ordinary consumption spending is `a*T/(a+s)`. It is
unchanged when it reaches the target, or when `b=0`. Otherwise the spending
solution is the smaller root, evaluated without subtractive cancellation:

```text
A = a + 1
r = T / q
E = T * 2*A / (A+s+r + sqrt((A+s+r)^2 - 4*r*A))
```

The implementation scales this expression for numerical stability. For the
working choice, resources include full-time labor income and `s=d+g`. If the
result would imply leisure above one, the no-work boundary is solved with
cash resources alone and `s=d`. Purchases are recomputed against the actual
settled wage income before accounts are finalized.

The two firms retain Economy 1.0's production, payroll funding, depreciation,
investment, ownership, and dividend timing. A nested bracketed solver clears
the joint household/firm market. The inner payroll inversion is monotone;
the outer price search uses continuity and a sign-changing bracket. The
implementation does not claim a general proof of uniqueness or global
monotonicity of that outer equation.

When all targets are zero, the existing Economy 1.0 market solver is used
directly. This reproduces its economic behavior exactly; the new saved-period
digest includes the target parameter and therefore belongs to a new engine.

## Setup and reporting

- Target default: 0.50 X per household per period.
- Target controls: 0 to 100 X, +/- 0.10, with direct numeric entry.
- Target zero disables the extra preference term.
- Default first-period consumption is about 0.7016 X per household, so the
  default target has no first-period effect. Set a target to 1.00 X to explore
  an active shortfall.
- Household cards show the target, consumption, coverage, and shortfall.
- Economy coverage adds individually fulfilled targets; extra consumption by
  one household never offsets another household's shortfall.
- Cumulative target and shortfall numbers sum separately for every household
  and period. Money flows continue to use their original period prices.
- Accounting checks describe accounting validity. They may all pass even
  when consumption targets are not met.

For household `i` in period `t`:

```text
needed_X    = b[i]
needs_met_X = min(C[i,t], b[i])
shortfall_X = max(b[i] - C[i,t], 0)
coverage    = needs_met_X / needed_X, or undefined if needed_X is zero
```

Gap quantities retain full precision. Counts of below-target periods use the
model's numerical tolerance. Small positive gaps are not presented as complete
coverage merely because of percentage rounding.

## Saved experiments and explanations

Files use format version 3, model `consumption_target`, and engine
`consumption-targets-1.1.0`. They preserve submitted settings, an independently
editable draft, selected report scope, firm selection, and full period replay
digests. Older files are routed to their original economy; they are not silently
converted. Baselines and copies are isolated from the active experiment.

The page has its own session-state namespace. The new engine reuses immutable
Economy 1.0 account types; reporting adds target measures to the canonical
accounts instead of introducing another ledger. Existing engines are unchanged.

Built-in explanations require no API call. The optional AI context includes
actual target settings, selected/cumulative results, and baseline changes.
Repeated fields are represented as named-column tables to remain within the
existing context allowance at the maximum supported household count. This
compaction retains numeric precision and changed setting values.

## Validation and limits

Checks cover independent household optimality conditions and boundary choices,
goods/money conservation, account identities, target-zero equivalence,
heterogeneous targets, cumulative shortfalls without offsets, file replay and
rejection, a frozen released 1.0 fixture, and actual Streamlit/component output.
Long-run checks include five 100-period scenarios, twenty households, asymmetric
firms, and high-target/low-productivity cases that are problematic for a hard
subsistence requirement. Randomized market checks supplement these cases.

Illustrative first-period values with both default households sharing a target:

| Target X | Price M/X | Wage M/work | Consumption X | Closing money | Work |
|---:|---:|---:|---:|---:|---:|
| 0.00 or 0.50 | 1.036523 | 1.181818 | 0.701646 | 0.727273 | 0.384615 |
| 1.00 | 1.290340 | 1.041307 | 0.742977 | 0.541307 | 0.480166 |
| 2.00 | 1.430084 | 0.890957 | 0.775509 | 0.390957 | 0.561194 |

Supported workspace limits remain twenty households and one hundred periods.
The numerical solver rejects unsupported or non-clearing inputs rather than
inventing a result. An economy with zero total household cash is not supported
by the inherited firm market rules. Tests establish the checked domains, not
a theorem covering every possible floating-point combination.
