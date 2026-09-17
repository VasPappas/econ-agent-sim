# Using Tiny Economy

The root URL opens one workspace with **Set up**, **Results** and **Ask why**.
There is no version catalogue or chapter sidebar.

## Set up

Use **Starting experiments** to choose and explicitly apply a preset. It replaces
the editable draft, not completed results or a saved baseline. All presets use
the same two-firm model; they do not reproduce the retired two-good economies.

Households have starting money, three relative priority scores and a soft
consumption target. Equal scores mean equal utility weights, not equal realized
spending or time. Increasing one score raises its relative weight; normalization
is automatic. The target is an amount of X per period, not a guaranteed minimum.
The explicit copy action copies Household 1's priorities and target to the other
households, leaving their starting money alone.

Firms have starting cash, capital, productivity, investment policy and capital
wear. Their cash funds wages independently. The setup shows starting totals and
keeps optional detail in disclosures.

Run starts a new history from the draft. Returning to setup keeps the draft;
changing it does not change completed results.

## Results and Ask why

Advance one or ten periods using the submitted setup. Select a completed period
and report range. Cumulative means flows summed at their historical period prices,
opening stocks from the beginning and closing stocks from the selected period.
Price and wage remain selected-period rates.

Compact summaries come first. Open statements, transactions and technical checks
when needed. Firms are selectable; households show their submitted priorities.
Consolidated accounts eliminate household claims on firm equity.

Ask why uses the selected period and report range. Built-in explanations require
no AI requests. Optional chat sends the current report, recent conversation and
question to OpenAI only when the user submits a question.

## Experiment controls

- Save the current run as a baseline, then edit a copy for a comparison.
- Download the current experiment and optional baseline as JSON.
- Open a supported file; replay and validation finish before state is replaced.
- Reset explicitly to the default draft and remove the current history. A saved
  baseline remains available; use Clear baseline to remove it. Downloaded files are untouched.

There is no account database. Download before leaving if you want to preserve an
experiment. Current files use format 4, model tiny_economy and engine
tiny-economy-2.0.0. Historical files are identified as incompatible; old models
are available through Git history, not active pages.
