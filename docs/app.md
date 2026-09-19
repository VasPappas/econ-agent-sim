# Using Tiny Economy

Use the root [Streamlit app](https://econ-agent-sim.streamlit.app/). The three
views are **Set up**, **Results** and **Ask why**.

## Start an experiment

Set up offers six controls: future importance, capital wear, leisure preference,
money preference, capital per firm, and the share of money held by firms.
Two identical households and two identical firms are fixed. Percentages are
shown for patience, wear and the initial cash split.

Choose a starting experiment and press **Use this setup** to populate the draft.
The growing, capital-abundant, capital-scarce, tight-cash and stationary presets
illustrate different paths of the same model. Selecting a title alone changes
nothing. **Start new simulation** validates a complete plan and reveals period 1.
An unsupported or failed solve keeps the existing run and baseline intact.

Draft edits survive navigation and do not change completed results. Start again
to apply edits. An existing run continues with its submitted settings.

## Explore results

**Next period** and **+10 periods** reveal more of one accepted plan, up to 100
periods. They do not revise prior choices. The solver checks a longer
continuation beyond the displayed window; there is no forced sale of ending capital.

Select a completed period and choose **This period** or **Cumulative**. Production,
consumption and investment cover that range; capital and cash are closing stocks.
Cumulative money flows retain their original prices. Work and leisure percentages
are averages. Prices and wages are labeled with the selected period.

Household and firm tables show physical activity, cash and ownership accounts.
Expand the account bridges for wages, dividends, sales, investment, wear, profit
and capital revaluation. Trends show production, capital, prices and work through
the selected period. CSV export contains all revealed periods at full precision.
**Ask why** gives deterministic explanations grounded in the same run and accounts.

## Save, open and compare

The **Save, open and compare experiments** panel can:

- Download the draft, current run and optional baseline as JSON.
- Open a compatible file after independent replay and validation.
- Save the current run as an independent baseline, or copy its setup into the draft.
- Compare the same completed period or cumulative range in both runs.
- Reset to the default draft while retaining a saved baseline.

Experiments exist only in the current session until downloaded. Current files use
format 6, model `tiny-economy-monetary-1`, engine `tiny-economy-4.0.0`. Files from
the previous model are incompatible and leave the workspace unchanged. Restart
with the six current settings; older outcomes are not automatically converted.

The model's assumptions and unsupported cash-retention regime are explained in
**How this economy works** and the [model guide](model.md).
