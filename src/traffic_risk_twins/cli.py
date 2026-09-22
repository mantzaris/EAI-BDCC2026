import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description='Bounded Stage 1 traffic-risk research')
    commands = parser.add_subparsers(dest='action',required=True)
    audit = commands.add_parser('audit-data')
    audit.add_argument('--raw',default='data/raw')
    ledger = commands.add_parser('budget-run')
    ledger.add_argument('--ledger',default='results/compute_ledger.jsonl')
    ledger.add_argument('--reserve-seconds',required=True,type=float)
    ledger.add_argument('command',nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'audit-data':
        from .ingestion import audit_pems
        result = audit_pems(args.raw)
        print(json.dumps({k:v for k,v in result.items() if k != 'splits'},indent=2))
    elif args.action == 'budget-run':
        from .compute_ledger import run_budgeted
        command = args.command[1:] if args.command[0] == '--' else args.command
        sys.exit(run_budgeted(args.ledger,command,args.reserve_seconds))


if __name__ == '__main__':
    main()
