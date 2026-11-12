#!/bin/zsh
cd -- "${0:A:h}"
export PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1
task_python=python3
[[ -x .venv/bin/python ]] && task_python=.venv/bin/python
[[ -x .venv-repro/bin/python ]] && task_python=.venv-repro/bin/python
"$task_python" scripts/check_agent_live.py
echo
read -r "reply?Press Enter to close."
