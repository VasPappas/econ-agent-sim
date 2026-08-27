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

Community Cloud reads `requirements.txt` from the repository root. That file installs the project together with its `app` extra. The Streamlit version is pinned in `pyproject.toml` so browser deployment and Codespaces use the same declared app dependency.

## Update behavior

`main` remains authoritative. Changes merged into `main` are picked up by Streamlit Community Cloud automatically. Dependency changes trigger a redeploy.
