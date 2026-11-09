"""Execute the five scripted cases IN the Streamlit app, saving an honest trace.

This checks UI wiring and deterministic response templates, not LLM conversation.
Run from the project root after installing the demo extra.
"""
from pathlib import Path
import json
from datetime import datetime, timezone
from streamlit.testing.v1 import AppTest


def run():
    root = Path(__file__).resolve().parents[1]
    records = []
    checks = {
        1: lambda r: r["result"]["new_portions_to_prepare"] == 80 and r["result"]["total_available"] == 100,
        2: lambda r: r["result"]["original_plan"]["new_portions_to_prepare"] == 80 and r["result"]["adjusted_plan"]["new_portions_to_prepare"] == 90 and r["result"]["manager_context"]["demand_shift"] == 10,
        3: lambda r: r["result"]["new_portions_to_prepare"] == 0 and r["result"]["total_available"] == 150 and r["result"]["target_supply"] == 100,
        4: lambda r: r["status"] == "needs_input" and r["missing"] == ["manager_estimate", "opinion_weight"] and r["tool_call"] is None,
        5: lambda r: r["status"] == "cannot_guarantee" and r["result"] is None and "Uncertain demand" in r["answer"],
    }
    for case_id in range(1, 6):
        app = AppTest.from_file(str(root / "app.py"), default_timeout=10).run()
        app.radio(key="data_mode").set_value("Acceptance examples").run()
        options = app.selectbox(key="case").options
        case = options[case_id - 1]
        app.selectbox(key="case").select(case).run()
        assert not app.exception, str(app.exception)
        response = app.session_state["current_response"]
        assert checks[case_id](response), response
        records.append({"case": case, "user_message": app.chat_message[0].markdown[0].value,
                        "response": response, "ui_tool_check": "PASS",
                        "reason": "Expected values/status verified in AppTest; actual teammate tool invoked where required.",
                        "llm_conversation_check": "NOT RUN — no model connected"})
    app = AppTest.from_file(str(root / "app.py")).run()
    app.radio(key="data_mode").set_value("Acceptance examples").run()
    app.selectbox(key="case").select(app.selectbox(key="case").options[5]).run()
    response = app.session_state["current_response"]
    assert not app.exception
    assert response["result"]["new_portions_to_prepare"] == 100
    assert response["tool_call"]["application_arguments"]["quantile"] == 5/7
    assert "waste" in response["answer"]
    records.append({"case":"6. Fewer shortages", "response":response,"ui_tool_check":"PASS", "llm_conversation_check":"NOT RUN"})
    # A real UI invalidation check after a valid recommendation.
    app = AppTest.from_file(str(root / "app.py")).run()
    app.radio(key="data_mode").set_value("Acceptance examples").run()
    app.number_input(key="stock_1").set_value(-1).run()
    assert app.session_state["current_response"]["status"] == "error"
    assert len(app.metric) == 0
    app.number_input(key="stock_1").set_value(None).run()
    assert app.session_state["current_response"]["status"] == "needs_input"
    assert len(app.metric) == 0
    output = root / "outputs" / "application_acceptance.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": "525a9a8b501169daa8a2c785b03edd135e98cf09",
        "scope": "Scripted UI plus real Python tools; not end-to-end AI acceptance",
        "cases": records, "stale_result_checks": "PASS"}, indent=2))
    print(f"6 scripted UI/tool cases and stale-result checks passed. Trace: {output}")


if __name__ == "__main__":
    run()
