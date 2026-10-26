# Local data only
Set FRESHWISE_DATA_DIR to your existing folder containing train.csv, test.csv,
meal_info.csv, fulfilment_center_info.csv, sample_submission.csv,
Emissions intensities.csv and TPFLW.csv. Raw data are never committed.
If unset, the loader checks data/ and the existing iCloud FreshWise folder.
Do not edit the original datasets. Preserve identifiers such as CPC codes as strings.
