# Streamlit Community Cloud deployment

The simulator is designed to run as a normal browser app on Streamlit Community Cloud, with GitHub `main` as the source of truth.

## One-time deployment settings

Use these values when creating the app in Streamlit Community Cloud:

- Repository: `VasPappas/econ-agent-sim`
- Branch: `main`
- Entrypoint file: `app/streamlit_app.py`
- Python: `3.11`
- Suggested app subdomain: `econ-agent-sim` if available
- Secrets: none required

Because the repository is public, the deployed app can be public as well.

## Dependencies

Community Cloud reads `requirements.txt` from the repository root. That file installs the project together with its `app` extra. The Streamlit version is pinned in `pyproject.toml` so browser deployment and Codespaces use the same declared app dependency.

## Update behavior

After the first deployment, `main` remains authoritative. Changes merged into `main` are picked up by Streamlit Community Cloud automatically. Dependency changes trigger a redeploy.

## After first deployment

Copy the permanent `*.streamlit.app` URL into the root README so the simulator can be opened directly from a tablet or any other browser without using GitHub or Codespaces.
