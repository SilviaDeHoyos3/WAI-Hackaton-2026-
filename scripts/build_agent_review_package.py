"""Create a review ZIP from explicit code/docs paths; exclude keys/data/envs."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
files = []
for folder in ['src', 'tests', 'assets']:
    files += [p for p in (ROOT / folder).rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.csv'}]
for name in ['AGENT_START_HERE.md', 'agent_lan_demo.py', 'app.py', 'pyproject.toml',
             'requirements-demo-repro.txt', '.gitignore', 'AGENT_TOOLS.md', 'AGENT_ACCEPTANCE_TESTS.md',
             'run_agent_demo.command', 'run_agent_acceptance.command',
             'docs/LAN_AI_AGENT_HANDOFF.md', 'docs/AI_PRESENTATION_GUIDE.md',
             'scripts/check_agent_live.py', 'scripts/check_agent_offline.py',
             'scripts/build_agent_review_package.py']:
    files.append(ROOT / name)
live = ROOT / 'outputs/agent_live_acceptance.json'
report = json.loads(live.read_text()) if live.is_file() else None
live_matches = bool(report and report.get('all_checks_pass') and all(
    hashlib.sha256((ROOT / 'src/freshwise' / name).read_bytes()).hexdigest() == expected
    for name, expected in report['source_sha256'].items()))
manifest = {'scope': 'Lan AI review package; no key or raw CSV included',
            'verification': '127 unit tests; current offline UI flow passes. Recorded full live flow belongs to the report source hashes; retest this UI before presentation.',
            'live_report_matches_current_sources': live_matches,
            'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
output = ROOT.parent / 'agent_lan_demo.zip'
with ZipFile(output, 'w', ZIP_DEFLATED) as z:
    for p in files:
        z.write(p, Path('agent_lan_demo') / p.relative_to(ROOT))
    z.writestr('agent_lan_demo/PACKAGE_MANIFEST.json', json.dumps(manifest, indent=2))
    evidence = ROOT / 'outputs/agent_offline_acceptance.json'
    if evidence.is_file():
        z.write(evidence, 'agent_lan_demo/docs/AGENT_OFFLINE_ACCEPTANCE.json')
    if live.is_file():
        assert report.get('all_checks_pass') is True
        z.write(live, 'agent_lan_demo/docs/AGENT_LIVE_ACCEPTANCE.json')
with ZipFile(output) as z:
    assert z.testzip() is None
    assert all(not n.endswith(('.csv', '.pyc', '.env')) and '/.venv' not in n for n in z.namelist())
    print(f'Verified {len(z.namelist())} package entries: {output}')
