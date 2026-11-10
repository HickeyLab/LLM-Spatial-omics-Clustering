"""Offline acceptance, accounting and scoring for the one-repetition campaign.

There is deliberately no HTTP client, credential lookup, launch command, response
repair or generation retry here. Submission state helpers only persist evidence
supplied by a caller. A submission receipt is evidence of serving identity, not
the requested identity copied from the request registry.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import tempfile


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'Duplicate JSON key: {key}')
        obj[key] = value
    return obj


def strict_json(text):
    """Reject duplicate keys and JavaScript's non-JSON NaN/Infinity extensions."""
    def reject_constant(value):
        raise ValueError(f'Non-JSON constant: {value}')
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=reject_constant)


def parse_labels(content, expected_n):
    if type(expected_n) is not int or not 0 < expected_n <= 75:
        raise ValueError('Expected a nonempty batch of at most 75 cases')
    if not isinstance(content, str):
        raise ValueError('Content must be a JSON string')
    obj = strict_json(content)
    if type(obj) is not dict or set(obj) != {'a'} or type(obj['a']) is not list:
        raise ValueError('Require exactly the a array')
    if len(obj['a']) != expected_n:
        raise ValueError('Missing or extra annotation cases')
    labels = {}
    for item in obj['a']:
        if type(item) is not dict or set(item) != {'i', 'l'}:
            raise ValueError('Each annotation must contain only i and l')
        i, label = item['i'], item['l']
        if type(i) is not int or type(label) is not int:
            raise ValueError('Query IDs and label codes must be strict integers')
        if not 0 <= i < expected_n or not 0 <= label < 28 or i in labels:
            raise ValueError('Duplicate/out-of-range query ID or label code')
        labels[i] = label
    if set(labels) != set(range(expected_n)):
        raise ValueError('Query IDs must cover the exact planned batch')
    return [labels[i] for i in range(expected_n)]


def _decoded(raw):
    if isinstance(raw, bytes):
        payload_bytes = raw
        value = strict_json(raw.decode('utf-8'))
        representation = 'original_utf8_bytes'
    elif isinstance(raw, str):
        payload_bytes = raw.encode('utf-8')
        value = strict_json(raw)
        representation = 'original_utf8_bytes'
    elif type(raw) is dict:
        payload_bytes = json.dumps(raw, sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=False, allow_nan=False).encode('utf-8')
        value = raw
        representation = 'canonical_mapping_bytes'
    else:
        raise ValueError('A response must be JSON bytes, text or an object')
    if type(value) is not dict:
        raise ValueError('The response envelope must be an object')
    return value, hashlib.sha256(payload_bytes).hexdigest(), representation


def _unwrap(value):
    """Return Chat Completions body, including OpenRouter Batch result wrappers."""
    if value.get('error') is not None:
        raise ValueError('Provider or Batch result reports an error')
    response = value.get('response')
    if response is None:
        return value
    if type(response) is not dict:
        raise ValueError('Response wrapper is not an object')
    if 'status_code' in response:
        if type(response['status_code']) is not int or response['status_code'] != 200:
            raise ValueError('Provider response was not HTTP 200')
        body = response.get('body')
    else:
        body = response
    if type(body) is not dict or body.get('error') is not None:
        raise ValueError('Missing or failed Chat Completions body')
    return body


def _receipt_for_request(receipt, request):
    if type(receipt) is not dict:
        return None
    request_id = request['request_id']
    if receipt.get('request_id') == request_id:
        return receipt
    ids = receipt.get('request_ids')
    if type(ids) is list and request_id in ids and len(ids) == len(set(ids)):
        return receipt
    return None


