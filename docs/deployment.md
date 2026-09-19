# Streamlit Community Cloud deployment

[Live app](https://econ-agent-sim.streamlit.app/) uses repository
`VasPappas/econ-agent-sim`, branch `main`, entrypoint
`app/streamlit_app.py`, Python 3.11 and subdomain `econ-agent-sim`.
No API keys or other secrets are needed for the simulator or explanations.

Root `requirements.txt` installs the project's app extra. Streamlit and Starlette
are pinned in `pyproject.toml`. CI installs the same dependencies, runs Ruff and
Python tests including Streamlit AppTest, then starts a real server and checks
its health endpoint.

## Release checks

1. Run economic, settlement, reporting, persistence and UI tests.
2. Recheck the remote branch before publishing; preserve unrelated changes.
3. Update the requirements rebuild marker for coordinated cross-module releases.
4. Verify CI and actual live controls/results after merging. Server health alone
   does not establish that the correct app release is running.
5. Check setup, stepping, cumulative views, explanations and baseline comparison;
   verify phone layout and saved-file compatibility.

## Monetary model migration

There is one app and one maintained model. New files use format 6,
model `tiny-economy-monetary-1`, engine `tiny-economy-4.0.0`. Previous model files
are rejected explicitly and atomically. They are not replayed under changed
economics. In-memory sessions from the old model reset with an explanation.
Refresh the browser after deployment if an old interface is still visible.

Git history provides source recovery. Retired engines, policy controls and
custom presentation components are removed from the active deployment.
