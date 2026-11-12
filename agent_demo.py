"""Compatibility entry point; main UI is agent_lan_demo.py."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("agent_lan_demo.py")), run_name="__main__")