def _identity(body, outer, request, receipt):
    """Require model and exact route evidence; generic Google is not a route."""
    receipt = _receipt_for_request(receipt, request)
    expected_model = request['model_id']
    expected_canonical = request.get('canonical_slug_expected')
    expected_route = request['provider_route']
    observed_model = body.get('model')
    if observed_model is not None and observed_model not in {expected_model, expected_canonical}:
        return 'identity_mismatch', 'Unexpected response model'
    receipt_model = receipt.get('model_id') if receipt else None
    receipt_canonical = receipt.get('canonical_slug') if receipt else None
    if receipt_model is not None and receipt_model != expected_model:
        return 'identity_mismatch', 'Submission receipt model differs'
    if receipt_canonical is not None and receipt_canonical != expected_canonical:
        return 'identity_mismatch', 'Submission receipt canonical identity differs'
    if expected_canonical:
        if observed_model != expected_canonical and receipt_canonical != expected_canonical:
            return 'identity_unverified', 'Canonical model identity requires a bound receipt'
    elif observed_model != expected_model and receipt_model != expected_model:
        return 'identity_unverified', 'Model identity is missing'
    observed_provider = body.get('provider_route', outer.get('provider_route'))
    observed_name = body.get('provider', outer.get('provider'))
    # These display names identify one intended provider. Google display names
    # are deliberately excluded because they cannot identify a global route.
    unambiguous_names = {'OpenAI': 'openai', 'Anthropic': 'anthropic', 'DeepSeek': 'deepseek'}
    if observed_provider is None and observed_name in unambiguous_names:
        observed_provider = unambiguous_names[observed_name]
    if observed_provider is not None and observed_provider != expected_route:
        return 'identity_mismatch', 'Unexpected serving provider route'
    if observed_name is not None:
        expected_display = {'openai': 'OpenAI', 'anthropic': 'Anthropic',
                            'google-vertex/global': 'Google', 'deepseek': 'DeepSeek'}.get(expected_route)
        if observed_name not in {expected_display, expected_route}:
            return 'identity_mismatch', 'Unexpected serving provider'
    receipt_route = receipt.get('provider_route') if receipt else None
    if receipt_route is not None and receipt_route != expected_route:
        return 'identity_mismatch', 'Submission receipt provider route differs'
    if observed_provider is None and receipt_route != expected_route:
        return 'identity_unverified', 'Exact serving provider route requires a bound receipt'
    return None, None


def _usage(body):
    value = body.get('usage')
    if value is None:
        return None, None
    if type(value) is not dict:
        raise ValueError('Usage is not an object')
    for key in ['prompt_tokens', 'completion_tokens', 'total_tokens']:
        if key in value and (type(value[key]) is not int or value[key] < 0):
            raise ValueError('Invalid usage token count')
    cost = value.get('cost')
    if cost is not None:
        if isinstance(cost, bool):
            raise ValueError('Invalid cost')
        try:
            amount = Decimal(str(cost))
        except InvalidOperation as error:
            raise ValueError('Invalid cost') from error
        if not amount.is_finite() or amount < 0:
            raise ValueError('Invalid cost')
        cost = str(amount)
    return deepcopy(value), cost


def normalize_response(raw, request, receipt=None):
    """Validate one response atomically. Missing or unverified means no labels.

    ``receipt`` must come from an actual bound submission/provider observation.
    A requested route or a protocol's expected canonical identity alone does not
    establish the serving identity. Unverified identity is surfaced separately
    from malformed annotation output, never silently admitted.
    """
    n = request['expected_n']
    if type(n) is not int or not 0 < n <= 75:
        raise ValueError('Expected a nonempty batch of at most 75 cases')
    result = {'request_id': request['request_id'], 'status': 'invalid',
              'labels': [None] * n, 'raw_sha256': None, 'raw_hash_representation': None,
              'usage': None, 'cost_usd': None, 'physical_call_id': None, 'reason': None}
    try:
        outer, sha, representation = _decoded(raw)
        result.update(raw_sha256=sha, raw_hash_representation=representation)
        saved_id = outer.get('custom_id')
        if saved_id is None and 'response' in outer:
            saved_id = outer.get('request_id')
        if saved_id is not None and saved_id != request['request_id']:
            result.update(status='identity_mismatch', reason='Saved result request ID differs')
            return result
        body = _unwrap(outer)
        physical_id = body.get('id')
        if physical_id is None and type(outer.get('response')) is dict:
            physical_id = outer['response'].get('request_id')
        if physical_id is not None:
            if not isinstance(physical_id, str) or not physical_id:
                raise ValueError('Invalid physical call identity')
            result['physical_call_id'] = physical_id
        result['usage'], result['cost_usd'] = _usage(body)
        identity_status, reason = _identity(body, outer, request, receipt)
        if identity_status:
            result.update(status=identity_status, reason=reason)
            return result
        if body.get('status') not in {None, 'completed'}:
            raise ValueError('Nonterminal or incomplete response status')
        choices = body.get('choices')
        if type(choices) is not list or len(choices) != 1:
            raise ValueError('Exactly one response choice is required')
        choice = choices[0]
        if type(choice) is not dict or choice.get('finish_reason') != 'stop':
            raise ValueError('Refused, truncated or nonterminal response')
        message = choice.get('message')
        if type(message) is not dict or message.get('refusal') not in {None, ''}:
            raise ValueError('Missing or refused assistant message')
        result['labels'] = parse_labels(message.get('content'), n)
        result['status'] = 'completed_valid'
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError) as error:
        result['reason'] = str(error)
        if result['raw_sha256'] is None and isinstance(raw, (str, bytes)):
            payload_bytes = raw.encode('utf-8') if isinstance(raw, str) else raw
            result['raw_sha256'] = hashlib.sha256(payload_bytes).hexdigest()
            result['raw_hash_representation'] = 'original_utf8_bytes'
    return result


