# Optional experiment assistant

Built-in explanations are always available without an AI request.
The optional assistant explains the current canonical report and comparison,
not draft edits. It cannot change settings, run simulations or call tools.

Set these in Streamlit Community Cloud app settings → Secrets:

```toml
OPENAI_API_KEY = "your-key"
ECON_CHAT_ENABLED = "true"
OPENAI_MODEL = "gpt-4.1-mini"
ECON_CHAT_DAILY_LIMIT = "100"
```

Do not commit the actual key. API usage is billed separately from a ChatGPT
subscription. The configured model name is passed to the API; model availability
depends on the app owner's API access.

The UI tells users that submitting sends run data, recent conversation and their
question to OpenAI. Requests set store=false, have no tools, cap question/context/
history/output size, use a timeout and never automatically retry billable calls.
Output is rendered as plain text, not model-supplied HTML, links or images.

A small server-local SQLite request counter provides an atomic shared daily
allowance, per-session cap and cooldown. It is not a simulation database and is
not durable billing enforcement across server resets or multiple server instances.
Workspace Reset does not renew the current browser session's allowance identity.
Provider error details and secrets are not shown to users.

Conversations are bounded and keyed to selected report context. Results and
accounts remain authoritative; AI answers can be mistaken.
