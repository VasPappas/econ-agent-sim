"""Local-only visual harness for the real component and engine, without Streamlit.

Run: PYTHONPATH=src python tools/preview_playground.py
Open http://127.0.0.1:8765. Each tab holds its own development scenario.
This is NOT the deployed app or a replacement for Streamlit integration tests.
"""

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from econ_agent_sim.economy_0_2 import ExchangeAgentConfig, canonical_population
from econ_agent_sim.economy_0_4 import Economy04Config, run_economy_0_4
from econ_agent_sim.playground import apply_transfer, playground_data

ASSETS = Path(__file__).parents[1] / "src/econ_agent_sim/playground_component"
HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Economy playground — local development preview</title>
<style>body{margin:0;background:#e8ebe4;font-family:system-ui}
main{max-width:414px;margin:20px auto;padding:0 8px}
header{font-size:12px;color:#52646a;margin:12px 0}</style>
<main><header>Economy 0.4 · component development preview</header><div id="host"></div></main>
<script type="module">
import render from '/component.js';
const host=document.querySelector('#host').attachShadow({mode:'open'});
const style=document.createElement('style'); style.textContent=await (await fetch('/styles.css')).text();
const root=document.createElement('div'); root.className='playground-root';host.append(style,root);
let config, data, cleanup;
const initial=await (await fetch('/initial')).json(); config=initial.config; data=initial.data;
function draw(){cleanup?.();cleanup=render({parentElement:host,data,setTriggerValue:async(name,action)=>{
  const response=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({config,revision:data.revision,action})});
  const next=await response.json();if(next.config)config=next.config;
  data=next.data||{...data,error:next.error};draw();
}})}draw();
</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def reply(self, content, content_type="application/json", status=200):
        raw = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            return self.reply(HTML, "text/html; charset=utf-8")
        if self.path in ("/styles.css", "/component.js"):
            mime = "text/css" if self.path.endswith("css") else "text/javascript"
            return self.reply((ASSETS / self.path[1:]).read_text(), mime)
        if self.path == "/initial":
            config = Economy04Config(period_populations=(canonical_population(),))
            result = run_economy_0_4(config)
            return self.reply(
                json.dumps(
                    {"config": asdict(config), "data": playground_data(result, 0, 0)}
                )
            )
        self.reply("Not found", "text/plain", 404)

    def do_POST(self):
        if self.path != "/run":
            return self.reply("Not found", "text/plain", 404)
        size = int(self.headers.get("Content-Length", "0"))
        if size > 100_000:
            return self.reply("Request too large", "text/plain", 413)
        try:
            body = json.loads(self.rfile.read(size))
            raw = body["config"]
            populations = tuple(
                tuple(ExchangeAgentConfig(**a) for a in p)
                for p in raw.pop("period_populations")
            )
            updated = apply_transfer(populations[-1], body["action"], body["revision"])
            config = Economy04Config(period_populations=(*populations, updated), **raw)
            result = run_economy_0_4(config)
            payload = playground_data(
                result, len(result.periods) - 1, body["revision"] + 1, body["action"]
            )
            self.reply(json.dumps({"config": asdict(config), "data": payload}))
        except (ValueError, TypeError, KeyError, RuntimeError, AssertionError) as error:
            self.reply(json.dumps({"error": str(error)}), status=400)


if __name__ == "__main__":
    print("Local preview: http://127.0.0.1:8765", flush=True)
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