def collect_results(requests, raw_items, receipts=None):
    """Reconcile every planned request; never use returned list order as identity.

    raw_items may be original JSONL line strings/bytes or decoded result objects.
    Standard responses must be wrapped with their saved custom_id/request_id.
    Unexpected and malformed lines prevent a complete collection certificate.
    Duplicate result rows invalidate that logical request while physical charges
    are deduplicated by a reported generation/request ID, never by label content.
    """
    registry = {r['request_id']: r for r in requests}
    if len(registry) != len(requests):
        raise ValueError('Duplicate planned request IDs')
    receipts = receipts or {}
    groups, unexpected, malformed = defaultdict(list), [], []
    for raw in raw_items:
        try:
            item, sha, _ = _decoded(raw)
            request_id = item.get('custom_id', item.get('request_id'))
            if not isinstance(request_id, str) or not request_id:
                raise ValueError('Result lacks its saved custom_id/request_id')
            if request_id not in registry:
                unexpected.append({'request_id': request_id, 'raw_sha256': sha})
            else:
                groups[request_id].append(raw)
        except (ValueError, TypeError, UnicodeError) as error:
            if isinstance(raw, bytes):
                payload_bytes = raw
            elif isinstance(raw, str):
                payload_bytes = raw.encode('utf-8')
            else:
                payload_bytes = repr(raw).encode('utf-8')
            malformed.append({'reason': str(error),
                              'raw_sha256': hashlib.sha256(payload_bytes).hexdigest()})
    outcomes, calls, conflicts, unresolved_cost = [], {}, [], []
    for request in requests:
        request_id = request['request_id']
        rows = groups.get(request_id, [])
        parsed = [normalize_response(raw, request, receipts.get(request_id)) for raw in rows]
        for item in parsed:
            physical_id = item['physical_call_id']
            if physical_id is None:
                # Hashes preserve evidence but cannot prove that two rows are
                # one execution. Never report an unknown charge as zero.
                unresolved_cost.append({'request_id': request_id,
                                        'raw_sha256': item['raw_sha256']})
                continue
            charge = {'physical_call_id': physical_id, 'request_id': request_id,
                      'usage': item['usage'], 'cost_usd': item['cost_usd']}
            if physical_id in calls and calls[physical_id] != charge:
                conflicts.append({'physical_call_id': physical_id,
                                  'request_ids': [calls[physical_id]['request_id'], request_id]})
            else:
                calls[physical_id] = charge
        if not rows:
            outcomes.append({'request_id': request_id, 'status': 'missing',
                             'labels': [None] * request['expected_n'],
                             'reason': 'No result was supplied'})
        elif len(rows) > 1:
            outcomes.append({'request_id': request_id, 'status': 'duplicate',
                             'labels': [None] * request['expected_n'],
                             'reason': 'Duplicate result rows require reconciliation',
                             'raw_sha256': [p['raw_sha256'] for p in parsed]})
        else:
            outcomes.append(parsed[0])
    known_cost = sum((Decimal(v['cost_usd']) for v in calls.values()
                      if v['cost_usd'] is not None), Decimal(0))
    costs_complete = bool(calls) and not unexpected and not malformed and not unresolved_cost and \
        not conflicts and all(groups.get(r['request_id']) for r in requests) and all(
            v['cost_usd'] is not None for v in calls.values())
    return {'schema': 'annotation47.offline_collection.v1', 'outcomes': outcomes,
            'unexpected_ids': unexpected, 'malformed_items': malformed,
            'all_planned_predictions_valid': all(o['status'] == 'completed_valid' for o in outcomes),
            'collection_complete': not unexpected and not malformed and not conflicts and
                all(o['status'] == 'completed_valid' for o in outcomes),
            'accounting': {'physical_calls': list(calls.values()), 'known_cost_usd': str(known_cost),
                           'cost_complete_for_supplied_calls': costs_complete,
                           'total_cost_usd': str(known_cost) if costs_complete else None,
                           'conflicts': conflicts, 'unresolved_physical_id': unresolved_cost}}


