"""Executable study entry point. Commands fail rather than silently skip gates."""
import argparse
import json


def main():
    parser=argparse.ArgumentParser(prog="temporal_evidence")
    commands=parser.add_subparsers(dest="command",required=True)
    commands.add_parser("check-environment")
    acquisition=commands.add_parser("acquire-data")
    acquisition.add_argument("--datasets",nargs="+",choices=["wesad","ppg_dalia"],required=True)
    acquisition.add_argument("--local-archive")
    acquisition.add_argument("--author-source",action="store_true")
    synthetic=commands.add_parser("generate-synthetic")
    synthetic.add_argument("--config",default="configs/synthetic.yaml")
    inventory=commands.add_parser("inventory-data")
    inventory.add_argument("--datasets",nargs="+",default=["wesad","ppg_dalia"])
    prepare=commands.add_parser("prepare-features")
    prepare.add_argument("--config",default="configs/minimum_study.yaml")
    prepare.add_argument("--datasets",nargs="+")
    validate=commands.add_parser("validate-core")
    validate.add_argument("--config",default="configs/minimum_study.yaml")
    validate.add_argument("--graph",action="store_true")
    args=parser.parse_args()
    if args.command=="check-environment":
        from temporal_evidence.environment import check_environment
        print(json.dumps(check_environment(),indent=2))
    elif args.command=="acquire-data":
        from temporal_evidence.data.acquire import acquire
        if args.local_archive and len(args.datasets)!=1:
            parser.error("Local archive requires exactly one dataset")
        for dataset in args.datasets:
            acquire(dataset,args.local_archive,args.author_source)
    elif args.command=="generate-synthetic":
        from temporal_evidence.synthetic.generator import generate_all
        print(f"Generated {len(generate_all()['subjects'])} virtual subjects")
    elif args.command=="inventory-data":
        from temporal_evidence.data.adapters import inventory
        for dataset in args.datasets:
            print(f"Inventoried {dataset}: {len(inventory(dataset)['subjects'])} subjects")
    elif args.command=="prepare-features":
        from temporal_evidence.data.prepare import prepare
        print(f"Prepared {len(prepare(args.config,args.datasets))} base episodes")
    elif args.command=="validate-core":
        from temporal_evidence.environment import validate_core
        validate_core(args.graph)
        print("Temporal fixtures passed for all five conditions")


if __name__=="__main__":
    main()
