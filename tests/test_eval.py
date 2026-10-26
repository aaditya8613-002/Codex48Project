from eval.run_eval import evaluate


def test_accuracy_targets_hold_on_the_30_item_set():
    report = evaluate(use_ai=False)
    assert report["items"] == 30
    assert report["recall"] >= 0.8, [r for r in report["rows"] if r["missed"]]
    assert report["false_alarms_on_clean"] == 0, [r for r in report["rows"] if not r["expected"] and r["raised"]]
