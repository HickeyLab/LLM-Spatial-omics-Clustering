"""Offline admission and cost reservations for the one-generation campaign.

This module has no credential lookup, HTTP client or submission implementation.
Passing preparation checks never authorizes execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from pathlib import Path


MODELS = {
    'openai': ('openai/gpt-6-astra', 'openai', 'openai/gpt-6-astra-20260903', 'batch'),
    'anthropic': ('anthropic/claude-opus-5.5', 'anthropic', 'anthropic/claude-opus-5.5-20260921', 'batch'),
    'google': ('google/gemini-4-argon', 'google-vertex/global', 'google/gemini-4-argon-20261013', 'batch'),
    'deepseek': ('deepseek/deepseek-v4.1-flash-1017', 'deepseek', 'deepseek/deepseek-v4.1-flash-20261017', 'standard'),
}
METHODS = ['leiden', 'flowsom', 'spatialsort', 'pixie_tiff']
COUNTS = {'leiden': 300, 'flowsom': 299, 'spatialsort': 229, 'pixie_tiff': 300}
SPLIT = {'2e65eeef2dd18bee2a0baf1cec6d35a1': 'train',
         '5318485b16983482401c3be24b6c42ad': 'calibration',
         '63d000170e475af142f6e8673de5eb0f': 'train',
         '768b7adb649959b6a4e354867595032d': 'test',
         '76d3efd17b6fc83aaac13e961824c5ae': 'train',
         '8da8f27977d946b8c912d42c8827b55c': 'test',
         'ae422532f260b3d6fc662aae69b05d33': 'train',
         'dceadbb36871071f30c308ca091fbdc8': 'calibration'}
MARKERS = 'CD45RO CD56 CD15 CD163 MUC2 CD34 CD36 aDefensin5 CD49a HLA-DR CD38 CollagenIV CD4 CD138 CD44 Vimentin CD66 Podoplanin CHGA CD3 SOX9 CD161 Synaptophysin CD57 ITLN1 CD127 CD45 CD49f aSMA Cytokeratin CD8 CD19 BCL2 CD90 CD21 CD7 CD11c Ki67 CD68 MUC1 CD206 CD16 CD117 CD69 CD31 CD123 CDX2'.split()
ONTOLOGY = ['B', 'CD36 high Endothelial', 'CD36 low Endothelial', 'CD4+ T', 'CD49a+ Smooth muscle', 'CD57+ Epithelial', 'CD66+ Epithelial', 'CD8+ T', 'Cycling TA', 'DC', 'Epithelial', 'Goblet', 'ICC', 'ITLN+ Epithelial', 'M1 Macrophage', 'M2 Macrophage', 'MUC1+ Epithelial', 'NK', 'Nerve', 'Neuroendocrine', 'Neutrophil', 'Noise', 'PDPN+ Stromal', 'Paneth', 'Plasma', 'Smooth muscle', 'Stromal', 'TA']


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def validate_protocol(protocol):
    """Validate the selected study, including the non-execution boundary."""
    p = protocol
    if p.get('schema') != 'annotation47.primary.one_repeat_opus55.v1':
        raise ValueError('Wrong one-repeat protocol schema')
    if p.get('status') != 'planned_not_executed' or p.get('experiment_ids') != [7, 14]:
        raise ValueError('Only the planned #7/#14 campaign is admitted')
    for field, value in {'n_cells': 220082, 'n_markers': 47, 'repeats': 1,
                         'batch_size': 75, 'logical_annotation_sets': 32,
                         'initial_request_items': 128, 'planned_cluster_predictions': 9024}.items():
        if type(p.get(field)) is not int or p[field] != value:
            raise ValueError(f'Incorrect {field}')
    if p.get('methods') != METHODS or p.get('model_families') != list(MODELS):
        raise ValueError('Incorrect method/model order')
    if p.get('markers') != MARKERS or p.get('ontology') != ONTOLOGY:
        raise ValueError('Missing or reordered markers or original label vocabulary')
    if p.get('arms') != ['all_means', 'all_means_fractions'] or p.get('repeat_seeds_where_supported') != [42]:
        raise ValueError('Incorrect paired arms or repetition seed')
    if p.get('split') != SPLIT:
        raise ValueError('Preserve exact frozen training/validation/test region roles')
    ex = p['execution']
    if any(ex.get(k) is not False for k in ['enabled', 'automatic_launch']):
        raise ValueError('Execution must stay disabled')
    if any(ex.get(k) is not None for k in ['executor_entrypoint', 'spend_cap_usd', 'launch_authorization']):
        raise ValueError('No wired executor or paid launch authorization is permitted')
    if ex.get('annotation_calls') != 0 or ex.get('jobs_submitted') != 0:
        raise ValueError('No generation or job may have occurred')
    if Decimal(p['budget']['proposed_inference_ceiling_usd']) != Decimal('65'):
        raise ValueError('Preserve the proposed $65 ceiling')
    if p['budget'].get('spending_authorized') is not False or p['budget'].get('approved_cap_usd') is not None:
        raise ValueError('A proposed ceiling is not spending authorization')
    if set(p['model_bindings']) != set(MODELS):
        raise ValueError('Incomplete model bindings')
    for family, identity in MODELS.items():
        b = p['model_bindings'][family]
        if tuple(b[k] for k in ['model_id', 'provider_route', 'canonical_slug_expected', 'transport']) != identity:
            raise ValueError('Model, canonical identity, provider or transport drift')
        if b['reasoning_setting'] != {'effort': 'high'} or b['requested_total_output_ceiling'] != 32768:
            raise ValueError('Preserve high reasoning and requested output limit')
        expected_reservation = 393216 if family == 'deepseek' else 32768
        if type(b['reservation_output_tokens']) is not int or b['reservation_output_tokens'] != expected_reservation:
            raise ValueError('Incorrect output cost reservation')
    flow = p['partitions']['flowsom']
    if (flow['seed'], flow['full_passes'], flow['occupied_clusters']) != (42, 3, COUNTS['flowsom']):
        raise ValueError('Incorrect frozen FlowSOM')
    ss = p['partitions']['spatialsort']
    if (ss['primary_seed'], ss['point_estimate_sweep'], ss['dmh_iter'], ss['occupied_clusters']) != (42, 100, 5, 229):
        raise ValueError('Incorrect frozen SpatialSort')
    if p['publication_scope']['fresh_study_ids'] != [7, 14] or p['publication_scope']['archived_experiment_ids'] != [9]:
        raise ValueError('Incorrect publication study scope')
    if p['publication_scope'].get('figure_replacements_paused') is not True:
        raise ValueError('Figure replacements must remain paused')
    return {'annotation_sets': 32, 'request_items': 128, 'cluster_predictions': 9024, 'execution_enabled': False}


def verify_provider_metadata(protocol, metadata_dir):
    """Recompute admission from the frozen public catalog, not asserted flags."""
    validate_protocol(protocol)
    root = Path(metadata_dir)
    catalog = json.loads((root / 'models.json').read_text())
    catalog_by_id = {m['id']: m for m in catalog['data']}
    report = {}
    for family, identity in MODELS.items():
        b = protocol['model_bindings'][family]
        path = root / f'{family}_endpoints.json'
        if sha256(path) != b['metadata_sha256'] or sha256(root / 'models.json') != b['canonical_catalog_sha256']:
            raise ValueError('Provider evidence hash mismatch')
        model = catalog_by_id[b['model_id']]
        if model['canonical_slug'] != b['canonical_slug_expected'] or 'high' not in model.get('reasoning', {}).get('supported_efforts', []):
            raise ValueError('Canonical identity/high-effort mismatch')
        inventory = json.loads(path.read_text())['data']
        expected_id = b['model_id'] + (':batch' if b['transport'] == 'batch' else '')
        if inventory['id'] != expected_id:
            raise ValueError('Wrong endpoint inventory')
        endpoints = [e for e in inventory['endpoints'] if e.get('tag') == b['provider_route'] and e.get('status') == 0]
        if len(endpoints) != 1:
            raise ValueError('Pinned route is not uniquely available')
        endpoint = endpoints[0]
        if b['canonical_slug_expected'] not in endpoint['name']:
            raise ValueError('Endpoint canonical identity mismatch')
        supported = endpoint['supported_parameters']
        if not {'reasoning', 'max_tokens', 'response_format'}.issubset(supported):
            raise ValueError('Required parameters missing')
        if b['supported_parameters'] != supported or b['seed_supported'] is not ('seed' in supported):
            raise ValueError('Parameter/seed contract mismatch')
        prices = endpoint['pricing']
        candidates = [prices] + prices.get('overrides', [])
        # Astra uses the short-input rate only after every actual request is checked.
        if family == 'openai':
            candidates = [prices]
        for key, field in [('prompt', 'input_per_million_usd'), ('completion', 'output_per_million_usd')]:
            rate = max(Decimal(str(c.get(key, prices[key]))) for c in candidates) * 1_000_000
            if rate != Decimal(b['prices'][field]):
                raise ValueError('Frozen price is not the conservative endpoint price')
        if endpoint['max_completion_tokens'] < b['reservation_output_tokens']:
            raise ValueError('Output reservation exceeds selected route maximum')
        report[family] = {'canonical_identity': model['canonical_slug'], 'provider_route': endpoint['tag'],
                          'high_supported_in_public_metadata': True, 'account_or_runtime_verified': False}
    return report


def _decimal_text(value):
    return str(value.quantize(Decimal('.000001'), rounding=ROUND_CEILING))


def calculate_budget(protocol, requests, bundle_dir):
    """Use actual request contents with a disclosed conservative token proxy.

    Exact provider tokenization and hidden wrapper overhead are not available
    offline. UTF-8 byte length plus 1024 tokens per message is a conservative
    engineering proxy, not a provider-enforced ceiling or exact token count.
    Keep that limitation explicit in the certificate.
    """
    validate_protocol(protocol)
    if len(requests) != 128:
        raise ValueError('Expected the full request registry')
    root = Path(bundle_dir)
    rows = []
    family_totals = {f: {'input_token_proxy': 0, 'reservation': Decimal(0), 'central_scenario': Decimal(0)} for f in MODELS}
    seen = set()
    for request in requests:
        if request['request_id'] in seen:
            raise ValueError('Duplicate budget request')
        seen.add(request['request_id'])
        binding = protocol['model_bindings'][request['model_family']]
        path = root / request['body_path']
        if sha256(path) != request['body_sha256']:
            raise ValueError('Budget payload hash mismatch')
        body = json.loads(path.read_text())
        messages = body['messages']
        input_bytes = sum(len(m['content'].encode('utf-8')) for m in messages)
        proxy = input_bytes + 1024 * len(messages)
        if request['model_family'] == 'openai' and proxy >= 272000:
            raise ValueError('Cannot use Astra short-context rate')
        if body.get('max_tokens') != 32768:
            raise ValueError('Output setting mismatch')
        inp = Decimal(binding['prices']['input_per_million_usd']) / 1_000_000
        out = Decimal(binding['prices']['output_per_million_usd']) / 1_000_000
        reserve = Decimal(proxy) * inp + Decimal(binding['reservation_output_tokens']) * out
        # Scenario only: no claim that byte/3.5 is exact native tokenization.
        central = Decimal(input_bytes) / Decimal('3.5') * inp + Decimal(17384) * out
        totals = family_totals[request['model_family']]
        totals['input_token_proxy'] += proxy
        totals['reservation'] += reserve
        totals['central_scenario'] += central
        rows.append({'request_id': request['request_id'], 'input_utf8_bytes': input_bytes,
                     'input_token_reservation_proxy': proxy, 'reservation_usd': _decimal_text(reserve)})
    reserve = sum(v['reservation'] for v in family_totals.values())
    central = sum(v['central_scenario'] for v in family_totals.values())
    cap = Decimal(protocol['budget']['proposed_inference_ceiling_usd'])
    return {'input_count_method': 'actual UTF-8 message bytes +1024 tokens per message',
            'exact_provider_input_token_counts': False, 'provider_enforced_budget_guarantee': False,
            'central_scenario_method': 'actual UTF-8 message bytes /3.5 input tokens;17384 total output tokens/request',
            'central_scenario_usd': _decimal_text(central), 'reservation_usd': _decimal_text(reserve),
            'proposed_ceiling_usd': str(cap), 'within_proposed_ceiling': reserve <= cap,
            'fees_taxes_and_credit_purchase_excluded': True,
            'models': {f: {k: _decimal_text(v) if isinstance(v, Decimal) else v for k, v in t.items()} for f, t in family_totals.items()},
            'requests': rows}


def preparation_certificate(protocol, bundle_dir, metadata_dir, account=None):
    """Seal honest passing evidence and remaining blockers. Always non-launchable."""
    from .annotation47_prepare import verify_bundle
    root = Path(bundle_dir)
    bundle_check = verify_bundle(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    canonical = lambda obj: json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    if hashlib.sha256(canonical(protocol)).hexdigest() != manifest['protocol_sha256']:
        raise ValueError('Passed protocol differs from the sealed request protocol')
    requests_path = root / 'requests.jsonl'
    requests = [json.loads(line) for line in requests_path.read_text().splitlines() if line]
    providers = verify_provider_metadata(protocol, metadata_dir)
    budget = calculate_budget(protocol, requests, root)
    blockers = ['Separate explicit paid launch instruction and approved spending cap are absent',
                'No paid submission executor is wired to the disabled preparation',
                'Exact provider tokenization and hidden input-wrapper bounds are not independently certified',
                'Public parameter metadata does not establish account-level Batch admission or runtime forwarding']
    if not budget['within_proposed_ceiling']:
        blockers.append('Conservative request-based reservation exceeds the proposed $65 ceiling')
    if not account or not account.get('credential_available'):
        blockers.append('OpenRouter credential unavailable to the read-only account preflight')
    elif not account.get('route_execution_verified'):
        blockers.append('Read-only account checks do not verify inference-route execution')
    return {'schema': 'annotation47.preparation_certificate.v1', 'created_at': datetime.now(timezone.utc).isoformat(),
            'protocol_id': protocol['protocol_id'], 'protocol': validate_protocol(protocol),
            'bundle_manifest_sha256': sha256(root / 'manifest.json'), 'request_registry_sha256': sha256(requests_path),
            'bundle_checks': bundle_check, 'providers': providers, 'budget': budget,
            'account_preflight': account, 'status': 'offline_prepared_launch_blocked', 'launch_ready': False,
            'execution_enabled': False, 'annotation_calls': 0, 'jobs_submitted': 0, 'launch_blockers': blockers}
