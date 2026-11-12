"""Plain conversation handoff screen. AI integration: Lan."""
import os
import base64
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
import streamlit as st
from freshwise.application_tools import load_application_data, context_for_meal
from freshwise.conversation_agent import PreparationAgent, GeminiClient, WEIGHTS, CODE_REVISION

st.set_page_config(page_title='FreshWise | Kitchen assistant', page_icon='🌿', layout='wide')

def logo(name):
    return 'data:image/png;base64,' + base64.b64encode((Path(__file__).parent / 'assets' / name).read_bytes()).decode()

st.html('''<style>
:root{--fw-ink:#203e32;--fw-green:#32634a;--fw-muted:#6b786a;--fw-line:#dde3d6}
.stApp{background:#faf8f2;color:var(--fw-ink)}
[data-testid="stMainBlockContainer"]{max-width:1080px;padding-top:2rem;padding-bottom:5rem}
[data-testid="stSidebar"]{background:#f0f2e8;border-right:1px solid var(--fw-line)}
[data-testid="stHeader"]{background:#faf8f2e8}
.stButton button{border-radius:12px;min-height:44px;border-color:#cfd9c8;color:var(--fw-ink)}
.stButton button[kind="primary"]{background:var(--fw-green);border-color:var(--fw-green);color:white}
.stButton button:hover{border-color:var(--fw-green);color:var(--fw-green)}
.stButton button[kind="primary"]:hover{background:#244f39;color:white}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input{color:var(--fw-ink)}
[data-testid="stChatMessage"]{background:white;border:1px solid #e1e6da;border-radius:18px;padding:20px;margin:10px 0}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){background:#edf2e6;border-color:#dce5d2}
[data-testid="stChatInput"]{border:1px solid #b5c5a6;border-radius:16px;box-shadow:0 5px 22px #23472a08}
[data-testid="stBottom"]>div{background:#faf8f2}
[data-testid="stExpander"]{border-color:#dce3d5;border-radius:14px;background:#fffdf8}
.fw-header{display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid var(--fw-line);padding:0 0 20px;margin-bottom:28px}
.fw-project{width:255px;max-width:58%;height:auto;mix-blend-mode:multiply}
.fw-team{display:flex;align-items:center;gap:10px;font-size:10px;letter-spacing:1.5px;color:var(--fw-muted);text-transform:uppercase}
.fw-team img{width:94px;height:auto}
.fw-kicker{font-size:11px;font-weight:700;letter-spacing:2px;color:#68805c;text-transform:uppercase;margin:0 0 10px}
.fw-heading{font-size:clamp(28px,4vw,42px);letter-spacing:-1.3px;line-height:1.16;margin:0 0 10px;color:var(--fw-ink);font-weight:750}
.fw-subtitle{font-size:15px;color:var(--fw-muted);line-height:1.6;margin:0 0 24px}
.fw-pills{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px}
.fw-pills span{background:#edf0e5;border:1px solid #dfe5d7;padding:6px 12px;border-radius:30px;font-size:12px;color:#4d6447}
.fw-ticket{background:#fffef9;border:1px solid #d9e1cf;border-top:5px solid #3b684e;border-radius:20px;padding:25px 28px;margin:0 0 24px;box-shadow:0 8px 25px #203e3205}
.fw-ticket.pending{background:#fff9ec;border-color:#e6d7b5;border-top-color:#b58c46}
.fw-ticket h2{color:var(--fw-ink);font-size:clamp(26px,3.5vw,38px);line-height:1.2;margin:10px 0 16px;letter-spacing:-.7px;padding:0}
.fw-ticket p{color:#617159;font-size:14px;line-height:1.7;margin:0}
.fw-status{display:inline-block;color:#346347;background:#e9f0df;border-radius:20px;padding:5px 10px;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
.pending .fw-status{color:#886323;background:#f3e7c9}
.fw-numbers{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}
.fw-numbers div{background:#f1f4e9;padding:12px 18px;border-radius:12px;flex:1;min-width:130px}
.fw-numbers strong{font-size:25px;display:block;color:#2d523b}
.fw-numbers small{font-size:12px;color:#718066}
.fw-welcome{background:linear-gradient(125deg,#eef3e4,#fffdf7);border:1px solid #dde5d2;border-radius:22px;padding:30px;margin-bottom:20px}
.fw-welcome h2{font-size:25px;margin:0 0 12px;padding:0;color:#2d523b}
.fw-welcome p{font-size:15px;color:#627459;line-height:1.8}
.fw-step{font-size:13px;color:#5a7051;margin-top:12px}
.fw-section{font-size:11px;letter-spacing:1.8px;color:#6a7f60;font-weight:700;text-transform:uppercase;margin:20px 0 10px}
.fw-footer{font-size:11px;color:#7a8474;border-top:1px solid var(--fw-line);padding-top:16px;line-height:1.8;margin-top:25px}
.fw-credit-label{font-weight:600;color:#566b4e}
@media(max-width:600px){.fw-header{gap:8px}.fw-project{width:210px}.fw-team{gap:4px;flex-direction:column}.fw-team img{width:72px}.fw-ticket{padding:20px}.fw-heading{font-size:29px}}
</style>''')
st.html(f'<div class="fw-header"><img class="fw-project" src="{logo("freshwise-logo.png")}" alt="FreshWise project logo"><div class="fw-team"><span>Created by</span><img src="{logo("sallas-logo.png")}" alt="SALLAS team logo"></div></div>')
st.html('<div class="fw-kicker">Your kitchen assistant</div><h1 class="fw-heading">A little context. A clearer prep plan.</h1><p class="fw-subtitle">Tell FreshWise what is ready and what you expect. Review the recommendation before making it your plan.</p>')
with st.sidebar:
    st.html('<div class="fw-kicker">Plan your next week</div>')
    with st.expander('Connection settings', expanded=st.session_state.get('agent') is None):
        key = st.text_input('Gemini API key', type='password', value='', help='Used in this session only; never included in the tool trace.')
        model = st.text_input('Model', value=os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'))
    center = st.number_input('Selected centre', min_value=1, value=13, step=1)
    meal = st.number_input('Selected meal', min_value=1, value=1198, step=1)
    load = st.button('Load forecast and start', type='primary')
    st.divider()
    st.caption('START WITH YOUR STOCK')
    st.write('“I have 20 portions ready to use. How many more should I make?”')
    st.caption('ADD YOUR LOCAL KNOWLEDGE')
    st.write('“There’s a local event. I think we’ll get 600 orders.”')
    st.caption('Planning prototype · No real kitchen action is sent.')
if load:
    st.session_state.pop('agent', None)
    st.session_state['messages'] = []
    try:
        with st.spinner('Loading real forecast locally…'):
            context = context_for_meal(int(center), int(meal), load_application_data())
        st.session_state['agent'] = PreparationAgent(context, GeminiClient(key, model))
        st.session_state['selection'] = (int(center), int(meal), model)
    except Exception:
        st.error('Could not start. Check your API key input, model and local FRESHWISE_DATA_DIR; confirm the dish exists in the data.')
agent = st.session_state.get('agent')
if agent is not None and getattr(agent, 'revision', None) != CODE_REVISION:
    st.session_state.pop('agent', None)
    st.session_state['messages'] = []
    agent = None
    st.info('The conversation code was updated. Load the forecast again to start a fresh session.')
if agent is None:
    st.html('<div class="fw-welcome"><div class="fw-kicker">Make the most of what is ready</div><h2>Your next prep plan starts here.</h2><p>Use your available portions first. Add what you know about next week. See a clear recommendation, with the final choice in your hands.</p><div class="fw-step">01 &nbsp; Connect in the sidebar &nbsp; · &nbsp; 02 &nbsp; Load your dish &nbsp; · &nbsp; 03 &nbsp; Start a conversation</div></div>')
    st.info('Enter a key in Connection settings, then load the forecast. This does not call the AI yet.')
    st.html('<div class="fw-footer"><span class="fw-credit-label">Lan</span> · Conversation interface &amp; AI integration<br><span class="fw-credit-label">Silvia</span> · Forecasting model &amp; forecast tools<br><span class="fw-credit-label">Ari</span> · Preparation policy &amp; decision tools<br>Local prototype. Forecasts are estimates; inventory is supplied by the manager.</div>')
    st.stop()
if st.session_state['selection'] != (int(center), int(meal), model):
    st.warning('Selection changed. Load the forecast again to reset conversation and plans.')
    st.stop()
record = agent.context.forecast_record
st.html(f'<div class="fw-pills"><span>Centre {int(center)}</span><span>Meal {int(meal)}</span><span>Week {record["target_week"]}</span><span>Forecast loaded</span></div>')
if agent.active_plan is not None:
    plan = agent.active_plan
    st.html(f'<div class="fw-ticket"><span class="fw-status">Confirmed plan</span><h2>Prepare {plan["new_portions_to_prepare"]} new portions.</h2><div class="fw-numbers"><div><strong>{plan["usable_stock"]}</strong><small>ready to use · use these first</small></div><div><strong>{agent.context.forecast:.2f}</strong><small>expected orders · model forecast</small></div></div><p>This is your active plan in the demo. Any new adjustment needs your confirmation.</p></div>')
else:
    st.html(f'<div class="fw-ticket"><span class="fw-status">Let’s make a plan</span><h2>What do you already have ready?</h2><p>Expected orders: about {agent.context.forecast:.2f}. Tell the assistant your usable portions to see what to prepare next. No plan has been confirmed yet.</p></div>')
st.html('<div class="fw-section">Your conversation</div>')
if not st.session_state.get('messages'):
    with st.chat_message('assistant', avatar='🌿'):
        st.write('Hi! How many portions do you already have ready to use for this dish? Zero is fine too.')
for msg in st.session_state.get('messages', []):
    with st.chat_message(msg['role'], avatar='🌿' if msg['role'] == 'assistant' else '👤'):
        st.write(msg['text'])
prompt = st.chat_input('Tell FreshWise your ready stock or event estimate')
if prompt:
    st.session_state['messages'].append({'role': 'user', 'text': prompt})
    with st.spinner('Calling AI and the planning tools…'):
        response = agent.send(prompt)
    st.session_state['messages'].append({'role': 'assistant', 'text': response['answer']})
    st.rerun()
if agent.last_error:
    st.caption(f'Last error: {agent.last_error}. Re-enter the message to retry; the active plan is unchanged.')
if agent.estimate is not None and agent.pending_plan is None:
    st.html('<div class="fw-section">How much should your estimate influence the plan?</div>')
    for col, label in zip(st.columns(3), WEIGHTS):
        if col.button(label):
            with st.spinner('Requesting adjustment preview…'):
                response = agent.choose_weight(label)
            st.session_state['messages'].extend([
                {'role': 'user', 'text': label}, {'role': 'assistant', 'text': response['answer']}])
            st.rerun()
if agent.pending_plan is not None:
    pending = agent.pending_plan
    before = f'{agent.active_plan["new_portions_to_prepare"]} → ' if agent.active_plan is not None else ''
    st.html(f'<div class="fw-ticket pending"><span class="fw-status">Preview · not applied</span><h2>{before}{pending["new_portions_to_prepare"]} new portions</h2><p>Use {pending["usable_stock"]} ready portions first. Review this recommendation before applying it. Your current confirmed plan stays unchanged.</p></div>')
    if st.button('Confirm and apply plan', type='primary'):
        response = agent.confirm()
        st.session_state['messages'].append({'role': 'assistant', 'text': response['answer']})
        st.rerun()
    if st.button('Discard preview'):
        response = agent.cancel_preview()
        st.session_state['messages'].append({'role': 'assistant', 'text': response['answer']})
        st.rerun()
with st.expander('What this prototype can and cannot do'):
    st.write('Can: collect ready stock and a manager estimate, call existing preparation tools using a locally generated forecast, preview three adjustment weights and require confirmation before updating the demo plan.')
    st.write('Cannot: verify food safety, deduct real inventory, send kitchen orders, guarantee demand or zero waste, or predict exact next-week waste/shortages. Gemini does not train the forecast model or calculate portions.')
    st.write('Numerical explanations use templates filled with actual tool results. This is a constrained tool-using prototype, not an unrestricted autonomous agent. Internet/API access is required for chat; the original manual app is the fallback.')
with st.expander('Exact tool trace and forecast context'):
    st.json({'forecast': record, 'tool_calls': agent.trace})
    st.download_button('Download trace (no API key)',
                       data=__import__('json').dumps({'forecast': record, 'tool_calls': agent.trace}, indent=2),
                       file_name='freshwise-agent-trace.json', mime='application/json')
st.html('<div class="fw-footer"><span class="fw-credit-label">Lan</span> · Conversation interface &amp; AI integration<br><span class="fw-credit-label">Silvia</span> · Forecasting model &amp; forecast tools<br><span class="fw-credit-label">Ari</span> · Preparation policy &amp; decision tools<br>Powered by Gemini with FreshWise tools. Numerical explanations use actual tool results. Plans are applied within this demo only.</div>')
