"""Check substantive integrity and reproducibility; core checks use stdlib only."""

import csv
import hashlib
import importlib.util
import json
import math
import sqlite3
import tempfile
from copy import deepcopy
from pathlib import Path
from analysis import (
    ROOT,
    METRICS,
    load_protocol,
    run,
    generate_accounts,
    summarize,
    decide,
    difference_ci,
)


def validate():
    protocol = load_protocol()
    expected = json.loads((ROOT / "outputs/results.json").read_text(encoding="utf-8"))
    checks = []
    with tempfile.TemporaryDirectory() as folder:
        actual = run(folder)
        assert actual == expected
        for name in ["synthetic_accounts.csv", "results.csv", "results.json"]:
            assert (Path(folder) / name).read_bytes() == (ROOT / "outputs" / name).read_bytes()
    checks.append("Fresh deterministic rerun matches numeric outputs and account CSV byte for byte")
    with (ROOT / "outputs/synthetic_accounts.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 40000 and len({r["account_id"] for r in rows}) == 40000
    csv_metrics = summarize(rows, protocol)
    assert csv_metrics == expected["scenarios"]["main_conflict"]["metrics"]
    checks.append(
        "CSV-derived estimates agree with JSON; 40,000 unique accounts and 20,000 per arm"
    )
    connection = sqlite3.connect(":memory:")
    columns = list(rows[0])
    numeric = set(columns) - {"account_id", "scenario", "arm"}
    definitions = ", ".join(name + (" INTEGER" if name in numeric else " TEXT") for name in columns)
    connection.execute("CREATE TABLE accounts (" + definitions + ")")
    tuples = [
        tuple(
            None if r[name] == "" else int(r[name]) if name in numeric else r[name]
            for name in columns
        )
        for r in rows
    ]
    connection.executemany(
        "INSERT INTO accounts VALUES (" + ",".join("?" for _ in columns) + ")", tuples
    )
    for arm, n, *counts in connection.execute((ROOT / "metrics.sql").read_text(encoding="utf-8")):
        prefix = "control" if arm == "onboarding" else "treatment"
        assert n == 20000
        for metric, count in zip(METRICS, counts):
            assert count == csv_metrics[metric][prefix + "_count"]
    connection.close()
    checks.append("Independent SQLite metric query matches all eight event counts and denominators")
    unseen = sum(r["arm"] == "after_workout" and r["prompt_seen"] == "0" for r in rows)
    assert unseen == 6242
    checks.append("All 6,242 unexposed treatment accounts remain included")
    # A separate unpooled normal approximation should be close at these counts.
    for m in csv_metrics.values():
        p = m["control_count"] / m["control_n"]
        q = m["treatment_count"] / m["treatment_n"]
        half = (
            1.959963984540054
            * math.sqrt(p * (1 - p) / m["control_n"] + q * (1 - q) / m["treatment_n"])
            * 100
        )
        assert abs((m["difference_pp"] - half) - m["ci_low_pp"]) < 0.02
        assert abs((m["difference_pp"] + half) - m["ci_high_pp"]) < 0.02
    d, lo, hi = difference_ci(0, 0, 20, 20)
    assert d == 0 and lo < 0 < hi
    checks.append("Interval cross-check within 0.02 pp; zero-event boundary retains uncertainty")
    decisions = {key: item["decision"] for key, item in expected["scenarios"].items()}
    assert decisions == {
        "main_conflict": "RETAIN_CURRENT_RETENTION_HARM",
        "null": "RETAIN_CURRENT_MORE_EVIDENCE",
        "aligned_benefit": "SIMULATED_ROLLOUT",
    }
    guarded = deepcopy(expected["scenarios"]["aligned_benefit"]["metrics"])
    guarded["paid_d28"]["ci_high_pp"] = -1.1
    assert decide(guarded, protocol) == "RETAIN_CURRENT_GUARDRAIL_HARM"
    uncertain = deepcopy(expected["scenarios"]["aligned_benefit"]["metrics"])
    uncertain["paid_d28"]["ci_low_pp"] = -1.1
    assert decide(uncertain, protocol) == "RETAIN_CURRENT_MORE_EVIDENCE"
    checks.append(
        "Conflicting, null, aligned-benefit, guardrail-harm and uncertain-guardrail decisions checked"
    )
    memo = (ROOT / "outputs/decision_memo.md").read_text(encoding="utf-8")
    for m in csv_metrics.values():
        assert (
            f"{m['difference_pp']:+.2f} pp [{m['ci_low_pp']:+.2f}, {m['ci_high_pp']:+.2f}]" in memo
        )
    checks.append("Editable memo contains every calculated difference and interval")
    if importlib.util.find_spec("fitz"):
        import fitz

        pdf = fitz.open(ROOT / "outputs/decision_memo.pdf")
        assert len(pdf) == 1
        text = "".join(page.get_text() for page in pdf)
        for m in csv_metrics.values():
            assert (
                f"{m['difference_pp']:+.2f} pp [{m['ci_low_pp']:+.2f}, {m['ci_high_pp']:+.2f}]"
                in text
            )
        assert "SYNTHETIC" in text and "6,242" in text
        checks.append(
            "One-page PDF contains every calculated difference, interval and synthetic label"
        )
    report = {
        "status": "PASS",
        "checks": checks,
        "decisions": decisions,
        "protocol_sha256": expected["protocol_sha256"],
    }
    (ROOT / "outputs/validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    validate()
