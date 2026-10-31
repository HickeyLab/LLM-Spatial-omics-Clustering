# Frozen inputs for current manuscript replay

`manifest.json` pins every file by SHA-256 and records its deposited source path or derivation. These compact inputs come from the frozen October 30 revision release and the checked October 31 manuscript export. Tables, annotations, fixed spatial windows and calculation receipts support offline replots and independent verification. Figure 3 metric CSVs are derived from the pinned archived cell labels and assignments, with independent recalculation in `scripts/verify_manuscript_replay.py`. No new predictions or fits were generated.

`tables/current_tables.json` preserves native table cells and notes. `tables/companions/` retains original deposited filenames and bytes. Current display numbers are in `configs/supplementary_table_crosswalk.json`. `captions.json` preserves the checked current captions as read, without proposed edits. `note_01/` holds a verified historical benchmark request and archived parsed labels.

Run `python scripts/verify_manuscript_replay.py`. Use `docs/manuscript_reproduction.md` for scientific definitions and replay boundaries. Default plotting outputs are separate under `outputs/manuscript_replay/`.
