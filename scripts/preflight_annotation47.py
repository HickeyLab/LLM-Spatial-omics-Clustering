#!/usr/bin/env python3
"""Verify the sealed preparation offline. This command cannot submit requests."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_spatial_omics_clustering.revision.annotation47_admission import preparation_certificate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--metadata', type=Path, required=True)
    p.add_argument('--account-receipt', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Preserve the existing certificate. Choose a new output path.')
    protocol = json.loads(args.protocol.read_text())
    account = json.loads(args.account_receipt.read_text()) if args.account_receipt else None
    certificate = preparation_certificate(protocol, args.bundle, args.metadata, account)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(certificate, indent=2) + '\n')
    print(json.dumps({k: certificate[k] for k in ['status', 'launch_ready', 'annotation_calls', 'jobs_submitted', 'bundle_manifest_sha256', 'launch_blockers']}, indent=2))
    print(json.dumps({k: certificate['budget'][k] for k in ['central_scenario_usd', 'reservation_usd', 'within_proposed_ceiling']}, indent=2))


if __name__ == '__main__':
    main()
