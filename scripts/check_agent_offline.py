"""Real forecasting and UI, mocked Gemini: never mislabel as live acceptance."""
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from streamlit.testing.v1 import AppTest
from freshwise.application_tools import invoke


class OfflineProvider:
    model = 'OFFLINE-TEST-DOUBLE-NOT-A-LIVE-MODEL'
    def __init__(self):
        self.responses = [
            {'functionCall': {'name': 'central_preparation_recommendation', 'args': {'usable_stock': 20}}},
            {'functionCall': {'name': 'record_manager_estimate', 'args': {'manager_estimate': 600}}},
            {'functionCall': {'name': 'manager_adjusted_central_recommendation', 'args': {}}},
        ]
    def generate(self, payload):
        return {'candidates': [{'content': {'role': 'model', 'parts': [self.responses.pop(0)]}}]}


def main():
    app = AppTest.from_file(str(ROOT / 'agent_lan_demo.py'), default_timeout=120).run()
    app.text_input[0].set_value('offline-placeholder-not-a-key')
    app.button[0].click().run(timeout=120)
    assert not app.exception, app.exception
    agent = app.session_state['agent']
    agent.client = OfflineProvider()
    def chat(text):
        app.chat_input[0].set_value(text).run()
        assert not app.exception, app.exception
    def button(label):
        next(x for x in app.button if x.label == label).click().run()
        assert not app.exception, app.exception
    chat('I have 20 portions ready to use. How many more should I make?')
    manual = invoke('central_preparation_recommendation', {'usable_stock':20}, context=agent.context)
    assert agent.pending_plan == manual['result'] and agent.active_plan is None
    button('Confirm and apply plan')
    original = dict(agent.active_plan)
    chat('There is an event')
    assert agent.estimate is None and len(agent.trace) == 1
    chat('I expect 600 orders')
    button('Small change')
    manual_adjusted = invoke('manager_adjusted_central_recommendation',
                            {'usable_stock':20, 'manager_estimate':600, 'opinion_weight':.25}, context=agent.context)
    assert agent.pending_plan == manual_adjusted['result']['adjusted_plan']
    assert agent.active_plan == original
    adjusted = dict(agent.pending_plan)
    button('Confirm and apply plan')
    assert agent.active_plan == adjusted and agent.pending_plan is None
    chat('Can you guarantee zero waste?')
    assert 'cannot guarantee' in app.session_state['messages'][-1]['text']
    report = {'executed_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'OFFLINE: real forecast, adapter and Streamlit UI; provider responses MOCKED; zero API requests',
              'forecast': agent.context.forecast_record, 'tool_calls':agent.trace,
              'checks': {'central_matches_manual':True,'adjustment_matches_manual':True,
                         'initial_confirmation':True,'adjustment_requires_confirmation':True,
                         'missing_estimate':True,'guarantee_refused_without_provider':True}}
    app.number_input[1].set_value(2444).run()
    assert any('Selection changed' in x.value for x in app.warning)
    assert not app.chat_input
    report['checks']['dish_change_blocks_old_conversation'] = True
    output = ROOT / 'outputs/agent_offline_acceptance.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2))
    print(f"OFFLINE UI PASS: forecast={agent.context.forecast:.8f}; new preparation {original['new_portions_to_prepare']} -> {adjusted['new_portions_to_prepare']}")
    print(f'No live model tested. Report: {output}')


if __name__ == '__main__':
    main()
