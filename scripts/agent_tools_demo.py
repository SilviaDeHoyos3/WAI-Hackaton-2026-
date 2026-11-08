"""Try the assistant's data tools on the real data: centre 13 menu, meal 1198 forecast,
and the development evidence. Prints JSON (what the assistant would receive).
The first forecast call fits the hgb model for the centre (about 1 minute); later calls are cached.
"""
import json

from freshwise.agent_data_tools import build_context, evidence_tool, forecast_tool, menu_tool

ctx = build_context()

menu = menu_tool(13, ctx)
print(f"Centre 13 menu: {len(menu['meals'])} meals; first three:")
print(json.dumps(menu["meals"][:3], indent=2))

print("\nForecast for meal 1198 (next week):")
print(json.dumps(forecast_tool(13, 1198, ctx), indent=2))

print("\nEvidence the assistant may quote:")
print(json.dumps(evidence_tool()["demo_meals_centre_13"], indent=2))
