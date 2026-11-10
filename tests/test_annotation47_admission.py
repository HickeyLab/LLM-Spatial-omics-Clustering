"""Paid-preflight boundaries and adversarial protocol/price checks, without API calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_spatial_omics_clustering.revision.annotation47_admission import (
    validate_protocol, verify_provider_metadata, calculate_budget, preparation_certificate,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def protocol():
    return json.loads((ROOT / 'configs/primary_annotation47_1repeat_opus55_v1.json').read_text())


def test_exact_one_repeat_campaign_has_no_execution(protocol):
    assert validate_protocol(protocol) == {'annotation_sets': 32, 'request_items': 128,
                                         'cluster_predictions': 9024, 'execution_enabled': False}


@pytest.mark.parametrize('field,value', [
    ('repeats', 3), ('repeats', True), ('initial_request_items', 384),
    ('experiment_ids', [7, 9, 14]), ('planned_cluster_predictions', 27072),
])
def test_stale_designs_are_rejected(protocol, field, value):
    protocol[field] = value
    with pytest.raises(ValueError):
        validate_protocol(protocol)


def test_marker_order_label_order_noise_and_launch_boundary(protocol):
    for field in ['markers', 'ontology']:
        changed = deepcopy(protocol)
        changed[field] = list(reversed(changed[field]))
        with pytest.raises(ValueError):
            validate_protocol(changed)
    for field, value in [('enabled', True), ('automatic_launch', True),
                         ('launch_authorization', 'old campaign'), ('spend_cap_usd', 65),
                         ('executor_entrypoint', 'run.py')]:
        changed = deepcopy(protocol)
        changed['execution'][field] = value
        with pytest.raises(ValueError):
            validate_protocol(changed)


def test_role_swap_preserving_four_two_two_counts_is_rejected(protocol):
    split = protocol['split']
    keys = list(split)
    split[keys[0]], split[keys[3]] = split[keys[3]], split[keys[0]]
    with pytest.raises(ValueError, match='region roles'):
        validate_protocol(protocol)


def test_flowsom_contract_metadata_cannot_drift(protocol):
    protocol['partitions']['flowsom']['full_passes'] = 1
    with pytest.raises(ValueError, match='FlowSOM'):
        validate_protocol(protocol)


def test_model_provider_reasoning_and_reservation_cannot_drift(protocol):
    for field, value in [('model_id', 'anthropic/claude-fable-5.1'),
                         ('provider_route', 'some-cheaper-provider'),
                         ('reasoning_setting', {'effort': 'medium'}),
                         ('requested_total_output_ceiling', 65536)]:
        changed = deepcopy(protocol)
        changed['model_bindings']['anthropic'][field] = value
        with pytest.raises(ValueError):
            validate_protocol(changed)
    protocol['model_bindings']['deepseek']['reservation_output_tokens'] = 32768
    with pytest.raises(ValueError):
        validate_protocol(protocol)


def fake_metadata(protocol, tmp_path):
    catalog = {'data': []}
    for family, binding in protocol['model_bindings'].items():
        catalog['data'].append({'id': binding['model_id'], 'canonical_slug': binding['canonical_slug_expected'],
                                'reasoning': {'supported_efforts': ['high']}})
        rates = binding['prices']
        endpoint = {'name': binding['canonical_slug_expected'], 'tag': binding['provider_route'], 'status': 0,
                    'supported_parameters': binding['supported_parameters'], 'max_completion_tokens': 393216,
                    'pricing': {'prompt': str(float(rates['input_per_million_usd']) / 1e6),
                                'completion': str(float(rates['output_per_million_usd']) / 1e6)}}
        inventory = {'data': {'id': binding['model_id'] + (':batch' if binding['transport'] == 'batch' else ''),
                              'endpoints': [endpoint]}}
        path = tmp_path / f'{family}_endpoints.json'
        path.write_text(json.dumps(inventory))
        binding['metadata_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    path = tmp_path / 'models.json'
    path.write_text(json.dumps(catalog))
    for binding in protocol['model_bindings'].values():
        binding['canonical_catalog_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()


def test_price_metadata_is_recomputed_not_trusted(protocol, tmp_path):
    fake_metadata(protocol, tmp_path)
    result = verify_provider_metadata(protocol, tmp_path)
    assert len(result) == 4
    protocol['model_bindings']['anthropic']['prices']['output_per_million_usd'] = '1'
    with pytest.raises(ValueError, match='price'):
        verify_provider_metadata(protocol, tmp_path)


def test_tampered_route_evidence_is_rejected(protocol, tmp_path):
    fake_metadata(protocol, tmp_path)
    (tmp_path / 'anthropic_endpoints.json').write_text('{}')
    with pytest.raises(ValueError, match='hash'):
        verify_provider_metadata(protocol, tmp_path)


def make_budget_requests(protocol, tmp_path, content='small'):
    requests = []
    for family in protocol['model_families']:
        for number in range(32):
            body = {'messages': [{'role': 'system', 'content': content}, {'role': 'user', 'content': content}],
                    'max_tokens': 32768}
            name = f'{family}-{number}.json'
            path = tmp_path / name
            path.write_text(json.dumps(body))
            requests.append({'request_id': name, 'model_family': family, 'body_path': name,
                             'body_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return requests


def test_deepseek_route_maximum_reserved_without_raising_generation_limit(protocol, tmp_path):
    requests = make_budget_requests(protocol, tmp_path)
    budget = calculate_budget(protocol, requests, tmp_path)
    assert budget['within_proposed_ceiling']
    assert float(budget['models']['deepseek']['reservation']) > 15
    assert budget['exact_provider_input_token_counts'] is False
    assert budget['provider_enforced_budget_guarantee'] is False


def test_duplicate_request_and_changed_payload_block_budget(protocol, tmp_path):
    requests = make_budget_requests(protocol, tmp_path)
    with pytest.raises(ValueError, match='Duplicate'):
        calculate_budget(protocol, requests[:-1] + [requests[0]], tmp_path)
    (tmp_path / requests[0]['body_path']).write_text('{}')
    with pytest.raises(ValueError, match='hash'):
        calculate_budget(protocol, requests, tmp_path)


def test_reservation_over_65_is_detected_without_automatic_cap_raise(protocol, tmp_path):
    requests = make_budget_requests(protocol, tmp_path, content='x' * 100000)
    budget = calculate_budget(protocol, requests, tmp_path)
    assert not budget['within_proposed_ceiling']
    assert budget['proposed_ceiling_usd'] == '65.00'


def test_astra_long_prompt_override_cannot_be_underpriced(protocol, tmp_path):
    requests = make_budget_requests(protocol, tmp_path, content='x' * 140000)
    with pytest.raises(ValueError, match='short-context'):
        calculate_budget(protocol, requests, tmp_path)


def test_certificate_cannot_mix_a_different_valid_protocol_with_sealed_requests(protocol, tmp_path):
    canonical = json.dumps(protocol, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    (tmp_path / 'manifest.json').write_text(json.dumps({
        'protocol_sha256': hashlib.sha256(canonical).hexdigest()}))
    different = deepcopy(protocol)
    different['reporting']['interpretation'] = 'Different analysis statement'
    with patch('llm_spatial_omics_clustering.revision.annotation47_prepare.verify_bundle', return_value={}):
        with pytest.raises(ValueError, match='differs from the sealed'):
            preparation_certificate(different, tmp_path, tmp_path)
