# Isolated runtime verification — November 9

Requested and verified locally: Python 3.12.16, NumPy 2.5.4, pandas 3.1.0,
scikit-learn 1.9.1. Streamlit 1.66.1. The original app environment was preserved.
The isolated environment is `.venv-repro`; downloaded Python is in `.python-repro`.
Neither runtime directory belongs in Git.

Centre 13, meal 1198, week 146: exact forecast 453.15969951433823, stock 20 gives
434 new portions; manager estimate 600 at 25% gives 470, or 36 extra portions.
This remained unchanged after aligning the four recorded versions. We have not
reproduced Silvia's 455.0 and have not established the cause of the difference.

Her message contains the literal placeholder "[match / don't match]" for data
hashes. Hash agreement is therefore unconfirmed. Compare the actual four source
CSV hashes, forecast-tool/next_week/supervised revisions, platform and remaining
package versions next. Local hashes and versions are in live_application_acceptance.json.
No final evaluation was rerun; this check predicts week 146 only.

Forecasting/decision source base remains Ari 525a9a8 plus Silvia b16d451 data-tool
fixes. Silvia's reported final-evaluation commit is 7eefc42; we have not checked
out or independently verified that revision's final-run manifest in this session.
The numerical source files were not changed for this design update.

Brand assets: FreshWise logo extracted unchanged from the original supplied
FreshWise_Abstract_Refined.pdf; SALLAS logo copied unchanged from the original
SALLAS Eco Leaf Logo.png. Both are team-provided originals, not replacements.

Current local isolated-runtime preview: http://127.0.0.1:8503
