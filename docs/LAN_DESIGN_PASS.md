# Manager interface design pass — November 9

The default landing screen now uses real next-week planning. A warm cream background,
green preparation card and FreshWise wordmark put the action first. An official
logo asset was not present in the supplied files; the wordmark is temporary.

The main card reads "Prepare 434 new portions" for the verified test input,
with "Expected orders: about 453 · Ready to use: 20" underneath. Manager adjustment
shows "434 → 470 portions" and one sentence attributing the change to the explicit
600-order estimate and 25% weight. Calculation functions and full-precision
forecast handoff are unchanged.

Usable stock and manager controls use plain-language questions. Verification mode,
model details, uncertainty, development evidence, scripted prompts and exact JSON
trace are in collapsed sections. The evidence snapshot is clearly labelled older
than the newly reported final run; no final evaluation has been rerun or imported.

Verification after the design change: all six scripted UI/tool cases and the
real-data Streamlit flow passed, including stale-plan invalidation.

Actual local runtime: Python 3.12.14, scikit-learn 1.9.1, macOS 15.3 arm64.
Silvia reported Python 3.12.16 and scikit-learn 1.9.1. The forecast difference's cause
has not been established. Use dependency versions/data hashes in the traces to
investigate; no forecast value has been manually changed.

No language model is connected. One-extra-week storage is a simulation assumption,
not a food-safety recommendation. Manager adjustments are outside evaluated results.
