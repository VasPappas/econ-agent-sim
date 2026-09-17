# Audit fixes before purposeful investment

The independent audit of commit `0c21832` identified nine actionable findings.
The optional chat removal in `242db9a` retired A1 and A2. This change addresses
the seven remaining findings without adding new economic decision rules.

| Finding | Correction |
| --- | --- |
| N1: intermediate wage-scan precision | Accept a scan point at exhausted floating-point resolution only when adjacent representable wages still bracket the payroll root. Keep final market certification unchanged. |
| N2: cancellation in net-income checks | Use a compensated signed residual and explicit rounding allowances for the two stored subtractions, retaining the production-scale economic tolerance. |
| P1: malformed Unicode names | Reject surrogate code points before publishing imported state; preserve valid multilingual names and emoji. |
| P2: duplicate imported IDs on expansion | Allocate new household IDs against every retained household and firm identity. |
| P3: invalid outgoing name blocks import | Validate edits while retaining the last valid name; validate restoration using the incoming experiment name. |
| U1: fractional policies appear as integers | Preserve significant digits in percentage inputs and firm parameter displays, including tiny positive values. |
| U2: unmatched baseline firm lacks explanation | Render the individual firm's unavailable-comparison reason while preserving economy-level comparison. |

## Verification

- Full Python suite: **107 passed**.
- JavaScript results-component suite, Ruff and whitespace checks: **passed**.
- Independent numerical review repeated the original **158 configurations over
  three periods**: all passed household-optimality and ledger/account checks,
  including all 13 previously rejected cases.
- **75 complete snapshot fingerprints across 25 seeded configurations** matched
  the audited baseline exactly. The released saved-workspace fixture also replays.
- Independent persistence/UI review found no blocking issues. Tests cover actual
  callbacks, atomic failed imports, names, household expansion, fractional policies
  and unavailable firm comparisons.
- Streamlit's installed frontend formatter was executed directly to verify
  general numeric format support; AppTest alone does not verify browser layout.

The unchanged saved-file schema and engine identity remain appropriate: this
change preserves recorded economic outputs for previously accepted cases and
corrects rejection/validation/display behavior. The finite market scan still
does not guarantee that every possible clearing price is discovered.

The [investment specification](investment_design.md) is a separate proposal for
review. Its worked examples are conditional firm forecasts, not new app results.
