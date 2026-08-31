# Streamlit Community Cloud deployment

The simulator runs as a normal browser app on Streamlit Community Cloud, with GitHub `main` as the source of truth.

## Live app

Permanent URL: https://econ-agent-sim.streamlit.app

This URL is the preferred way to use the simulator from a tablet, phone, or desktop browser without opening GitHub or Codespaces.

## Deployment settings

- Repository: `VasPappas/econ-agent-sim`
- Branch: `main`
- Entrypoint file: `app/streamlit_app.py`
- Python: `3.11`
- App subdomain: `econ-agent-sim`
- Secrets: none required

Because the repository is public, the deployed app can be public as well.

## Dependencies

Community Cloud reads `requirements.txt` from the repository root. That file installs the project together with its `app` extra. Streamlit is pinned to `1.62.0`, and Starlette is pinned to `1.6.0`, so Community Cloud cannot resolve an older incompatible Starlette server build during a fresh redeploy.

CI installs the same app dependencies and now starts a real Streamlit server and checks its health endpoint after linting and tests. This catches server-startup failures that an in-process Streamlit `AppTest` alone would not detect.

## Update behavior

`main` remains authoritative. Changes merged into `main` are picked up by Streamlit Community Cloud automatically. Dependency changes trigger a redeploy.

Community Cloud may hot-reload a changed Streamlit page while keeping already-imported project modules in memory. Therefore, when a page starts calling a changed Python API signature from `src/econ_agent_sim`, the deployment must also trigger a clean rebuild rather than rely on hot reload. In this project, touching the rebuild marker comment in `requirements.txt` is the explicit mechanism for that clean rebuild. This prevents a new page from calling an older cached module interface.
