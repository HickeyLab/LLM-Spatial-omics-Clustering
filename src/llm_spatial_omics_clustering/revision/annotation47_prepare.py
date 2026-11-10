"""Prepare and verify the frozen one-repeat annotation request pack, offline.

There is intentionally no credential lookup, HTTP transport, executor or launch
hook in this module. The files it writes are review material, not authorization.
Only selected H5AD datasets are read. Reference-label values are never loaded.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd


METHODS = ['leiden', 'flowsom', 'spatialsort', 'pixie_tiff']
FAMILIES = ['openai', 'anthropic', 'google', 'deepseek']
ARMS = ['all_means', 'all_means_fractions']
OCCUPIED = dict(zip(METHODS, [300, 299, 229, 300]))
MARKERS = ['CD45RO', 'CD56', 'CD15', 'CD163', 'MUC2', 'CD34', 'CD36',
           'aDefensin5', 'CD49a', 'HLA-DR', 'CD38', 'CollagenIV', 'CD4',
           'CD138', 'CD44', 'Vimentin', 'CD66', 'Podoplanin', 'CHGA', 'CD3',
           'SOX9', 'CD161', 'Synaptophysin', 'CD57', 'ITLN1', 'CD127', 'CD45',
           'CD49f', 'aSMA', 'Cytokeratin', 'CD8', 'CD19', 'BCL2', 'CD90',
           'CD21', 'CD7', 'CD11c', 'Ki67', 'CD68', 'MUC1', 'CD206', 'CD16',
           'CD117', 'CD69', 'CD31', 'CD123', 'CDX2']
ONTOLOGY = ['B', 'CD36 high Endothelial', 'CD36 low Endothelial', 'CD4+ T',
            'CD49a+ Smooth muscle', 'CD57+ Epithelial', 'CD66+ Epithelial',
            'CD8+ T', 'Cycling TA', 'DC', 'Epithelial', 'Goblet', 'ICC',
            'ITLN+ Epithelial', 'M1 Macrophage', 'M2 Macrophage',
            'MUC1+ Epithelial', 'NK', 'Nerve', 'Neuroendocrine', 'Neutrophil',
            'Noise', 'PDPN+ Stromal', 'Paneth', 'Plasma', 'Smooth muscle',
            'Stromal', 'TA']
MODEL_IDS = {'openai': 'openai/gpt-6-astra',
             'anthropic': 'anthropic/claude-opus-5.5',
             'google': 'google/gemini-4-argon',
             'deepseek': 'deepseek/deepseek-v4.1-flash-1017'}
ROUTES = {'openai': 'openai', 'anthropic': 'anthropic',
          'google': 'google-vertex/global', 'deepseek': 'deepseek'}
PRIMARY_MANIFEST = 'data/frozen/clustering47_primary_20261108/manifest.json'
PRIMARY_MANIFEST_SHA256 = '1304ed16bc0ff858518a3a5ac18d662c4887f639d7084ee6df1dc8f013dc4618'
H5AD_SHA256 = '5d0a59d1e7866dee5a3a06772c3c80ce7328ba6420bc140708be5ec451b8a49a'
KEY_SHA256 = '7fced5df4b9ff6814059e1786a32154a1b871fe5d2bb4d90d63f2c87fd2b351a'
N_CELLS = 220082

# Literal task reused from revision_20261021/scripts/revision/four_llm_followup.py.
SYSTEM = ('Directly annotate intestinal CODEX query clusters using only supplied evidence. '
          'You choose every final label. Keep all 28 original labels including distinct Paneth, NK, '
          'M1 and M2 macrophages. Noise is a technical-quality class, not abstention. '
          'Return only JSON {"a":[{"i":0,"l":label_code},...]}. Use every supplied query_case_id '
          'exactly once. i is a query ID, never a prototype ID. Do not return explanations or tools.')
EXPRESSION_DEFINITION = ('Cluster means of arcsinh(deposited processed X/5), standardized by '
    'frozen B004 four-training-region marker means and SD. Encoded as integer thousandths: '
    'divide by 1000. Processed X can be negative. Standardized values are not biological positivity.')
FRACTION_DEFINITION = ('If provided, fraction_above_processed_zero is the fraction of cells '
    'with deposited processed X strictly greater than 0, encoded as integer thousandths: '
    'divide by 1000. It is a numerical summary, not validated biological marker positivity.')
TASK = 'Assign one allowed label per query case using the marker profiles and intestinal biological context.'
RESPONSE_CONTRACT = {'a': 'one object per case; fields i=query case ID and l=original label code 0..27'}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(8 * 1024**2), b''):
            result.update(part)
    return result.hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def read_json(path: Path):
    return json.loads(Path(path).read_text(), object_pairs_hook=_unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def relative_path(root: Path, name: str) -> Path:
    path = (Path(root) / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Path must remain within its root')
    return path


def validate_protocol(protocol: dict) -> None:
    """Admit only the selected offline one-repeat design, never a launch."""
    from .annotation47_admission import validate_protocol as validate_admission_protocol
    validate_admission_protocol(protocol)
    if protocol.get('markers') != MARKERS or protocol.get('n_markers') != 47:
        raise ValueError('Expected exact frozen 47-marker order')
    if protocol.get('ontology') != ONTOLOGY:
        raise ValueError('Expected exact original 28-label order')
    for key, expected in [('n_cells', N_CELLS), ('methods', METHODS),
                          ('model_families', FAMILIES), ('arms', ARMS),
                          ('repeats', 1), ('batch_size', 75),
                          ('logical_annotation_sets', 32),
                          ('initial_request_items', 128),
                          ('planned_cluster_predictions', 9024)]:
        if protocol.get(key) != expected:
            raise ValueError(f'Incorrect one-repeat design field: {key}')
    if protocol.get('expected_cell_key_sha256') != KEY_SHA256:
        raise ValueError('Unfrozen cell-key identity')
    if protocol.get('measurement_source', {}).get('sha256') != H5AD_SHA256:
        raise ValueError('Unfrozen measurement source')
    split = protocol.get('split', {})
    if len(split) != 8 or {s: list(split.values()).count(s) for s in set(split.values())} != {
            'train': 4, 'calibration': 2, 'test': 2}:
        raise ValueError('Expected existing four/two/two region split')
    execution = protocol.get('execution', {})
    if execution.get('enabled') is not False or execution.get('automatic_launch') is not False:
        raise ValueError('Offline preparation requires execution disabled')
    if execution.get('annotation_calls') != 0 or execution.get('jobs_submitted') != 0:
        raise ValueError('Preparation requires zero calls and jobs')
    if execution.get('launch_authorization') is not None:
        raise ValueError('Preparation cannot contain launch authorization')
    bindings = protocol.get('model_bindings', {})
    if set(bindings) != set(FAMILIES):
        raise ValueError('Expected four model bindings')
    for family, binding in bindings.items():
        if binding.get('model_id') != MODEL_IDS[family] or binding.get('provider_route') != ROUTES[family]:
            raise ValueError('Model or route substitution')
        expected_transport = 'standard' if family == 'deepseek' else 'batch'
        if binding.get('transport') != expected_transport:
            raise ValueError('Incorrect transport')
        if binding.get('reasoning_setting') != {'effort': 'high'}:
            raise ValueError('Only selected high reasoning is admitted')
        if binding.get('requested_total_output_ceiling') != 32768:
            raise ValueError('Incorrect requested output ceiling')
        if not isinstance(binding.get('canonical_slug_expected'), str):
            raise ValueError('Missing canonical model identity')
        if type(binding.get('seed_supported')) is not bool:
            raise ValueError('Explicit seed support is required')
        if binding['seed_supported'] != ('seed' in binding.get('supported_parameters', [])):
            raise ValueError('Seed support and supported-parameter inventory disagree')


def validate_evidence(protocol: dict, evidence: dict, arm: str) -> None:
    """Positive allowlist, including every nested object and scalar type."""
    if arm not in ARMS or type(evidence) is not dict:
        raise ValueError('Unknown evidence arm or object')
    fixed = {'label_dictionary': {str(i): label for i, label in enumerate(protocol['ontology'])},
             'marker_order': protocol['markers'], 'expression_definition': EXPRESSION_DEFINITION,
             'fraction_definition': FRACTION_DEFINITION, 'task': TASK,
             'response_contract': RESPONSE_CONTRACT}
    allowed = set(fixed) | {'query_case_ids', 'mean_asinh_expression_z_thousandths'}
    if arm == ARMS[1]:
        allowed.add('fraction_above_processed_zero')
    if set(evidence) != allowed or any(evidence.get(key) != value for key, value in fixed.items()):
        raise ValueError('Evidence violates recursive positive allowlist')
    ids = evidence['query_case_ids']
    if type(ids) is not list or not 1 <= len(ids) <= protocol['batch_size']:
        raise ValueError('Invalid anonymous query IDs')
    if any(type(value) is not int for value in ids) or ids != list(range(len(ids))):
        raise ValueError('IDs must be anonymous consecutive integers')
    for name in ['mean_asinh_expression_z_thousandths'] + (
            ['fraction_above_processed_zero'] if arm == ARMS[1] else []):
        matrix = evidence[name]
        if type(matrix) is not list or len(matrix) != len(ids):
            raise ValueError('Incorrect evidence rows')
        for row in matrix:
            if type(row) is not list or len(row) != 47 or any(type(value) is not int for value in row):
                raise ValueError('Expected 47 integer values in each evidence row')
            if name == 'fraction_above_processed_zero' and any(not 0 <= value <= 1000 for value in row):
                raise ValueError('Fraction is outside integer-thousandth bounds')


def evidence_pair(protocol: dict, means_z: np.ndarray, fractions: np.ndarray) -> dict:
    means_z, fractions = np.asarray(means_z), np.asarray(fractions)
    if means_z.shape != fractions.shape or means_z.ndim != 2 or means_z.shape[1] != 47:
        raise ValueError('Profiles must have exactly 47 matched markers')
    if not np.isfinite(means_z).all() or not np.isfinite(fractions).all() or not (
            (fractions >= 0) & (fractions <= 1)).all():
        raise ValueError('Nonfinite profiles or invalid fractions')
    left = {'label_dictionary': {str(i): label for i, label in enumerate(protocol['ontology'])},
            'marker_order': protocol['markers'], 'expression_definition': EXPRESSION_DEFINITION,
            'fraction_definition': FRACTION_DEFINITION, 'query_case_ids': list(range(len(means_z))),
            'mean_asinh_expression_z_thousandths': np.rint(means_z * 1000).astype(np.int64).tolist(),
            'task': TASK, 'response_contract': RESPONSE_CONTRACT.copy()}
    right = {**left, 'fraction_above_processed_zero': np.rint(fractions * 1000).astype(np.int64).tolist()}
    validate_evidence(protocol, left, ARMS[0])
    validate_evidence(protocol, right, ARMS[1])
    return {ARMS[0]: left, ARMS[1]: right}


def payload(protocol: dict, family: str, evidence: dict) -> dict:
    binding = protocol['model_bindings'][family]
    body = {'model': binding['model_id'],
            'messages': [{'role': 'system', 'content': SYSTEM},
                         {'role': 'user', 'content': canonical_bytes(evidence).decode()}],
            'reasoning': binding['reasoning_setting'], 'max_tokens': 32768,
            'response_format': {'type': 'json_object'}}
    if binding['seed_supported']:
        body['seed'] = 42
    if binding['transport'] == 'standard':
        body['provider'] = {'only': [binding['provider_route']], 'allow_fallbacks': False,
                            'require_parameters': True}
    return body


def validate_body(protocol: dict, record: dict, body: dict) -> dict:
    family, arm = record['model_family'], record['arm']
    binding = protocol['model_bindings'][family]
    try:
        if len(body['messages']) != 2 or body['messages'][0] != {'role': 'system', 'content': SYSTEM}:
            raise ValueError('Unexpected system prompt')
        user = body['messages'][1]
        if set(user) != {'role', 'content'} or user['role'] != 'user' or type(user['content']) is not str:
            raise ValueError('Unexpected user message')
        evidence = json.loads(user['content'], object_pairs_hook=_unique_object)
        validate_evidence(protocol, evidence, arm)
        if body != payload(protocol, family, evidence):
            raise ValueError('Body differs from the sealed parameter allowlist')
        if user['content'] != canonical_bytes(evidence).decode():
            raise ValueError('Noncanonical evidence encoding')
        if len(evidence['query_case_ids']) != record['expected_n']:
            raise ValueError('Query count mismatch')
        for key in ['model_id', 'provider_route', 'canonical_slug_expected', 'transport']:
            if record[key] != binding[key]:
                raise ValueError('Registry and binding disagree')
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError('Malformed request body') from exc
    return evidence


def cell_key_hash(keys: pd.DataFrame) -> str:
    """Existing frozen hash: numeric-ID sorted, headerless File_ID/ID TSV."""
    frame = keys[['File_ID', 'ID']].copy()
    frame['ID'] = frame['ID'].astype(np.int64)
    frame = frame.sort_values(['File_ID', 'ID'], kind='stable')
    return hashlib.sha256(frame.to_csv(index=False, header=False, sep='\t').encode()).hexdigest()


def join_memberships(keys: pd.DataFrame, assignments: pd.DataFrame, column: str,
                     expected_clusters: int) -> np.ndarray:
    """Return assignments in H5AD order, rejecting every non-bijective join."""
    required = ['File_ID', 'ID']
    if (len(assignments) != len(keys) or keys.duplicated(required).any()
            or assignments.duplicated(required).any()
            or assignments[required + [column]].isna().any().any()):
        raise ValueError('Missing or duplicated membership keys/values')
    joined = keys[required].merge(assignments[required + [column]], on=required, how='outer',
                                  validate='one_to_one', sort=False, indicator=True)
    if len(joined) != len(keys) or not joined['_merge'].eq('both').all():
        raise ValueError('Membership cell-key sets differ')
    ordered = keys[required].merge(assignments[required + [column]], on=required,
                                   how='left', validate='one_to_one', sort=False)
    if not ordered[required].equals(keys[required]) or ordered[column].nunique() != expected_clusters:
        raise ValueError('Membership order or occupied-cluster count differs')
    return ordered[column].astype(str).to_numpy()


def compute_profiles(raw: np.ndarray, train: np.ndarray, memberships: dict) -> tuple[dict, dict]:
    raw = np.asarray(raw)
    train = np.asarray(train)
    if raw.ndim != 2 or raw.shape[1] != 47 or not np.isfinite(raw).all():
        raise ValueError('Expected finite 47-marker raw measurements')
    if train.shape != (len(raw),) or train.dtype != np.bool_ or not train.any():
        raise ValueError('Invalid training mask')
    transformed = np.arcsinh(raw.astype(np.float64) / 5)
    center = transformed[train].mean(axis=0)
    raw_scale = transformed[train].std(axis=0, ddof=0)
    scale = np.where(raw_scale == 0, 1., raw_scale)
    scaler = {'center': center, 'scale': scale, 'raw_scale': raw_scale,
              'training_mask': train, 'markers': np.asarray(MARKERS)}
    profiles = {}
    for method, labels in memberships.items():
        # Unicode lexical order is stable across all methods and independent of outcomes.
        names, codes = np.unique(np.asarray(labels, dtype=str), return_inverse=True)
        if codes.shape != (len(raw),):
            raise ValueError('Membership length differs from expression cells')
        counts = np.bincount(codes, minlength=len(names))
        means = np.empty((len(names), 47), dtype=np.float64)
        fractions = np.empty_like(means)
        # Sorted cell order inside every cluster is inherited from authoritative H5AD.
        for index in range(len(names)):
            selected = codes == index
            means[index] = transformed[selected].mean(axis=0)
            fractions[index] = (raw[selected] > 0).mean(axis=0)
        z = (means - center) / scale
        profiles[method] = {'cluster_names': names, 'codes': codes, 'counts': counts,
                            'means_asinh': means, 'means_z': z, 'fractions': fractions,
                            'means_z_thousandths': np.rint(z * 1000).astype(np.int64),
                            'fractions_thousandths': np.rint(fractions * 1000).astype(np.int64)}
    return scaler, profiles


def _h5_string(node):
    if isinstance(node, h5py.Group):
        if set(node) != {'categories', 'codes'}:
            raise ValueError('Unsupported categorical encoding')
        categories = node['categories'].asstr()[:]
        codes = node['codes'][:]
        if (codes < 0).any() or (codes >= len(categories)).any():
            raise ValueError('Missing categorical values')
        return categories[codes]
    return node.asstr()[:]


def load_inputs(protocol: dict, sources_root: Path, h5ad: Path):
    """Read only explicit expression/key datasets and three-column memberships."""
    if sha256_file(h5ad) != H5AD_SHA256:
        raise ValueError('Authoritative H5AD checksum mismatch')
    manifest_path = relative_path(sources_root, PRIMARY_MANIFEST)
    if sha256_file(manifest_path) != PRIMARY_MANIFEST_SHA256:
        raise ValueError('Frozen clustering manifest checksum mismatch')
    manifest = read_json(manifest_path)
    with h5py.File(h5ad, 'r') as handle:
        names = _h5_string(handle['var/_index']).tolist()
        if names != MARKERS[:45] or handle['X'].shape != (N_CELLS, 45) or handle['X'].dtype != np.float64:
            raise ValueError('Incorrect authoritative expression shape/type/order')
        raw = np.column_stack([handle['X'][:], handle['obs/CD123'][:], handle['obs/CDX2'][:]])
        ids = handle['obs/ID'][:]
        if ids.dtype.kind not in 'iu' or (ids < 0).any():
            raise ValueError('Cell IDs must be nonnegative integers')
        keys = pd.DataFrame({'File_ID': _h5_string(handle['obs/File_ID']), 'ID': ids.astype(str)})
    if len(keys) != N_CELLS or keys.duplicated(['File_ID', 'ID']).any() or cell_key_hash(keys) != KEY_SHA256:
        raise ValueError('Authoritative cell keys differ from frozen population')
    if set(keys.File_ID) != set(protocol['split']):
        raise ValueError('Region identity differs from frozen split')
    keys['split'] = keys.File_ID.map(protocol['split'])
    counts = keys['split'].value_counts().to_dict()
    if counts != {'train': 90296, 'calibration': 60210, 'test': 69576}:
        raise ValueError('Frozen region cell counts differ')
    memberships, receipts = {}, {}
    for method in METHODS:
        spec = manifest['methods']['pixie' if method == 'pixie_tiff' else method]
        expected = spec['gzip_sha256']
        path = relative_path(sources_root, spec['path'])
        if sha256_file(path) != expected or manifest['files'][spec['path']]['sha256'] != expected:
            raise ValueError(f'Frozen membership checksum mismatch: {method}')
        column = spec['assignment_column']
        frame = pd.read_csv(path, usecols=['File_ID', 'ID', column], dtype=str, keep_default_na=False)
        if frame[['File_ID', 'ID', column]].eq('').any().any():
            raise ValueError('Empty membership key or assignment')
        memberships[method] = join_memberships(keys, frame, column, OCCUPIED[method])
        binding = protocol['partitions'][method]
        binding_hash = binding.get('gzip_sha256', binding.get('assignments_sha256'))
        if binding_hash != expected or binding.get('occupied_clusters') != OCCUPIED[method]:
            raise ValueError(f'Protocol partition identity differs: {method}')
        receipts[method] = {'path': spec['path'], 'sha256': expected,
                            'assignment_column': column, 'occupied_clusters': OCCUPIED[method],
                            'cells': N_CELLS, 'exact_key_join': True}
    receipt = {'h5ad_sha256': H5AD_SHA256, 'clustering_manifest_sha256': PRIMARY_MANIFEST_SHA256,
               'cell_key_sha256': KEY_SHA256, 'source_rows': N_CELLS, 'markers': MARKERS,
               'selected_h5ad_datasets': ['X', 'var/_index', 'obs/File_ID', 'obs/ID', 'obs/CD123', 'obs/CDX2'],
               'reference_label_values_materialized': False, 'memberships': receipts,
               'region_cell_counts': counts}
    return raw, keys, memberships, receipt


def make_records(protocol: dict, profiles: dict) -> tuple[list, dict, list]:
    records, bodies, maps = [], {}, []
    for method in METHODS:
        profile = profiles[method]
        n = len(profile['cluster_names'])
        if n != OCCUPIED[method] or int(profile['counts'].sum()) != N_CELLS:
            raise ValueError('Profile population differs from frozen method')
        for index, (name, count) in enumerate(zip(profile['cluster_names'], profile['counts'])):
            maps.append({'method': method, 'cluster_index': index, 'cluster_id': str(name),
                         'n_cells': int(count), 'batch': index // 75, 'query_case_id': index % 75})
        for batch, start in enumerate(range(0, n, 75)):
            stop = min(start + 75, n)
            pair = evidence_pair(protocol, profile['means_z'][start:stop], profile['fractions'][start:stop])
            for family in FAMILIES:
                identity = [protocol['protocol_id'], 0, method, family, batch]
                pair_id = 'p' + digest(identity)
                arms = ARMS if int(digest(identity), 16) % 2 == 0 else ARMS[::-1]
                for arm in arms:
                    body = payload(protocol, family, pair[arm])
                    body_bytes = canonical_bytes(body)
                    request_id = 'q' + digest(identity + [arm])
                    binding = protocol['model_bindings'][family]
                    record = {'request_id': request_id, 'pair_id': pair_id, 'method': method,
                              'model_family': family, 'arm': arm, 'repeat': 0, 'batch': batch,
                              'case_start': start, 'case_stop': stop, 'n_cases': stop - start,
                              'expected_n': stop - start, 'body_path': f'payloads/{request_id}.json',
                              'body_sha256': hashlib.sha256(body_bytes).hexdigest(),
                              'evidence_sha256': digest(pair[arm]),
                              'paired_mean_evidence_sha256': digest(pair[ARMS[0]]),
                              **{key: binding[key] for key in ['model_id', 'provider_route',
                                 'canonical_slug_expected', 'transport']}}
                    validate_body(protocol, record, body)
                    records.append(record)
                    bodies[request_id] = body
    validate_records(protocol, records, bodies)
    return records, bodies, maps


def validate_records(protocol: dict, records: list, bodies: dict) -> None:
    expected = set(itertools.product(METHODS, FAMILIES, ARMS, [0], range(4)))
    observed, ids, grouped = set(), set(), {}
    for record in records:
        observation = tuple(record[key] for key in ['method', 'model_family', 'arm', 'repeat', 'batch'])
        if observation not in expected or observation in observed or record['request_id'] in ids:
            raise ValueError('Duplicate or unexpected logical request/ID')
        observed.add(observation)
        ids.add(record['request_id'])
        method, family, arm, repeat, batch = observation
        n = min(75, OCCUPIED[method] - 75 * batch)
        if (record['case_start'], record['case_stop'], record['expected_n'], record['n_cases']) != (
                batch * 75, batch * 75 + n, n, n):
            raise ValueError('Batch coverage or boundaries differ')
        identity = [protocol['protocol_id'], repeat, method, family, batch]
        if record['request_id'] != 'q' + digest(identity + [arm]) or record['pair_id'] != 'p' + digest(identity):
            raise ValueError('Opaque request identity mismatch')
        if record['body_path'] != f"payloads/{record['request_id']}.json":
            raise ValueError('Unexpected request-body path')
        body = bodies[record['request_id']]
        evidence = validate_body(protocol, record, body)
        if record['body_sha256'] != digest(body) or record['evidence_sha256'] != digest(evidence):
            raise ValueError('Request or evidence digest mismatch')
        grouped.setdefault((method, family, repeat, batch), {})[arm] = (record, evidence, body)
    if observed != expected or len(records) != 128 or set(bodies) != ids:
        raise ValueError('Incomplete Cartesian request coverage')
    if sum(record['n_cases'] for record in records) != 9024:
        raise ValueError('Incorrect planned prediction count')
    for pair in grouped.values():
        left_record, left, left_body = pair[ARMS[0]]
        right_record, right, right_body = pair[ARMS[1]]
        added = dict(right)
        added.pop('fraction_above_processed_zero')
        if added != left or left_record['paired_mean_evidence_sha256'] != digest(left) or (
                right_record['paired_mean_evidence_sha256'] != digest(left)):
            raise ValueError('Paired means/evidence mismatch')
        if {k: v for k, v in left_body.items() if k != 'messages'} != {
                k: v for k, v in right_body.items() if k != 'messages'}:
            raise ValueError('Paired inference settings mismatch')


def batch_envelopes(protocol: dict, records: list, bodies: dict) -> dict:
    envelopes = {}
    for family in FAMILIES[:3]:
        binding = protocol['model_bindings'][family]
        selected = [record for record in records if record['model_family'] == family]
        # All fields precede requests for OpenRouter's streaming request parser.
        envelopes[family] = {'endpoint': '/v1/chat/completions', 'model': binding['model_id'],
                             'provider': {'only': [binding['provider_route']], 'allow_fallbacks': False},
                             'completion_window': '24h',
                             'requests': [{'custom_id': record['request_id'],
                                           'body': bodies[record['request_id']]} for record in selected]}
    return envelopes


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _gzip_csv(path: Path, frame: pd.DataFrame) -> None:
    with path.open('wb') as target:
        with gzip.GzipFile(filename='', mode='wb', mtime=0, fileobj=target) as stream:
            stream.write(frame.to_csv(index=False).encode())


def prepare(protocol_path: Path, sources_root: Path, h5ad: Path, output: Path) -> dict:
    protocol_path, sources_root, h5ad, output = map(lambda path: Path(path).expanduser().resolve(),
                                                   [protocol_path, sources_root, h5ad, output])
    if output.exists():
        raise ValueError('Refusing to overwrite an existing output directory')
    for name in ['data', 'configs', 'scripts', 'src', 'tests', 'docs', 'figures', 'notebooks']:
        if output.is_relative_to(sources_root / name):
            raise ValueError('Output cannot be inside repository source or frozen inputs')
    if sources_root.is_relative_to(output) or h5ad.is_relative_to(output):
        raise ValueError('Output cannot contain source inputs')
    protocol = read_json(protocol_path)
    validate_protocol(protocol)
    raw, keys, memberships, source_receipt = load_inputs(protocol, sources_root, h5ad)
    scaler, profiles = compute_profiles(raw, keys['split'].eq('train').to_numpy(), memberships)
    del raw
    records, bodies, maps = make_records(protocol, profiles)
    envelopes = batch_envelopes(protocol, records, bodies)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'profiles').mkdir()
    _write_json(output / 'protocol.json', protocol)
    _write_json(output / 'source_receipt.json', source_receipt)
    _gzip_csv(output / 'cell_keys.csv.gz', keys)
    _gzip_csv(output / 'memberships.csv.gz', pd.DataFrame({**{key: keys[key] for key in ['File_ID', 'ID']},
                                                        **memberships}))
    np.savez_compressed(output / 'training_scaler.npz', **scaler)
    for method, profile in profiles.items():
        np.savez_compressed(output / 'profiles' / f'{method}.npz', **profile)
    pd.DataFrame(maps).to_csv(output / 'cluster_map.csv', index=False)
    for record in records:
        _write_json(output / record['body_path'], bodies[record['request_id']])
    (output / 'requests.jsonl').write_bytes(b''.join(canonical_bytes(record) + b'\n' for record in records))
    for family, envelope in envelopes.items():
        # Intentionally do not sort envelope keys: requests must be the final top-level field.
        path = output / 'batch' / f'{family}.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(envelope, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
    standard = [record for record in records if record['transport'] == 'standard']
    (output / 'standard_request_ids.json').write_bytes(canonical_bytes([r['request_id'] for r in standard]))
    _write_json(output / 'preflight.json', {
        'status': 'prepared_not_submitted', 'execution_enabled': False,
        'annotation_calls': 0, 'jobs_submitted': 0, 'model_requests': 128,
        'batch_items': 96, 'batch_envelopes': 3, 'standard_items': 32,
        'annotation_sets': 32, 'cluster_predictions': 9024,
        'paired_mean_evidence_verified': True, 'reference_label_values_materialized': False,
        'cluster_order': 'Unicode lexicographic cluster-ID order within each frozen method',
        'source_h5ad_cell_order_preserved': True,
        'launch_ready': False, 'authorization': 'Offline preparation only. A separate launch is required.'})
    files = {str(path.relative_to(output)): {'sha256': sha256_file(path), 'bytes': path.stat().st_size}
             for path in sorted(output.rglob('*')) if path.is_file()}
    manifest = {'schema': 'annotation47.one_repeat.request_pack.v1',
                'protocol_id': protocol['protocol_id'], 'protocol_sha256': digest(protocol),
                'protocol_path': 'protocol.json',
                'protocol_source_sha256': sha256_file(protocol_path),
                'source_protocol_path': str(protocol_path),
                'source_h5ad_path': str(h5ad), 'sources_root': str(sources_root),
                'source_h5ad_sha256': H5AD_SHA256, 'clustering_manifest_sha256': PRIMARY_MANIFEST_SHA256,
                'registry': 'requests.jsonl', 'files': files,
                'annotation_calls': 0, 'jobs_submitted': 0, 'launch_ready': False,
                'builder_source_sha256': sha256_file(Path(__file__))}
    _write_json(output / 'manifest.json', manifest)
    return verify_bundle(output)


def verify_bundle(output: Path, *, protocol_path: Path | None = None) -> dict:
    """Re-read sealed bytes and recompute all input-to-prompt and pair checks."""
    output = Path(output).resolve()
    manifest = read_json(output / 'manifest.json')
    if manifest.get('schema') != 'annotation47.one_repeat.request_pack.v1':
        raise ValueError('Unknown request-pack schema')
    actual_names = {str(path.relative_to(output)) for path in output.rglob('*') if path.is_file()}
    if actual_names != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('Unmanifested or missing pack files')
    for name, entry in manifest['files'].items():
        path = relative_path(output, name)
        if sha256_file(path) != entry['sha256'] or path.stat().st_size != entry['bytes']:
            raise ValueError(f'Sealed file changed: {name}')
    protocol = read_json(output / 'protocol.json')
    validate_protocol(protocol)
    if digest(protocol) != manifest['protocol_sha256']:
        raise ValueError('Protocol seal mismatch')
    source_protocol = Path(protocol_path) if protocol_path is not None else Path(manifest['source_protocol_path'])
    if not source_protocol.is_file() or sha256_file(source_protocol) != manifest['protocol_source_sha256']:
        raise ValueError('Source protocol changed since sealing')
    if sha256_file(Path(__file__)) != manifest['builder_source_sha256']:
        raise ValueError('Preparation code changed since sealing')
    registry = relative_path(output, manifest['registry'])
    records = [json.loads(line, object_pairs_hook=_unique_object) for line in registry.read_text().splitlines()]
    bodies = {r['request_id']: read_json(relative_path(output, r['body_path'])) for r in records}
    for record in records:
        if sha256_file(output / record['body_path']) != record['body_sha256']:
            raise ValueError('Literal body hash mismatch')
    validate_records(protocol, records, bodies)
    expected_envelopes = batch_envelopes(protocol, records, bodies)
    for family, expected in expected_envelopes.items():
        envelope = read_json(output / 'batch' / f'{family}.json')
        if list(envelope)[-1] != 'requests' or envelope != expected:
            raise ValueError('Batch envelope differs from exact registered requests')
    expected_standard = [r['request_id'] for r in records if r['transport'] == 'standard']
    if read_json(output / 'standard_request_ids.json') != expected_standard:
        raise ValueError('Standard dispatch registry differs')
    keys = pd.read_csv(output / 'cell_keys.csv.gz', dtype={'File_ID': str, 'ID': str}, keep_default_na=False)
    if list(keys) != ['File_ID', 'ID', 'split'] or cell_key_hash(keys) != KEY_SHA256 or len(keys) != N_CELLS:
        raise ValueError('Saved cell-key population differs')
    if not keys.File_ID.map(protocol['split']).equals(keys['split']):
        raise ValueError('Saved region split differs')
    memberships = pd.read_csv(output / 'memberships.csv.gz', dtype=str, keep_default_na=False)
    if list(memberships) != ['File_ID', 'ID', *METHODS] or not memberships[['File_ID', 'ID']].equals(keys[['File_ID', 'ID']]):
        raise ValueError('Saved membership key order differs')
    with np.load(output / 'training_scaler.npz', allow_pickle=False) as scaler:
        if not np.array_equal(scaler['training_mask'], keys['split'].eq('train').to_numpy()):
            raise ValueError('Training-mask mismatch')
        if scaler['markers'].tolist() != MARKERS or not np.isfinite(scaler['center']).all() or not np.isfinite(scaler['scale']).all():
            raise ValueError('Invalid saved marker scaler')
        if not np.array_equal(scaler['scale'], np.where(scaler['raw_scale'] == 0, 1., scaler['raw_scale'])):
            raise ValueError('Saved zero-variance policy differs')
        for method in METHODS:
            with np.load(output / 'profiles' / f'{method}.npz', allow_pickle=False) as profile:
                names, codes = np.unique(memberships[method].to_numpy(), return_inverse=True)
                if names.tolist() != profile['cluster_names'].tolist() or not np.array_equal(codes, profile['codes']):
                    raise ValueError('Saved profile membership differs')
                if len(names) != OCCUPIED[method] or not np.array_equal(np.bincount(codes), profile['counts']):
                    raise ValueError('Saved profile counts differ')
                z = (profile['means_asinh'] - scaler['center']) / scaler['scale']
                if not np.array_equal(z, profile['means_z']) or not np.isfinite(z).all():
                    raise ValueError('Saved standardized means differ')
                for record in [r for r in records if r['method'] == method]:
                    pair = evidence_pair(protocol, z[record['case_start']:record['case_stop']],
                        profile['fractions'][record['case_start']:record['case_stop']])
                    if json.loads(bodies[record['request_id']]['messages'][1]['content']) != pair[record['arm']]:
                        raise ValueError('Encoded evidence differs from saved full-precision profile')
    return {'status': 'verified_offline_request_pack', 'protocol_id': protocol['protocol_id'],
            'manifest_sha256': sha256_file(output / 'manifest.json'), 'request_items': len(records),
            'batch_items': 96, 'standard_items': 32, 'cluster_predictions': 9024,
            'annotation_calls': 0, 'jobs_submitted': 0, 'launch_ready': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--sources-root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--h5ad', type=Path, help='Authoritative processed-expression H5AD, checksum verified')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-bundle', type=Path)
    args = parser.parse_args(argv)
    if args.verify_bundle is not None:
        if args.h5ad is not None or args.output is not None:
            parser.error('--verify-bundle cannot be combined with preparation inputs')
        result = verify_bundle(args.verify_bundle, protocol_path=args.protocol)
    else:
        if args.protocol is None or args.h5ad is None or args.output is None:
            parser.error('Preparation requires --protocol, --h5ad and --output')
        result = prepare(args.protocol, args.sources_root, args.h5ad, args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
