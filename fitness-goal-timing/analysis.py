"""Offline, standard-library-only synthetic experiment generation and analysis."""

import csv
import hashlib
import json
import math
import random
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parent
METRICS = {
    "retention_w4": "Week-four workout retention",
    "first_workout_d7": "First workout by day 7",
    "paid_d28": "Paid conversion by day 28",
    "error_d7": "Onboarding error by day 7",
}


def load_protocol():
    return json.loads((ROOT / "protocol.json").read_text(encoding="utf-8"))


def generate_accounts(protocol, scenario):
    """Assign first, then generate linked outcomes with a single fixed RNG."""
    rng = random.Random(protocol["seed"])
    n = protocol["accounts_per_arm"]
    arms = ["onboarding"] * n + ["after_workout"] * n
    rng.shuffle(arms)
    rows = []
    shared = protocol["shared"]
    for index, arm in enumerate(arms):
        # Fixed count and order of random draws prevents branching from changing
        # downstream streams. Sensitivity scenarios reuse these same uniforms.
        early_u, late_u, retention_u, paid_u, error_u = [rng.random() for _ in range(5)]
        early_day = rng.randint(1, 7)
        late_day = rng.randint(8, 21)
        retention_day = rng.randint(22, 28)
        paid_day = rng.randint(1, 28)
        error_day = rng.randint(0, 7)
        rates = protocol["control"] if arm == "onboarding" else protocol["scenarios"][scenario]
        early = early_u < rates["first_workout_by7"]
        late = (not early) and late_u < shared["late_first_workout_if_no_early"]
        first_day = early_day if early else late_day if late else None
        retention_probability = (
            rates["week4_given_early"] if early else shared["week4_given_late"] if late else 0
        )
        retained = retention_u < retention_probability
        paid = paid_u < shared["paid_by28"]
        error = error_u < shared["onboarding_error_by7"]
        prompt_day = 0 if arm == "onboarding" else first_day
        rows.append(
            {
                "account_id": f"SYN-{index + 1:06d}",
                "scenario": scenario,
                "arm": arm,
                "assignment_day": 0,
                "followup_days": 28,
                "prompt_seen": int(prompt_day is not None),
                "prompt_day": prompt_day,
                "first_workout_day": first_day,
                "week4_workout_day": retention_day if retained else None,
                "first_paid_day": paid_day if paid else None,
                "onboarding_error_day": error_day if error else None,
            }
        )
    return rows


def outcomes(row):
    def in_window(value, low, high):
        return value not in (None, "") and low <= int(value) <= high

    return {
        "retention_w4": int(in_window(row["week4_workout_day"], 22, 28)),
        "first_workout_d7": int(in_window(row["first_workout_day"], 0, 7)),
        "paid_d28": int(in_window(row["first_paid_day"], 0, 28)),
        "error_d7": int(in_window(row["onboarding_error_day"], 0, 7)),
    }


def wilson(successes, n, confidence=0.95):
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    p = successes / n
    scale = 1 + z * z / n
    center = (p + z * z / (2 * n)) / scale
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / scale
    return center - half, center + half


def difference_ci(control_successes, treatment_successes, nc, nt, confidence=0.95):
    pc, pt = control_successes / nc, treatment_successes / nt
    lc, uc = wilson(control_successes, nc, confidence)
    lt, ut = wilson(treatment_successes, nt, confidence)
    difference = pt - pc
    low = difference - math.sqrt((pt - lt) ** 2 + (uc - pc) ** 2)
    high = difference + math.sqrt((ut - pt) ** 2 + (pc - lc) ** 2)
    return difference * 100, low * 100, high * 100


