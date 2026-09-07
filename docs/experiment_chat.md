# Ask about this experiment

Economy 0.4 has a dedicated **Ask why** view with a focus selector for the whole
experiment or a specific trade. The selection is made in Streamlit and all
context comes from the actual model result. Opening chat does not
call OpenAI. Common explanations are deterministic text derived from the selected
model result; opening them never calls OpenAI. Only submitting a typed question
uses the API allowance. Built-in explanations remain available without an API key.

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

- `SubmittedRun.context()` supplies the same prices, agents, totals, changes,
  and trade records shown in Results. Built-in explanations use this context
  too. The selected trade adds focus without replacing the submitted facts.
  There is no separate legacy baseline/period context builder. Ledger IDs
  restart within each run, and the assistant instructions reflect that rule.
- The current submitted run supplies settings, preferences, opening/closing stocks,
  desired bundles, trades, prices and clearing error. Its preceding submitted run
  supplies comparison prices and starting agents. Setup changes include quantities,
  preferences, additions and removals. Unsubmitted draft edits never enter context.
  Each run has its own ledger IDs; there is no cumulative trade numbering across runs.
- Trade focus includes both its ordinal within the experiment and its ledger ID.
- Y is explicitly fixed at 1. Money settles trades but does not enter utility or
  impose a purchasing constraint. Experiments do not carry balances forward.
- The assistant is instructed to explain calculated results, identify model rules
  and uncertainty, and suggest manual experiments for uncomputed counterfactuals.
  It has no tools and cannot change the simulation. Grounding and instructions
  reduce mistakes; they do not guarantee explanation accuracy.
- History is session-local and bounded to 20 messages per context; the last six
  are sent for follow-ups. The 12 most recently visited experiment/trade contexts
  retain separate conversations, restored when returning to the same context.
  Clearing a conversation does not reset the usage allowance.
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
selected-versus-latest experiment context, trade focus, concurrency and
quota limits, input limits, response parsing, safe API errors, disabled chat,
follow-ups, context changes, and unchanged simulation state.

After adding the key, press Run on the symmetric setup and ask why no trade is
needed. Change one agent’s X quantity, press Run again, choose a trade under
**Focus** in Ask why, and ask why X changed but Y did not. Confirm that the
answer uses the displayed experiment and trade and does not claim to run a new
simulation. Live model accuracy and connectivity still require this activation
check; mocked tests do not establish them.
