# Mobile UI evolution

The Streamlit simulator is designed mobile-first. Changes to the phone experience are introduced incrementally so each interaction can be tested before adding the next one.

## Step 1 — persistent view navigation

Economy 0.3 keeps `Overview`, `Market`, and `Audit` available as the three top-level views. On screens up to 768 px wide, that selector is presented as a fixed bottom navigation bar so the user can switch views without scrolling back to the top of a long page.

The mobile navigation is scoped to the Economy 0.3 view selector through the Streamlit container key `economy03_mobile_nav`. It uses safe-area insets for phones with display cutouts or home indicators. The bar is deliberately raised above the very bottom of the viewport so browser chrome and Streamlit floating controls do not cover `Audit`, and the page reserves extra bottom padding so long content cannot scroll behind the navigation.

On wider screens, the same view selector remains in the normal document flow. No economic model, settings, redistribution behavior, accounting, or ledger logic changes as part of this UI step.

To keep each view focused, the `Model boundary` explanation belongs to `Overview` only. `Market` is reserved for price discovery and clearing, while `Audit` is reserved for decisions, accounts, and ledgers.

Future phone-oriented improvements such as a primary redistribution action, a more compact header, and phone-specific Audit summaries should be evaluated separately rather than bundled into this change.
