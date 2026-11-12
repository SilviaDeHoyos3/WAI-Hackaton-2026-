"""Opt-in live acceptance. Prompts for key; saves no credentials or raw CSVs."""
import getpass
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from importlib.metadata import version

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from freshwise.application_tools import load_application_data, context_for_meal, invoke
from freshwise.conversation_agent import PreparationAgent, GeminiClient, ADJUSTED


def main():
    print('FreshWise full live acceptance — Centre 13 / Meal 1198')
    print('Up to 4 Gemini requests. No automatic retries. No evaluation run. No key saved.')
    key = getpass.getpass('Gemini API key (hidden): ').strip()
    if not key:
        print('Cancelled.')
        return
    context = context_for_meal(13, 1198, load_application_data())
    agent = PreparationAgent(context, GeminiClient(key))
    messages = []
    checks = {}
    def send_case(name, text):
        print(f'\n{name}: {text}', flush=True)
        reply = agent.send(text)
        print(reply['answer'], flush=True)
        messages.append({'case': name, 'message': text, 'reply': reply['answer'], 'status': reply['status']})
        if reply['status'] == 'error':
            raise RuntimeError(f'{name} failed ({reply.get("error_code")}). No automatic retry.')
        return reply
    try:
        send_case('1. Real preparation', 'I have 20 portions ready to use. How many more should I make?')
        manual = invoke('central_preparation_recommendation', {'usable_stock': 20}, context=context)
        checks['central_matches_manual'] = agent.pending_plan == manual['result']
        checks['initial_requires_confirmation'] = agent.active_plan is None
        if not all(checks.values()):
            raise RuntimeError('Initial tool/confirmation check failed.')
        agent.confirm()
        original = dict(agent.active_plan)
        trace_count = len(agent.trace)
        reply = send_case('2. Missing event estimate', 'There is a local event. I have not estimated the orders yet.')
        checks['missing_estimate_asks_question'] = (
            'about how many orders do you expect for this dish next week' in reply['answer'].lower()
            and agent.estimate is None and len(agent.trace) == trace_count)
        send_case('3. Manager estimate', 'I think we will get 600 orders for this dish next week.')
        checks['estimate_recorded'] = agent.estimate == 600
        print('\n4. Choosing Small change (25%)...', flush=True)
        reply = agent.choose_weight('Small change')
        print(reply['answer'], flush=True)
        messages.append({'case': '4. Small change', 'message': 'Small change', 'reply': reply['answer'], 'status': reply['status']})
        manual_adjusted = invoke(ADJUSTED, {'usable_stock': 20, 'manager_estimate': 600, 'opinion_weight': .25}, context=context)
        checks['adjustment_matches_manual'] = agent.pending_plan == manual_adjusted['result']['adjusted_plan']
        checks['active_unchanged_before_confirmation'] = agent.active_plan == original
        if not checks['adjustment_matches_manual']:
            raise RuntimeError('Adjustment tool check failed; see trace.')
        pending = dict(agent.pending_plan)
        agent.confirm()
        checks['confirmation_applies_preview'] = agent.active_plan == pending and agent.pending_plan is None
        print('\nCHECKS:', json.dumps(checks, indent=2))
        print('PASS: complete live flow.' if all(checks.values()) else 'REVIEW NEEDED: at least one check did not pass.')
    except Exception as exc:
        # Only controlled local messages; do not print headers or raw provider bodies.
        print('STOPPED:', str(exc).replace(key, '[REDACTED]'))
        checks['completed_without_error'] = False
    report = {
        'executed_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Live Gemini conversation with real local forecast and decision tools; no final evaluation rerun',
        'model': agent.client.model, 'forecast_record': context.forecast_record,
        'checks': checks, 'all_checks_pass': bool(checks) and all(checks.values()),
        'messages': messages, 'tool_calls': agent.trace,
        'runtime': {'python': sys.version.split()[0],
                    'packages': {n: version(n) for n in ['numpy', 'pandas', 'scikit-learn', 'streamlit']}},
        'source_sha256': {name: hashlib.sha256((ROOT / 'src/freshwise' / name).read_bytes()).hexdigest()
                          for name in ['conversation_agent.py', 'application_tools.py', 'agent_tools.py', 'agent_data_tools.py']},
    }
    folder = ROOT / 'outputs'; folder.mkdir(exist_ok=True)
    output = folder / 'agent_live_acceptance.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'\nNo-key report saved: {output}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nCancelled.')
