#!/bin/zsh
cd -- "${0:A:h}"
export PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1
task_python=python3
[[ -x .venv/bin/python ]] && task_python=.venv/bin/python
[[ -x .venv-repro/bin/python ]] && task_python=.venv-repro/bin/python
echo 'Open http://127.0.0.1:8504. Enter the API key only in the local sidebar.'
"$task_python" -m streamlit run agent_lan_demo.py --server.address 127.0.0.1 --server.port 8504 --server.headless true --browser.gatherUsageStats false
