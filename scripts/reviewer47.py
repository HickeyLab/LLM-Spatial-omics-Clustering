#!/usr/bin/env python3
"""Offline reviewer refresh entry point. Does not submit cloud or model jobs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.revision.reviewer47.common import read_json, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path,
        default=ROOT / "configs/reviewer_annotation47_credit_batch_v1.json")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Build exact blinded B004 DRAFT bodies")
    prepare.add_argument("--source-bundle", type=Path, required=True)
    prepare.add_argument("--h5ad", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify", help="Validate hashes, joins, evidence and coverage offline")
    verify.add_argument("--bundle", type=Path, required=True)
    preflight = sub.add_parser("preflight", help="Write disabled preparation certificate with unresolved gates")
    preflight.add_argument("--bundle", type=Path, required=True)
    preflight.add_argument("--donor-observation", type=Path)
    preflight.add_argument("--output", type=Path, required=True)
    offline = sub.add_parser("offline", help="Run label-separated scoring; never make annotation calls")
    offline.add_argument("--analysis", choices=["granularity", "baselines", "calibration"], required=True)
    offline.add_argument("--h5ad", type=Path)
    offline.add_argument("--output", type=Path, required=True)
    observe = sub.add_parser("donor-status", help="Read producer metadata without submitting or changing it")
    observe.add_argument("--external-root", type=Path, required=True)
    observe.add_argument("--output", type=Path, required=True)
    observe.add_argument("--verify-hashes", action="store_true")
    admit = sub.add_parser("donor-admit", help="Check a completed producer export against an approved contract")
    admit.add_argument("--receipt", type=Path, required=True)
    admit.add_argument("--contract", type=Path, required=True)
    admit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    config = read_json(args.protocol)
    bundle = ROOT / config["b004_bundle"]
    if args.command == "prepare":
        from scripts.revision.reviewer47.prepare import prepare_b004
        result = prepare_b004(ROOT, args.source_bundle, args.h5ad, args.output, args.protocol)
        result = {k: v for k, v in result.items() if k not in {"files", "source_proofs", "markers", "ontology"}}
    elif args.command == "verify":
        from scripts.revision.reviewer47.preflight import verify_prepared
        result = verify_prepared(args.bundle, args.protocol)
    elif args.command == "preflight":
        from scripts.revision.reviewer47.preflight import preparation_certificate
        observation = read_json(args.donor_observation) if args.donor_observation else None
        result = preparation_certificate(args.bundle, args.protocol, args.output, donor_observation=observation)
    elif args.command == "offline":
        from scripts.revision.reviewer47 import offline
        if args.analysis == "baselines":
            if args.h5ad is None:
                parser.error("baselines requires the exact admitted --h5ad source")
            result = offline.run_classical_baselines(bundle, args.output, args.h5ad)
        elif args.analysis == "granularity":
            result = offline.run_granularity(bundle, args.output, tuple(config["granularity"]["targets"]))
        else:
            result = offline.run_agreement_calibration(bundle, args.output)
    else:
        from scripts.revision.reviewer47 import donors
        if args.output.exists():
            raise FileExistsError("Preserve the prior receipt; choose a new output")
        if args.command == "donor-status":
            markers = read_json(bundle / "protocol.json")["markers"]
            contract = config["donors"]["spatialsort"]
            result = donors.observe_external_campaign(args.external_root, markers,
                approved_contract=contract, verify_hashes=args.verify_hashes)
        else:
            contract = read_json(args.contract)
            approved = config["donors"]["spatialsort"]
            for name in ("expected_sweeps", "dmh_iter", "required_seeds", "primary_seed"):
                if contract.get(name) != approved[name]:
                    raise ValueError("Donor contract differs from the user-approved protocol: " + name)
            if contract.get("donor") not in config["donors"]["cohorts"]:
                raise ValueError("Donor is outside the approved B005/B006 scope")
            result = donors.admit_spatialsort_handoff(read_json(args.receipt), contract)
        write_json(args.output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
