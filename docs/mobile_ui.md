# Phone-first presentation

One root workspace, three primary navigation buttons: Set up / Results / Ask why.
Experiment management and Reset live together in a lower disclosure.

Keep controls native, labeled and touch-friendly. Prefer short field labels,
relative priority steppers and explicit actions to hidden automatic changes.
Household and firm setup disclosures retain their open/closed state on reruns.
Preset selection alone does not apply anything.

Results use compact summaries first, detailed statements and transaction receipts
on demand. Firm selection uses stable IDs. Avoid wide tables in the normal
reading path. Core labels use at least 12px; input targets are approximately
44px or greater. Target progress has accessible progress semantics.

Render only canonical report values. Money and asset balances use two decimals;
prices and receipts use four with tiny-value handling. Full precision stays in
calculations and CSV. Do not display negative rounded zero as a meaningful loss.
Positive cash movement is not automatically welfare or profit.

Use one shared style module and one results component. No chapter-specific
copies or custom renderer state coupled to a particular Streamlit session key.
