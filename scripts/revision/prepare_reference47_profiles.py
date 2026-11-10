"""Rebuild Figure S4A from 47 stored expression channels, without fitting.

This display uses raw stored processed expression, not the arcsinh/training-z
representation supplied to the annotation models. Reference Noise is excluded.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--h5ad', type=Path, required=True)
    ap.add_argument('--reference-cells', type=Path, required=True)
    ap.add_argument('--protocol', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--processed-cache', type=Path)
    ap.add_argument('--old-45-summary', type=Path)
    args = ap.parse_args()
    import h5py
    protocol = json.loads(args.protocol.read_text())
    markers = protocol['markers']
    assert len(markers) == len(set(markers)) == 47
    assert markers[-2:] == ['CD123', 'CDX2']
    reference = pd.read_csv(args.reference_cells, dtype={'File_ID':str, 'ID':str})
    assert len(reference) == 220082 and not reference.duplicated(['File_ID','ID']).any()
    with h5py.File(args.h5ad, 'r') as h:
        def col(z):
            if isinstance(z,h5py.Group):
                return z['categories'].asstr()[:][z['codes'][:]]
            a = z[:]
            return a.astype(str) if a.dtype.kind in ['S','O'] else a
        obs = h['obs']
        keys = pd.DataFrame({k:col(obs[k]).astype(str) for k in ['File_ID','ID']})
        assert keys.equals(reference[['File_ID','ID']])
        labels = col(obs['cell_type_update'])
        assert np.array_equal(labels, reference['truth_label'].values)
        x = h['X'][:]
        original_names = h['var']['_index'].asstr()[:].tolist()
        processed = np.column_stack([x[:,original_names.index(m)] if m in original_names else col(obs[m])
                                     for m in markers]).astype(np.float64)
    assert processed.shape == (220082,47) and np.isfinite(processed).all()
    cache_exact = None
    if args.processed_cache:
        cached = np.load(args.processed_cache, allow_pickle=False)['processed']
        cache_exact = bool(np.array_equal(cached, processed))
        assert cache_exact, 'Cached raw matrix differs from the original H5AD channels'
    keep = labels != 'Noise'
    assert int(keep.sum()) == 209587
    groups = sorted(np.unique(labels[keep]).tolist())
    assert len(groups) == 27
    matrix = processed[keep]
    codes = pd.Categorical(labels[keep], categories=groups).codes
    counts = np.bincount(codes, minlength=27)
    means = np.stack([np.bincount(codes, weights=matrix[:,j], minlength=27)/counts
                      for j in range(47)], axis=1)
    fractions = np.stack([np.bincount(codes, weights=(matrix[:,j] > 0).astype(np.int64), minlength=27)/counts
                          for j in range(47)], axis=1)
    lo, hi = means.min(axis=0), means.max(axis=0)
    scaled = np.divide(means-lo, hi-lo, out=np.zeros_like(means), where=(hi-lo)>0)
    # Independent direct slice means/counts check for every reference group and marker.
    direct_means = np.stack([matrix[codes == i].mean(axis=0) for i in range(27)])
    direct_fractions = np.stack([(matrix[codes == i] > 0).mean(axis=0) for i in range(27)])
    max_mean_delta = float(np.max(np.abs(means-direct_means)))
    max_fraction_delta = float(np.max(np.abs(fractions-direct_fractions)))
    assert max_mean_delta < 1e-12 and max_fraction_delta == 0
    rows = [{'cell_type':label, 'marker':marker, 'mean_expression':float(means[i,j]),
             'fraction_cells_pct':float(100*fractions[i,j]), 'scaled_mean_expression':float(scaled[i,j]),
             'n_cells':int(counts[i]), 'mean_raw_processed_expression':float(means[i,j])}
            for i,label in enumerate(groups) for j,marker in enumerate(markers)]
    data = pd.DataFrame(rows)
    assert len(data) == 1269 and not data.duplicated(['cell_type','marker']).any()
    old_check = None
    if args.old_45_summary:
        old = pd.read_csv(args.old_45_summary)
        joined = old.merge(data, on=['cell_type','marker'], suffixes=('_old','_new'), validate='one_to_one')
        old_check = {'matched_rows':len(joined),'old_markers':int(old.marker.nunique()),
            'max_mean_abs_delta':float((joined.mean_expression_old-joined.mean_expression_new).abs().max()),
            'max_fraction_percentage_point_delta':float((joined.fraction_cells_pct_old-joined.fraction_cells_pct_new).abs().max()),
            'max_scaled_mean_abs_delta':float((joined.scaled_mean_expression_old-joined.scaled_mean_expression_new).abs().max())}
    args.output.mkdir(parents=True, exist_ok=True)
    csv = args.output/'figureS4_marker_summaries.csv'
    data.to_csv(csv,index=False)
    sources = {str(p):sha(p) for p in [args.h5ad,args.reference_cells,args.protocol]}
    if args.processed_cache: sources[str(args.processed_cache)] = sha(args.processed_cache)
    if args.old_45_summary: sources[str(args.old_45_summary)] = sha(args.old_45_summary)
    verification = {'schema':'reference47_profiles.verification.v1','passed':True,
        'checked_at':datetime.now(timezone.utc).isoformat(),'cells_in_source':220082,'non_noise_cells':209587,
        'reference_classes':27,'markers':47,'rows':1269,'marker_order':markers,
        'source_channel_binding':'45 original H5AD X variables plus obs/CD123 and obs/CDX2',
        'expression_transform':'none; stored processed expression values',
        'fraction_definition':'100 * count(stored value > 0) / reference-type cell count',
        'color_definition':'Within each marker, min-max of raw group means across all 27 non-Noise reference types; constant markers map to zero',
        'source_cell_key_join_exact':True,'source_reference_labels_exact':True,'cached_matrix_bit_exact_to_h5ad':cache_exact,
        'independent_direct_mean_max_abs_delta':max_mean_delta,
        'independent_direct_fraction_max_abs_delta':max_fraction_delta,'old45_overlap_check':old_check,
        'new_model_calls':0,'new_fits':0,'jobs_submitted':0,'source_sha256':sources,
        'summary_csv_sha256':sha(csv),'helper_sha256':sha(__file__)}
    save(args.output/'verification.json',verification)
    manifest = {'schema':'reference47_profiles.frozen.v1','status':'verified','cells':220082,
        'non_noise_cells':209587,'reference_classes':27,'markers':47,'rows':1269,
        'marker_order':markers,'cell_type_order':groups,
        'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in [csv,args.output/'verification.json']},
        'source_sha256':sources,'reproduction_helper':'scripts/revision/prepare_reference47_profiles.py',
        'new_model_calls':0,'new_fits':0}
    save(args.output/'manifest.json',manifest)
    print(json.dumps(verification,indent=2))


if __name__ == '__main__':
    main()
