"""Exercise real menu -> HGB forecast -> central tools inside Streamlit.
This is next-week planning, not evaluation or an AI conversation test.
"""
from pathlib import Path
import json
import math
import hashlib
import sys
from importlib.metadata import version
from datetime import datetime, timezone
from streamlit.testing.v1 import AppTest
root = Path(__file__).resolve().parents[1]
app = AppTest.from_file(str(root/'app.py'), default_timeout=180).run()
app.radio(key='data_mode').set_value('Real next-week forecast').run()
assert not app.exception, str(app.exception)
assert app.session_state['current_response'] is None
app.button(key='load_forecast').click().run(timeout=180)
assert not app.exception, str(app.exception)
context = app.session_state['live_context']
assert context.forecast_record['center_id'] == 13
assert context.forecast_record['meal_id'] == 1198
assert context.forecast_record['method_requested'] == 'hgb'
assert context.forecast_record['target_week'] == 146
assert context.forecast_record['history_end_week'] == 145
assert app.session_state['current_response']['status'] == 'needs_input'
app.number_input(key='real_stock_13_1198').set_value(20).run()
base = app.session_state['current_response']
assert base['tool_call']['name'] == 'central_preparation_recommendation'
assert base['tool_call']['application_arguments']['forecast'] == context.forecast_record['forecast_orders']
assert base['result']['new_portions_to_prepare'] == max(0,math.ceil(context.forecast-20))
history_html = "\n".join(element.proto.body for element in app.tabs[1].get("html"))
assert ">166</strong>" in history_html and ">15</strong>" in history_html
assert "151 fewer portions wasted" in history_html and "91%</strong> less food waste" in history_html
assert "116 fewer orders missed" in history_html and "39 more orders missed" in history_html
app.number_input(key="impact_portion_cost").set_value(3.50).run()
assert any("CA$528.50" in element.proto.body for element in app.tabs[1].get("html"))
assert 'class="history-heatmap"' in history_html and 'Waste, weeks 1 to 145' in history_html
assert history_html.count('class="heat-value"') + history_html.count('class="heat-missing"') == 145
assert history_html.count('class="demand-bar"') == 1
assert 'Your plan covers up to <strong>454</strong>' in history_html
assert 'What if orders change?' in history_html
assert 'orders short' not in history_html and 'portions left over' not in history_html
assert not any("Next week’s prep outlook" in element.proto.body for element in app.tabs[0].get("html"))
app.radio(key="history_metric").set_value("Missed orders").run()
assert any("Missed orders, weeks 1 to 145" in element.proto.body for element in app.tabs[1].get("html"))
app.number_input(key='estimate').set_value(600.0).run()
app.radio(key='adjustment_choice').set_value('Small change').run()
adjusted = app.session_state['current_response']
assert adjusted['tool_call']['name'] == 'manager_adjusted_central_recommendation'
assert adjusted['result']['adjusted_plan']['new_portions_to_prepare'] == max(0,math.ceil(.75*context.forecast+.25*600-20))
assert 'applied_plan' not in app.session_state
app.button(key='apply_adjustment').click().run()
assert app.session_state['applied_plan'] == adjusted
app.radio(key='impact_population').set_value('All meals').run()
assert app.session_state['applied_plan'] == adjusted
selector = app.selectbox(key='meal_13')
selector.select_index(0 if selector.index != 0 else 1).run()
assert app.session_state['current_response'] is None
assert 'applied_plan' not in app.session_state
assert not app.exception, str(app.exception)
assert not any("Next week’s prep outlook" in element.proto.body for element in app.tabs[1].get("html"))
report = {'executed_at_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'Real data and tools in Streamlit; no LLM; no evaluation run',
          'forecast':context.forecast_record,'central_response':base,'manager_response':adjusted,
          'missing_stock_input':'PASS','preview_and_apply':'PASS','meal_change_invalidates_plan':'PASS'}
from freshwise.application_tools import resolve_data_dir, DATA_FILES
report['runtime'] = {'python': sys.version, 'packages': {name: version(name) for name in
    ['numpy', 'pandas', 'scikit-learn', 'scipy', 'streamlit']}}
report['data_sha256'] = {name: hashlib.sha256((resolve_data_dir()/name).read_bytes()).hexdigest()
                         for name in DATA_FILES}
output = root/'outputs/live_application_acceptance.json' 
output.write_text(json.dumps(report,indent=2))
print(f"Real UI/tool checks PASS: forecast={context.forecast!r}, prepare={base['result']['new_portions_to_prepare']}, adjusted={adjusted['result']['adjusted_plan']['new_portions_to_prepare']}. Trace: {output}")
