"""Accuracy harness: planted mistakes found vs false alarms on clean items.

Usage (from the project root):
    python -m eval.run_eval                 # exact rules + claim checks only (no API key needed)
    python -m eval.run_eval --ai            # also run Gemini checks (needs GEMINI_API_KEY and embeddings)
    python -m eval.run_eval --min-recall 0.8 --max-false-alarms 0   # exit code 1 if missed
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, make_engine
from app.kit import load_kit
from app.models import *  # noqa: F401,F403  (register tables)
from app.review import run_review

ROOT = Path(__file__).resolve().parent.parent
EVAL_DATE = date(2026, 10, 25)  # fixed so results do not change as facts expire


def evaluate(use_ai: bool = False) -> dict:
    from sqlalchemy import create_engine

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    org_id = load_kit(session, ROOT / "sample_kit" / "northwind.json", embed=use_ai)

    items = json.loads((ROOT / "eval" / "testset.json").read_text(encoding="utf-8"))["items"]
    expected_total = found_total = 0
    false_alarms = extra_on_planted = 0
    rows = []
    for item in items:
        result = run_review(session, org_id, item["text"], use_ai=use_ai, persist=False, today=EVAL_DATE)
        raised = [f["rule_id"] for f in result["findings"]]
        expect = item["expect"]
        hit = [e for e in expect if e in raised]
        missed = [e for e in expect if e not in raised]
        extras = [r for r in raised if r not in expect]
        expected_total += len(expect)
        found_total += len(hit)
        if expect:
            extra_on_planted += len(extras)
        else:
            false_alarms += len(raised)
        rows.append({"id": item["id"], "text": item["text"], "expected": expect, "raised": raised,
                     "missed": missed, "unexpected": extras})

    clean_items = sum(1 for i in items if not i["expect"])
    return {
        "items": len(items),
        "planted_mistakes": expected_total,
        "found": found_total,
        "recall": round(found_total / expected_total, 3) if expected_total else None,
        "clean_items": clean_items,
        "false_alarms_on_clean": false_alarms,
        "extra_findings_on_planted_items": extra_on_planted,
        "ai_used": use_ai,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true", help="include Gemini checks")
    ap.add_argument("--min-recall", type=float, default=None)
    ap.add_argument("--max-false-alarms", type=int, default=None)
    ap.add_argument("--json", type=str, default="", help="write the full report to this file")
    args = ap.parse_args()

    report = evaluate(use_ai=args.ai)
    for r in report["rows"]:
        status = "ok " if not r["missed"] and (r["expected"] or not r["raised"]) else "BAD"
        print(f"[{status}] #{r['id']:>2} expected={r['expected']} raised={r['raised']}")
    print()
    print(f"Planted mistakes found : {report['found']}/{report['planted_mistakes']}  (recall {report['recall']:.0%})")
    print(f"False alarms on {report['clean_items']} clean items: {report['false_alarms_on_clean']}")
    print(f"Extra findings on planted items: {report['extra_findings_on_planted_items']}")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")

    failed = False
    if args.min_recall is not None and (report["recall"] or 0) < args.min_recall:
        print(f"FAIL: recall below {args.min_recall:.0%}")
        failed = True
    if args.max_false_alarms is not None and report["false_alarms_on_clean"] > args.max_false_alarms:
        print(f"FAIL: more than {args.max_false_alarms} false alarms")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