def _validate_labels(truth, predictions, ontology_size):
    if len(truth) != len(predictions):
        raise ValueError('Predictions must retain every planned cell')
    if type(ontology_size) is not int or ontology_size != 28:
        raise ValueError('Use the original fixed 28-label vocabulary')
    if any(type(v) is not int or not 0 <= v < ontology_size for v in truth):
        raise ValueError('Truth labels must be original 28-label codes')
    if any(v is not None and (type(v) is not int or not 0 <= v < ontology_size)
           for v in predictions):
        raise ValueError('Predictions must be original codes or missing, never Noise imputation')


def score_regions(truth, predictions, regions, test_regions, ontology_size=28):
    """Single-run fixed-vocabulary scores, no repeat SD or pseudoreplication."""
    _validate_labels(truth, predictions, ontology_size)
    if len(regions) != len(truth) or len(test_regions) != 2 or len(set(test_regions)) != 2:
        raise ValueError('Require exactly two distinct prespecified test regions')
    metrics = []
    for region in test_regions:
        indices = [i for i, r in enumerate(regions) if r == region]
        if not indices:
            raise ValueError('A test region is missing its planned cells')
        correct = sum(predictions[i] == truth[i] for i in indices)
        delivered = sum(predictions[i] is not None for i in indices)
        f1 = []
        for label in range(ontology_size):
            tp = sum(truth[i] == label and predictions[i] == label for i in indices)
            fp = sum(truth[i] != label and predictions[i] == label for i in indices)
            fn = sum(truth[i] == label and predictions[i] != label for i in indices)
            denominator = 2 * tp + fp + fn
            f1.append(2 * tp / denominator if denominator else 0.0)
        count = len(indices)
        metrics.append({'region': region, 'planned_cells': count, 'delivered_cells': delivered,
                        'correct_cells': correct, 'agreement': correct / count,
                        'fixed28_macro_f1': sum(f1) / 28,
                        'cell_delivery_coverage': delivered / count,
                        'agreement_lower_bound': correct / count,
                        'agreement_upper_bound': (correct + count - delivered) / count})
    return {'regions': metrics, 'equal_region_agreement': sum(m['agreement'] for m in metrics) / 2,
            'equal_region_fixed28_macro_f1': sum(m['fixed28_macro_f1'] for m in metrics) / 2,
            'equal_region_cell_delivery_coverage': sum(m['cell_delivery_coverage'] for m in metrics) / 2,
            'equal_region_agreement_bounds': [sum(m[k] for m in metrics) / 2
                for k in ['agreement_lower_bound', 'agreement_upper_bound']],
            'repetitions': 1, 'repeatability_estimable': False}


def delivery_coverage(cluster_predictions, cluster_sizes):
    if len(cluster_predictions) != len(cluster_sizes) or not cluster_sizes:
        raise ValueError('Retain every planned occupied cluster')
    if any(type(n) is not int or n <= 0 for n in cluster_sizes):
        raise ValueError('Occupied cluster sizes must be positive integers')
    if any(v is not None and (type(v) is not int or not 0 <= v < 28) for v in cluster_predictions):
        raise ValueError('Invalid cluster prediction')
    delivered = sum(v is not None for v in cluster_predictions)
    cells = sum(n for p, n in zip(cluster_predictions, cluster_sizes) if p is not None)
    return {'planned_clusters': len(cluster_sizes), 'delivered_clusters': delivered,
            'cluster_delivery_coverage': delivered / len(cluster_sizes),
            'planned_cells': sum(cluster_sizes), 'delivered_cells': cells,
            'cell_delivery_coverage': cells / sum(cluster_sizes)}


def paired_label_changes(left, right):
    if len(left) != len(right) or not left:
        raise ValueError('Paired predictions must retain every planned case')
    for labels in [left, right]:
        if any(v is not None and (type(v) is not int or not 0 <= v < 28) for v in labels):
            raise ValueError('Invalid paired label code')
    joint = [(a, b) for a, b in zip(left, right) if a is not None and b is not None]
    changed = sum(a != b for a, b in joint)
    return {'planned_cases': len(left), 'joint_valid_cases': len(joint), 'changed_cases': changed,
            'joint_valid_coverage': len(joint) / len(left),
            'label_change_rate_on_joint_valid': changed / len(joint) if joint else None,
            'label_change_bounds_all_planned': [changed / len(left),
                (changed + len(left) - len(joint)) / len(left)]}