def summarize(rows, protocol):
    grouped = {arm: [r for r in rows if r["arm"] == arm] for arm in ["onboarding", "after_workout"]}
    result = {}
    for key, label in METRICS.items():
        counts = {arm: sum(outcomes(r)[key] for r in group) for arm, group in grouped.items()}
        nc, nt = len(grouped["onboarding"]), len(grouped["after_workout"])
        difference, low, high = difference_ci(
            counts["onboarding"], counts["after_workout"], nc, nt, protocol["confidence_level"]
        )
        result[key] = {
            "label": label,
            "control_count": counts["onboarding"],
            "control_n": nc,
            "treatment_count": counts["after_workout"],
            "treatment_n": nt,
            "control_pct": counts["onboarding"] / nc * 100,
            "treatment_pct": counts["after_workout"] / nt * 100,
            "difference_pp": difference,
            "ci_low_pp": low,
            "ci_high_pp": high,
        }
    return result


def decide(metrics, protocol):
    retention, paid, error = [metrics[k] for k in ["retention_w4", "paid_d28", "error_d7"]]
    if retention["ci_high_pp"] < 0:
        return "RETAIN_CURRENT_RETENTION_HARM"
    if (
        paid["ci_high_pp"] < protocol["paid_noninferiority_margin_pp"]
        or error["ci_low_pp"] > protocol["error_noninferiority_margin_pp"]
    ):
        return "RETAIN_CURRENT_GUARDRAIL_HARM"
    if (
        retention["difference_pp"] >= protocol["retention_minimum_worthwhile_lift_pp"]
        and retention["ci_low_pp"] > 0
        and paid["ci_low_pp"] > protocol["paid_noninferiority_margin_pp"]
        and error["ci_high_pp"] < protocol["error_noninferiority_margin_pp"]
    ):
        return "SIMULATED_ROLLOUT"
    return "RETAIN_CURRENT_MORE_EVIDENCE"


def validate_rows(rows, protocol):
    assert len(rows) == 2 * protocol["accounts_per_arm"]
    assert len({r["account_id"] for r in rows}) == len(rows)
    for arm in ["onboarding", "after_workout"]:
        assert sum(r["arm"] == arm for r in rows) == protocol["accounts_per_arm"]
    for row in rows:
        assert row["followup_days"] == 28
        first = row["first_workout_day"]
        assert row["prompt_seen"] == int(row["prompt_day"] is not None)
        assert row["prompt_day"] == (0 if row["arm"] == "onboarding" else first)
        assert row["week4_workout_day"] is None or (
            first is not None and first < row["week4_workout_day"]
        )
    assert any(r["arm"] == "after_workout" and not r["prompt_seen"] for r in rows)


def run(output_dir=None):
    output_dir = Path(output_dir or ROOT / "outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol = load_protocol()
    results = {
        "label": protocol["label"],
        "seed": protocol["seed"],
        "protocol_sha256": hashlib.sha256((ROOT / "protocol.json").read_bytes()).hexdigest(),
        "scenarios": {},
    }
    table_rows = []
    for scenario in protocol["scenarios"]:
        rows = generate_accounts(protocol, scenario)
        validate_rows(rows, protocol)
        metrics = summarize(rows, protocol)
        exposure = {
            arm: sum(r["prompt_seen"] for r in rows if r["arm"] == arm)
            for arm in ["onboarding", "after_workout"]
        }
        results["scenarios"][scenario] = {
            "metrics": metrics,
            "prompt_seen": exposure,
            "decision": decide(metrics, protocol),
        }
        for metric, stats in metrics.items():
            table_rows.append({"scenario": scenario, "metric": metric, **stats})
        if scenario == "main_conflict":
            with (output_dir / "synthetic_accounts.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    with (output_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table_rows[0]))
        writer.writeheader()
        writer.writerows(table_rows)
    (output_dir / "results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return results


if __name__ == "__main__":
    result = run()
    for scenario, item in result["scenarios"].items():
        print(scenario, item["decision"])
        for metric in item["metrics"].values():
            print(
                f"  {metric['label']}: {metric['difference_pp']:+.2f} pp [{metric['ci_low_pp']:+.2f}, {metric['ci_high_pp']:+.2f}]"
            )
