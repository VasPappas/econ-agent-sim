# Ask about this experiment

Economy 0.4 has a dedicated **Ask** view and buttons in the playground to ask about
the whole experiment or the displayed trade. The selected trade is validated in
Python and all context comes from the actual model result. Opening chat does not
call OpenAI; only sending a question or selecting a suggested question does.

## Activation on Streamlit Community Cloud

In the existing app's **Settings → Secrets**, add these top-level TOML settings
alongside any existing settings. Replace the placeholder privately in Streamlit:

```toml
OPENAI_API_KEY = "your-key-goes-here"
ECON_CHAT_ENABLED = true
OPENAI_MODEL = "gpt-4.1-mini"
ECON_CHAT_DAILY_LIMIT = 100
```

The OpenAI API project must have billing and access to the selected model. API
usage is paid by the key owner. Do not paste keys into chat, public source code,
issues, or PRs. The key is read only on the Python server from environment variables
or Streamlit secrets. With no key or without the enabled flag, the chat controls
are disabled with an honest unavailable message; the simulator still works.
Set `ECON_CHAT_ENABLED = false` to stop new requests without changing code.

Official setup: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

## Context and behavior

- Selected experiment settings, agent preferences, opening/closing stocks, desired
  bundles, trades, actual prices, clearing error and preceding-experiment price and
  Y-endowment differences are sent with the question. The latest editor population
  is never substituted for a selected historical experiment.
- Trade focus includes both its ordinal within the experiment and its ledger ID.
- Y is explicitly fixed at 1. Money settles trades but does not enter utility or
  impose a purchasing constraint. Experiments do not carry balances forward.
- The assistant is instructed to explain calculated results, identify model rules
  and uncertainty, and suggest manual experiments for uncomputed counterfactuals.
  It has no tools and cannot change the simulation. Grounding and instructions
  reduce mistakes; they do not guarantee explanation accuracy.
- History is session-local and bounded to 20 messages; the last six are sent for
  follow-ups. Changing the experiment data or trade focus clears history. Clearing
  the conversation does not reset the usage allowance.
- Messages are displayed as plain text, without model-generated links, media, or
  HTML. Questions are not automatically sent when opening the view.

## Usage and data controls

- Question limit: 1,200 characters. Context limit: 35,000 characters. History:
  six messages, at most 4,000 characters each. Output: at most 800 tokens.
- API: HTTPS to the fixed `api.openai.com/v1/responses` endpoint, 30-second timeout,
  no redirects, no retries, and `store: false`. This disables Responses storage;
  it is not a promise of zero provider retention under all account policies.
- A SQLite counter in the server's temporary directory atomically limits requests
  across browser sessions: default 100 per rolling 24 hours, 30 per rolling hour,
  20 per session per rolling 24 hours, and five seconds between session requests.
  The owner can set the daily cap from 1 to 1,000. Attempts, including failed API
  requests, consume allowance. Database failure blocks requests rather than
  disabling the limit. It stores only timestamps and random session identifiers.
- Limits are per hosting instance and survive ordinary process reruns while the
  file remains. Deployment/container replacement can reset the file, and replicas
  would each have their own allowance. This is not a permanent account-wide dollar
  cap. Use a dedicated API project and provider spend controls; a larger public
  rollout should use a shared durable quota service and visitor authentication.
- No prompts, responses, or API keys are written to application logs or the quota
  database. Visitors see a notice about sending chat and experiment data to OpenAI.

## Verification and activation check

Automated tests use a mocked HTTPS response, never a real API key. They cover
selected-versus-latest experiment context, trade-event validation, concurrency and
quota limits, input limits, response parsing, safe API errors, disabled chat,
follow-ups, context changes, and unchanged simulation state.

After adding the key, test a real question on Baseline, redistribute 0.10 Y, open
**Ask about this trade**, and ask why X changed but Y did not. Confirm that the
answer uses the displayed experiment and trade and does not claim to run a new
simulation. Live model accuracy and connectivity still require this activation
check; mocked tests do not establish them.