def paired_region_contrast(left_metrics, right_metrics):
    """Fractions minus means on matched regions, with failure bounds retained."""
    left = left_metrics['regions']
    right = right_metrics['regions']
    if [m['region'] for m in left] != [m['region'] for m in right] or len(left) != 2:
        raise ValueError('Arms must use the same two test regions in the same order')
    if [m['planned_cells'] for m in left] != [m['planned_cells'] for m in right]:
        raise ValueError('Arms must preserve identical planned denominators')
    a = left_metrics['equal_region_agreement_bounds']
    b = right_metrics['equal_region_agreement_bounds']
    return {'regions': [{'region': l['region'],
                'agreement_difference': r['agreement'] - l['agreement'],
                'fixed28_macro_f1_difference': r['fixed28_macro_f1'] - l['fixed28_macro_f1']}
            for l, r in zip(left, right)],
            'equal_region_agreement_difference': right_metrics['equal_region_agreement'] -
                left_metrics['equal_region_agreement'],
            'equal_region_fixed28_macro_f1_difference': right_metrics['equal_region_fixed28_macro_f1'] -
                left_metrics['equal_region_fixed28_macro_f1'],
            'agreement_difference_bounds': [b[0] - a[1], b[1] - a[0]]}


def new_ledger(requests):
    ids = [r['request_id'] for r in requests]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate planned request IDs')
    return {'schema': 'annotation47.submission_ledger.v1', 'execution_enabled': False,
            'entries': {request_id: {'request_id': request_id, 'state': 'prepared',
                'attempts': 0, 'events': []} for request_id in ids}}


def transition_submission(entry, event, evidence=None):
    """State-only guard. It cannot authorize or perform an actual submission.

    Every request has at most three attempts (initial plus two technical
    retries). An ambiguous outcome holds its reservation until documented proof
    of acceptance or no generation. Generated invalid/missing output is final.
    """
    evidence = deepcopy(evidence or {})
    result = deepcopy(entry)
    state = result['state']
    if event == 'submit_started':
        if state not in {'prepared', 'retryable'} or result['attempts'] >= 3:
            raise ValueError('Submission is not eligible, ambiguous or exhausted')
        result['state'] = 'submitting'
        result['attempts'] += 1
    elif event in {'submission_accepted', 'reconciled_accepted'}:
        allowed = {'submitting'} if event == 'submission_accepted' else {'ambiguous'}
        if state not in allowed or not (evidence.get('batch_id') or evidence.get('generation_id')):
            raise ValueError('Acceptance requires a durable provider receipt')
        result['state'] = 'accepted'
        result['acceptance_receipt'] = evidence
    elif event == 'submission_ambiguous':
        if state != 'submitting':
            raise ValueError('Only an in-flight submission can become ambiguous')
        result['state'] = 'ambiguous'
    elif event == 'no_generation_confirmed':
        if state not in {'submitting', 'ambiguous'} or evidence.get('no_generation_confirmed') is not True:
            raise ValueError('A retry requires explicit pre-generation proof')
        if evidence.get('provider_accepted') is not False or evidence.get('billed') is not False:
            raise ValueError('Unaccepted and unbilled pre-generation evidence is required')
        if not isinstance(evidence.get('source'), str) or not evidence['source']:
            raise ValueError('Proof source is required')
        result['state'] = 'retryable' if result['attempts'] < 3 else 'pre_generation_failed'
    elif event in {'result_valid', 'result_invalid', 'result_missing'}:
        if state != 'accepted':
            raise ValueError('A result requires a previously accepted submission')
        result['state'] = {'result_valid': 'completed_valid', 'result_invalid': 'completed_invalid',
                           'result_missing': 'completed_missing'}[event]
    else:
        raise ValueError('Unknown submission event')
    result['events'].append({'event': event, 'evidence': evidence})
    return result


def persist_submission_event(path, request_id, event, evidence=None):
    """Lock and fsync a ledger transition before a future caller may send/poll.

    This offline primitive does not make a paid executor available. The parent
    execution gate must separately verify explicit launch authorization and cap.
    """
    import fcntl
    path = Path(path)
    with path.with_suffix(path.suffix + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = strict_json(path.read_text())
        ledger['entries'][request_id] = transition_submission(
            ledger['entries'][request_id], event, evidence)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent,
                    prefix=path.name + '.', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(ledger, handle, indent=2, allow_nan=False)
                handle.write('\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return ledger
