#!/bin/zsh
set -eu
cd "$(dirname "$0")"
if [[ -x .venv-repro/bin/python ]]; then
  preview_python=.venv-repro/bin/python
elif [[ -x .venv/bin/python ]]; then
  preview_python=.venv/bin/python
elif [[ -x ../WAI-Hackaton-2026--main/.venv/bin/python ]]; then
  preview_python=../WAI-Hackaton-2026--main/.venv/bin/python
else
  echo "Please follow LAN_START_HERE.md to install the project and demo extra."
  read -r "reply?Press Enter to close."
  exit 1
fi
exec "$preview_python" -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
