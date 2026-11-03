"""Offline checks for the planned 47-marker combined annotation protocol.

This module has no transport, credential lookup, generation or job-submission
implementation. Validation cannot activate the scientific experiment.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


def validate_protocol(protocol: dict) -> dict:
    """Admit a dormant preparation, never a launch-ready campaign."""
    if protocol.get('status') != 'planned_not_executed':
        raise ValueError('Preparation must remain planned_not_executed')
    execution = protocol['execution']
    if execution.get('enabled') is not False or execution.get('automatic_launch') is not False:
        raise ValueError('Execution and automatic launch must remain disabled')
    if execution.get('executor_entrypoint') is not None:
        raise ValueError('No executor is wired to this preparation')
    if execution.get('annotation_calls') != 0 or execution.get('jobs_submitted') != 0:
        raise ValueError('Preparation must record zero calls and jobs')
    if execution.get('spend_cap_usd') is not None or execution.get('launch_authorization') is not None:
        raise ValueError('No spending or launch authorization belongs to this preparation')
    markers = protocol['markers']
    if protocol.get('n_markers') != 47 or len(markers) != 47 or len(set(markers)) != 47:
        raise ValueError('Exactly 47 distinct markers are required')
    if not {'CD123', 'CDX2'}.issubset(markers):
        raise ValueError('The extra two protein markers are required')
    if protocol.get('n_cells') != 220082:
        raise ValueError('Expected all 220082 B004 cells')
    if len(protocol['ontology']) != 28 or len(set(protocol['ontology'])) != 28:
        raise ValueError('The fixed original 28-label vocabulary is required')
    if not {'Noise', 'Paneth', 'NK', 'M1 Macrophage', 'M2 Macrophage'}.issubset(protocol['ontology']):
        raise ValueError('Distinct source labels must be preserved')
    if protocol['arms'] != ['all_means', 'all_means_fractions']:
        raise ValueError('Only the two declared marker-only arms are allowed')
    if protocol['repeats'] != 5 or protocol['batch_size'] != 75:
        raise ValueError('Use five fresh repetitions and batches of at most 75')
    if protocol['methods'] != ['leiden', 'flowsom', 'spatialsort', 'pixie_tiff']:
        raise ValueError('All four frozen methods are required')
    if protocol['model_families'] != ['openai', 'anthropic', 'google', 'deepseek']:
        raise ValueError('All four selected model families are required')
    if set(protocol['model_bindings']) != set(protocol['model_families']):
        raise ValueError('Each selected family needs an explicit unbound record')
    if any(v['status'] != 'unbound' or any(v[k] is not None for k in
           ['model_id', 'provider', 'reasoning_setting', 'max_output_tokens', 'reasoning_token_budget', 'prices', 'verified_at'])
           for v in protocol['model_bindings'].values()):
        raise ValueError('This preparation keeps model/provider/token/price bindings unbound')
    flow, spatial = protocol['partitions']['flowsom'], protocol['partitions']['spatialsort']
    if (flow['seed'], flow['full_passes'], flow['occupied_clusters']) != (42, 3, 299):
        raise ValueError('Preserve the frozen primary FlowSOM contract')
    if (spatial['primary_seed'], spatial['point_estimate_sweep'], spatial['dmh_iter'], spatial['sensitivity_seed']) != (42, 100, 5, 43):
        raise ValueError('Preserve the prespecified final SpatialSort estimate')
    if spatial['require_both_chains_complete'] is not True:
        raise ValueError('Both SpatialSort chains must be validated before a separate launch')
    split = list(protocol['split'].values())
    if {x: split.count(x) for x in set(split)} != {'train': 4, 'calibration': 2, 'test': 2}:
        raise ValueError('Preserve the existing four/two/two region split')
    sets = len(protocol['methods']) * len(protocol['model_families']) * len(protocol['arms']) * protocol['repeats']
    if sets != 160 or protocol['logical_annotation_sets'] != sets:
        raise ValueError('The design must contain 160 annotation sets')
    return {'status': 'valid_planned_protocol', 'annotation_sets': sets,
            'execution_enabled': False, 'annotation_calls': 0, 'jobs_submitted': 0,
            'launch_blockers': execution['required_before_launch']}


def validate_cell_join(frozen_keys, assignment_keys, *, expected_n=220082):
    """Require exactly one membership per frozen (File_ID, ID), with no extras."""
    frozen = [tuple(k) for k in frozen_keys]
    assigned = [tuple(k) for k in assignment_keys]
    if any(len(k) != 2 for k in frozen + assigned):
        raise ValueError('Cell keys must contain File_ID and ID')
    if len(frozen) != expected_n or len(set(frozen)) != expected_n:
        raise ValueError('Frozen cell keys are incomplete or duplicated')
    if len(assigned) != expected_n or len(set(assigned)) != expected_n or set(assigned) != set(frozen):
        raise ValueError('Membership join is missing, duplicated or includes unexpected cells')


def validate_paired_evidence(protocol, means_arm, fractions_arm):
    """Check the actual encoded pair, including identical means and batch IDs."""
    right = deepcopy(fractions_arm)
    fractions = right.pop('fraction_above_processed_zero_thousandths', None)
    if fractions is None or 'fraction_above_processed_zero_thousandths' in means_arm:
        raise ValueError('Only the fractions arm may contain the added matrix')
    if means_arm != right:
        raise ValueError('Paired evidence differs beyond the added fraction matrix')
    if means_arm.get('markers') != protocol['markers'] or means_arm.get('ontology') != protocol['ontology']:
        raise ValueError('Missing or reordered markers or labels')
    if any(k in means_arm for k in ['reference_profiles', 'clustering_method', 'neighborhood_profiles', 'truth_labels']):
        raise ValueError('Forbidden evidence in the marker-only design')
    ids = means_arm['cluster_ids']
    if not 0 < len(ids) <= protocol['batch_size'] or len(set(ids)) != len(ids):
        raise ValueError('Cluster IDs must be unique within a nonempty bounded batch')
    means = means_arm['mean_expression_z_thousandths']
    if len(means) != len(ids) or len(fractions) != len(ids):
        raise ValueError('Evidence rows must match cluster IDs')
    for row in means:
        if len(row) != 47 or any(type(v) is not int for v in row):
            raise ValueError('Expected 47 integer-thousandth means per cluster')
    for row in fractions:
        if len(row) != 47 or any(type(v) is not int or not 0 <= v <= 1000 for v in row):
            raise ValueError('Expected 47 bounded integer-thousandth fractions per cluster')


def validate_request_ids(requests):
    """Independent repetitions and arms cannot share a request record."""
    seen_ids, seen_observations = set(), set()
    for r in requests:
        observation = tuple(r[k] for k in ['method', 'model_family', 'arm', 'repeat', 'batch'])
        if r['request_id'] in seen_ids or observation in seen_observations:
            raise ValueError('Duplicate request ID or duplicate logical observation')
        seen_ids.add(r['request_id'])
        seen_observations.add(observation)


def load_protocol(path):
    protocol = json.loads(Path(path).read_text())
    validate_protocol(protocol)
    return protocol
