# Streamlit Community Cloud deployment

[Live app](https://econ-agent-sim.streamlit.app/) uses repository
`VasPappas/econ-agent-sim`, branch `main`, entrypoint
`app/streamlit_app.py`, Python 3.11 and subdomain `econ-agent-sim`.

No API keys or other secrets are needed for the simulator or built-in explanations.

Community Cloud reads root `requirements.txt`, which installs the project with
its app extra. Streamlit and its server dependency are pinned in pyproject.toml.
CI installs the same dependencies, runs Ruff, Python and JavaScript tests, then
starts a real Streamlit server and checks its health endpoint.

## Release checks

1. Run engine/accounting, report, persistence and UI tests before publishing.
2. Recheck the remote branch before updating; never force-overwrite user changes.
3. Update the requirements rebuild marker with a coordinated cross-module release.
   This requests a fresh Cloud rebuild instead of relying solely on page hot reload.
4. Verify CI, deployment and actual app interactions after publishing. A healthy
   server alone does not establish that every UI route works.
5. Review the root URL on a narrow screen, including setup, run, cumulative
   results, firm selection, explanations, download/open and reset.

## Single-app migration

Retired chapter routes and sidebar pages are removed. Existing bookmarks should
use the root URL. Users should refresh after deployment; pre-release in-memory
sessions are not migrated. New files use format 5 / engine 3.0.0. Released
format-4 / engine-2.0.0 percentage files migrate after their original replay
digests verify. Older files fail with a clear compatibility message.

Source recovery is available through Git history. Retired engines and tests are
not kept in the active deployment.
