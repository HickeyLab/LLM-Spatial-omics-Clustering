# Preserved B004 annotation artwork

`artwork_index.json` pins the exact files from main commit
`55638ee701e32e06d7e4553e4fbc4b73b990cc6e` for Figures 3, S7, S10 and S11,
their renderer/design sources, display configuration, inventories and previews.
The original `data/frozen/annotation47_results_20261110` bank remains unchanged.
Unchanged Figure 4 and S6 artwork is not duplicated here.

From the repository root, reconstruct only these superseded figures offline:

```sh
python3 archive/reviewer47_publication_before_20261111/replay_artwork.py
```

The replay verifies the archive, uses its preserved style and palette, reads
the original frozen bank and checks decoded PNG pixel identity. PNG compression
bytes may differ across encoder environments; the original artwork bytes and
their checksums are retained separately in the archive. It writes under
`outputs/` and makes no model calls. These files are archival provenance;
the active figure inventory selects the current result bank and artwork.
