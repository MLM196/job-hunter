import argparse

from .notify import notify
from .pipeline import run
from .settings import load_env


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m jobhunter")
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run", help="find new jobs and prepare applications")
    run_cmd.add_argument("--dry-run", action="store_true", help="search and filter only; save nothing")
    run_cmd.add_argument("--limit", type=int, help="max new jobs this run (overrides config)")
    notify_cmd = sub.add_parser("notify", help="email the jobs found so far")
    notify_cmd.add_argument("--dry-run", action="store_true", help="print the email instead of sending it")
    args = parser.parse_args()
    load_env()

    if args.command == "run":
        run(dry_run=args.dry_run, limit=args.limit)
    else:
        notify(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
