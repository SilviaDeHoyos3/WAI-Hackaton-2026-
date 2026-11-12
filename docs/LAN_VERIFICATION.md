# Local integration verification — November 9

- Python suite: 115 tests passed, none skipped.
- Scripted Streamlit checks: five central cases, synthetic fewer-shortages case,
  plus invalid/missing stock checks passed.
- Live Streamlit check: centre 13, meal 1198, week 146 forecast loaded from real
  CSVs; central and manager-adjusted quantities match the tools; changing the
  meal clears the previous recommendation.
- Exact local forecast: 453.15969951433823 orders.
- Stock 20 (test input): prepare 434.
- Manager estimate 600, weight 25% (test inputs): prepare
  470.

Silvia's chat example was approximately 455; this installation produces 453.2
(display). Shared forecasting code is unchanged, but exact cross-machine
reproduction still needs comparison with Silvia's data/dependency versions.
Our checks verify the exact locally returned forecast reaches the decision tool.
Runtime versions and data hashes are recorded in the local live trace.

No final-evaluation script or AI conversation was run. These checks do not
validate real-world waste reduction or a completed agent.
