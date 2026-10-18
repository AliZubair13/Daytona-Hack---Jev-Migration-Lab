"""Build a static, publishable snapshot of the UI (docs/index.html) for GitHub Pages.

Embeds /api/state and every cell timeline for one stored run, and answers the page's fetch calls from that data.
Usage: python build_static.py [run_id]   (default: the Arize-verified run)
"""
import json
import sys

import server

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "run_91c521692c"
REPO = "https://github.com/Vanshika2021/jev-or-nah"

run = server._load_run(RUN_ID)
state = server.state()
state["latest_run"] = server._summary(run)
cells = {f"/api/run/{RUN_ID}/cell/{a['id']}/{c['id']}": server.cell(RUN_ID, a["id"], c["id"])
         for a in run["architectures"] for c in state["cases"]}

shim = """<script>
window.__SNAPSHOT__ = %s;
(function () {
  const D = window.__SNAPSHOT__, realFetch = window.fetch;
  const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "Content-Type": "application/json" } });
  window.fetch = async (url, opts = {}) => {
    const u = String(url).split("?")[0];
    if (u === "/api/state") return json(D.state);
    if (u in D.cells) return json(D.cells[u]);
    if (u === "/api/run") return new Response("This is a published snapshot of a measured run (all 6 architectures ran in Daytona). Live runs need the local server and API keys: " + D.repo, { status: 409 });
    return realFetch(url, opts);
  };
  document.addEventListener("DOMContentLoaded", () => {
    const b = document.createElement("div");
    b.className = "snapbar";
    b.innerHTML = 'Published snapshot of a measured run (<code>' + D.run_id + '</code>, all architectures ran in Daytona). Code and live runs: <a href="' + D.repo + '">' + D.repo.replace("https://", "") + '</a>';
    document.querySelector("main").prepend(b);
  });
})();
</script>
<style>.snapbar { font-size: 15px; color: var(--ink-2); background: var(--surface-2); border: 1px solid var(--line); border-radius: 10px;
  padding: 10px 14px; margin-bottom: 18px; } .snapbar a { color: var(--bar); }</style>
""" % json.dumps({"state": state, "cells": cells, "run_id": RUN_ID, "repo": REPO}).replace("</", "<\\/")

html = (server.lab.ROOT / "static" / "index.html").read_text()
html = html.replace("</head>", shim + "</head>", 1)
out = server.lab.ROOT / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html)
(out.parent / ".nojekyll").write_text("")
print(f"wrote {out} ({len(html) // 1024} KB) for {RUN_ID}")
