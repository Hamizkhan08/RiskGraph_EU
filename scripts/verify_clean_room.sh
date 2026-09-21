#!/bin/sh
# Clean-room verification: usage  sh scripts/verify_clean_room.sh RiskGraph_EU_FINAL.zip  (needs python3, node>=20.9, network for pip/npm). Set WORK_DIR to choose the scratch dir.
ZIP=$(realpath "$1"); W=${WORK_DIR:-$(mktemp -d)}; rm -rf "$W" && mkdir -p "$W" && cd "$W"
step() { echo "[$(date +%H:%M:%S)] $*"; }
unzip -q "$ZIP" -d . && cd RiskGraph_EU && step "EXTRACT ok ($(find . -type f | wc -l) files)"
python3 -m venv $W/venv_full && . $W/venv_full/bin/activate
pip install -q -r requirements.txt > $W/pip_full.log 2>&1 && step "PIP full requirements ok" || { step "PIP full FAILED"; tail -5 $W/pip_full.log; exit 1; }
ruff check . > $W/ruff.log 2>&1 && step "RUFF ok" || { step "RUFF FAILED"; tail -5 $W/ruff.log; }
mypy riskgraph backend/app scripts --ignore-missing-imports --explicit-package-bases > $W/mypy.log 2>&1 && step "MYPY ok" || { step "MYPY FAILED"; tail -5 $W/mypy.log; }
python -m pytest -q --junitxml=$W/junit.xml > $W/pytest.log 2>&1 && step "PYTEST ok: $(tail -1 $W/pytest.log)" || { step "PYTEST FAILED"; tail -15 $W/pytest.log; }
python - <<PY
import xml.etree.ElementTree as ET
r=ET.parse("$W/junit.xml").getroot(); s=r if r.tag=="testsuite" else r.find("testsuite")
print("   pytest counts:", {k:s.attrib[k] for k in ("tests","failures","errors","skipped")})
PY
deactivate
# --- Dockerfile import-closure simulation: ONLY backend/requirements.txt deps + the files the Dockerfile COPYs ---
python3 -m venv $W/venv_api && . $W/venv_api/bin/activate
pip install -q -r backend/requirements.txt > $W/pip_api.log 2>&1 && step "PIP api-only requirements ok" || { step "PIP api FAILED"; tail -5 $W/pip_api.log; exit 1; }
C=$W/closure && mkdir -p $C/backend $C/riskgraph $C/artifacts && cp -r backend/app $C/backend/app && cp riskgraph/__init__.py riskgraph/config.py riskgraph/decision.py riskgraph/reasons.py $C/riskgraph/ && cp -r artifacts/demo $C/artifacts/demo
cd $C && (RISKGRAPH_BUNDLE_DIR=$C/artifacts/demo RISKGRAPH_DB_PATH=/tmp/closure.db RISKGRAPH_CORS_ORIGINS=https://example.vercel.app setsid nohup uvicorn backend.app.main:create_app --factory --port 8011 > $W/closure_api.log 2>&1 < /dev/null &)
sleep 12
curl -fsS localhost:8011/health | head -c 120 && echo && step "CLOSURE health ok" || { step "CLOSURE health FAILED"; tail -8 $W/closure_api.log; }
curl -fsS -X POST localhost:8011/api/simulate -H 'Content-Type: application/json' -d '{"dataset":"HI","policy":"conformal","alpha":0.1,"capacity_multiplier":1.0}' | python3 -c "import sys,json;j=json.load(sys.stdin);print('   simulate HI conformal miss',round(j['realised_miss_rate'],3),'CI',[round(x,3) for x in j['miss_ci95']])" && step "CLOSURE simulate ok"
python3 - <<PY
import json,urllib.request
d=json.load(open("$C/artifacts/demo/LI/case_details.json")); cid=next(iter(d))
r=urllib.request.urlopen(urllib.request.Request("http://localhost:8011/api/predict?dataset=LI",json.dumps({"features":d[cid]["features"]}).encode(),{"Content-Type":"application/json"}))
j=json.load(r); print("   predict", round(j["score"],4), "stored", round(d[cid]["score"],4), "match", abs(j["score"]-d[cid]["score"])<1e-6)
PY
curl -s -o /dev/null -w "   CORS preflight allowed-origin echoed: " -X OPTIONS localhost:8011/api/alerts -H "Origin: https://example.vercel.app" -H "Access-Control-Request-Method: GET" -D - | grep -i "access-control-allow-origin" || echo "(missing!)"
pkill -f "uvicorn backend.app.main:create_app --factory --port 8011"; deactivate
# --- frontend from the ZIP: npm ci + lint + typecheck + test + build ---
cp -r $W/RiskGraph_EU/frontend $W/fe && cd $W/fe
npm ci > $W/npm_ci.log 2>&1 && step "NPM ci ok" || { step "NPM ci FAILED"; tail -8 $W/npm_ci.log; exit 1; }
npm run lint > $W/fe_lint.log 2>&1 && step "FE lint ok" || { step "FE lint FAILED"; tail -8 $W/fe_lint.log; }
npm run typecheck > $W/fe_tsc.log 2>&1 && step "FE typecheck ok" || { step "FE typecheck FAILED"; tail -8 $W/fe_tsc.log; }
npm test > $W/fe_test.log 2>&1 && step "FE tests ok: $(grep -E 'Tests ' $W/fe_test.log | tail -1 | sed 's/\x1b\[[0-9;]*m//g')" || { step "FE tests FAILED"; tail -15 $W/fe_test.log; }
npm run build > $W/fe_build.log 2>&1 && step "FE build ok" || { step "FE build FAILED"; tail -12 $W/fe_build.log; }
step "ALL STEPS FINISHED"
