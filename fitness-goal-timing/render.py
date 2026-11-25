"""Render the shared result object into a PNG, editable memo and one-page PDF."""

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT
from analysis import ROOT, METRICS, load_protocol


def percent_text(metric, arm):
    value = Decimal(metric[arm + "_count"]) * 100 / Decimal(metric[arm + "_n"])
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) + "%"


def result_line(metric):
    return f"{metric['difference_pp']:+.2f} pp [{metric['ci_low_pp']:+.2f}, {metric['ci_high_pp']:+.2f}]"


def memo_content(result, protocol):
    main = result["scenarios"]["main_conflict"]
    unseen = protocol["accounts_per_arm"] - main["prompt_seen"]["after_workout"]
    paragraphs = [
        (
            "Decision",
            "Retain the onboarding goal prompt in this simulated case. The first-workout gain accompanies a clear decline in the primary retention metric. Test a shorter onboarding prompt in a separate follow-up experiment.",
        ),
        (
            "Product question and design",
            "Would moving the same optional weekly goal prompt until after the first completed workout improve sustained use? Randomize new eligible accounts before onboarding, with 20,000 per arm and 28 complete days of follow-up. Keep wording, skip option, workouts, prices and reminders identical. Goal capture does not change workout selection.",
        ),
        (
            "Frozen success criteria",
            "Recommend rollout only if retention improves by at least 1.50 percentage points and its 95% interval excludes zero, paid conversion has a lower bound above -1.00 point, and onboarding errors have an upper bound below +0.50 point. Clear retention or guardrail harm takes precedence. Otherwise retain current timing pending more evidence.",
        ),
        (
            "What the simulation shows",
            f"The primary outcome is a completed workout during days 22-28. All assigned accounts stay in every denominator, including {unseen:,} treatment accounts that never see the deferred prompt. Paid conversion and error intervals pass the prespecified guardrails. Intervals describe sampling variation within this synthetic model.",
        ),
        (
            "Interpretation and next bet",
            "Earlier goal-setting may support commitment, but this simulation cannot establish that mechanism. Inspect the path from first workout to return visits, then separately test lower-friction goal-setting. Never compare only prompt viewers or first-workout completers as if they remained randomized.",
        ),
        (
            "Scope and provenance",
            "SYNTHETIC educational exercise by Aviv Emanuel. Rates, thresholds and sample size are chosen assumptions. Seed 20261125 was fixed before the first run. This case uses fictional accounts and illustrates growth-experiment decision-making. It reports no real app effect or production rollout. The public source provides framing only.",
        ),
    ]
    return paragraphs


def draw_chart(result, destination):
    metrics = result["scenarios"]["main_conflict"]["metrics"]
    fig, ax = plt.subplots(figsize=(12, 8.6), dpi=180)
    fig.patch.set_facecolor("#ffffff")
    fig.subplots_adjust(left=0.32, right=0.76, top=0.665, bottom=0.19)
    keys = list(METRICS)
    row_colors = ["#ab443b", "#266b88", "#506b74", "#506b74"]
    verdicts = [
        "Missed retention target",
        "Diagnostic only",
        "Passed conversion guardrail",
        "Passed error guardrail",
    ]
    labels = [
        "Primary KPI: Week 4 workout retention",
        "Activation: First workout by day 7",
        "Guardrail: Paid conversion by day 28",
        "Guardrail: Onboarding error by day 7",
    ]
    for index, key in enumerate(keys):
        y = 3 - index
        m = metrics[key]
        ax.errorbar(
            m["difference_pp"],
            y,
            xerr=[[m["difference_pp"] - m["ci_low_pp"]], [m["ci_high_pp"] - m["difference_pp"]]],
            fmt="o",
            color=row_colors[index],
            capsize=5,
            linewidth=2.1,
            markersize=7,
        )
        label = (
            labels[index]
            + "\n"
            + f"Control {percent_text(m, 'control')}  |  Treatment {percent_text(m, 'treatment')}"
        )
        ax.text(
            -0.045,
            y,
            label,
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=10,
            linespacing=1.7,
            color="#26363c",
        )
        ax.text(
            1.05,
            y,
            f"{m['difference_pp']:+.2f} pp\n[{m['ci_low_pp']:+.2f}, {m['ci_high_pp']:+.2f}]",
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=10,
            linespacing=1.45,
            color="#26363c",
        )
        ax.text(
            1.05,
            y - 0.28,
            verdicts[index],
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="top",
            fontsize=8.4,
            weight="semibold",
            color=row_colors[index],
        )
    for y, threshold, title in [
        (3, 1.5, "Target +1.50 pp"),
        (1, -1.0, "Floor −1.00 pp"),
        (0, 0.5, "Ceiling +0.50 pp"),
    ]:
        ax.vlines(
            threshold, y - 0.25, y + 0.24, color="#9b713a", linestyles="dashed", linewidth=1.4
        )
        left = threshold < 0
        ax.annotate(
            title,
            (threshold, y + 0.24),
            xytext=(-4 if left else 4, 4),
            textcoords="offset points",
            ha="right" if left else "left",
            va="bottom",
            fontsize=8.5,
            weight="semibold",
            color="#795624",
        )
    ax.axvline(0, color="#a2abb0", linewidth=1)
    ax.set_xlim(-4.7, 8.4)
    ax.set_ylim(-0.55, 3.6)
    ax.set_yticks([])
    ax.set_xticks([-4, -2, 0, 2, 4, 6, 8])
    ax.tick_params(axis="x", labelsize=10, colors="#506068", length=0, pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel(
        "Treatment effect vs. control (percentage points)",
        fontsize=11,
        labelpad=14,
        color="#26363c",
    )
    fig.text(
        0.06,
        0.947,
        "SIMULATED DATA  /  FITNESS APP A/B TEST",
        fontsize=10,
        weight="bold",
        color="#266b88",
    )
    fig.text(
        0.06,
        0.901,
        "Goal-prompt timing: activation rose, retention fell",
        fontsize=21,
        weight="bold",
        color="#162d38",
    )
    fig.text(
        0.06,
        0.853,
        "A  /  We asked users to set a weekly goal",
        fontsize=11,
        weight="bold",
        color="#266b88",
    )
    fig.text(
        0.075,
        0.810,
        "Random assignment",
        fontsize=11,
        weight="bold",
        color="#26363c",
        va="center",
        bbox=dict(boxstyle="round,pad=.50", fc="#f1f4f6", ec="#b9c8ce"),
    )
    for target_y in (0.830, 0.790):
        ax.annotate(
            "",
            xy=(0.350, target_y),
            xytext=(0.230, 0.810),
            xycoords="figure fraction",
            textcoords="figure fraction",
            arrowprops=dict(
                arrowstyle="-|>", color="#266b88", lw=1.5, mutation_scale=13, shrinkA=0, shrinkB=0
            ),
        )
    fig.text(
        0.361,
        0.830,
        "Onboarding (early)",
        fontsize=10,
        color="#26363c",
        va="center",
        bbox=dict(boxstyle="round,pad=.43", fc="#eaf3f8", ec="none"),
    )
    fig.text(
        0.361,
        0.790,
        "After the first completed workout (deferred)",
        fontsize=10,
        color="#26363c",
        va="center",
        bbox=dict(boxstyle="round,pad=.43", fc="#eef2f0", ec="none"),
    )
    fig.text(0.73, 0.830, "CONTROL", fontsize=8.5, weight="bold", color="#506068", va="center")
    fig.text(0.73, 0.790, "TREATMENT", fontsize=8.5, weight="bold", color="#506068", va="center")
    fig.text(
        0.06,
        0.751,
        "20,000 accounts per arm. Intention-to-treat: all assigned accounts counted, even if they never saw the prompt.",
        fontsize=9,
        color="#506068",
    )
    fig.text(
        0.06,
        0.722,
        "B  /  KPI READOUT: TREATMENT VS. CONTROL",
        fontsize=10,
        weight="bold",
        color="#266b88",
    )
    fig.text(
        0.06,
        0.689,
        "Dot = estimated difference   •   Capped bar = 95% confidence interval   •   Brown dash = decision threshold   •   Grey zero line = no difference",
        fontsize=9,
        color="#506068",
    )
    fig.text(
        0.06,
        0.09,
        "Decision: hold rollout. Keep the early prompt; test a lighter version.",
        fontsize=12,
        weight="bold",
        color="#162d38",
    )
    fig.text(
        0.06,
        0.055,
        "Compare the retention target to the dot, the conversion floor to the left end of the bar, and the error ceiling to the right end.",
        fontsize=8.7,
        color="#506068",
    )
    fig.text(
        0.06,
        0.030,
        "Week-four retention = at least one workout on days 22–28. This simulation does not estimate real product effects.",
        fontsize=8.7,
        color="#506068",
    )
    fig.savefig(
        destination,
        metadata={"Software": "Synthetic fitness goal experiment v1.3"},
        facecolor="white",
    )
    plt.close(fig)


def render(output_dir=None):
    output = Path(output_dir or ROOT / "outputs")
    result = json.loads((output / "results.json").read_text(encoding="utf-8"))
    protocol = load_protocol()
    paragraphs = memo_content(result, protocol)
    metrics = result["scenarios"]["main_conflict"]["metrics"]
    rows = [["Outcome", "Onboarding", "Deferred", "Difference [95% CI]"]]
    for m in metrics.values():
        rows.append(
            [m["label"], percent_text(m, "control"), percent_text(m, "treatment"), result_line(m)]
        )
    markdown = "# When should a fitness app ask for a goal?\n\n**SYNTHETIC PORTFOLIO EXERCISE | V1 | 25 November 2026**\n\n"
    for heading, content in paragraphs[:3]:
        markdown += f"## {heading}\n\n{content}\n\n"
    markdown += "| Outcome | Onboarding | Deferred | Difference [95% CI] |\n|---|---:|---:|---:|\n"
    for row in rows[1:]:
        markdown += "| " + " | ".join(row) + " |\n"
    markdown += "\nAll rates use 20,000 accounts per arm. pp = percentage points. Newcombe / Wilson 95% intervals.\n\n"
    for heading, content in paragraphs[3:]:
        markdown += f"## {heading}\n\n{content}\n\n"
    markdown += "Context: [Aviv Emanuel’s public retention case](https://www.avivemanuel.com/post/loyal-users-early-behaviors).\n"
    (output / "decision_memo.md").write_text(markdown, encoding="utf-8", newline="\n")
    styles = {
        "tag": ParagraphStyle(
            "tag",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#266b88"),
            spaceAfter=9,
        ),
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=25,
            textColor=colors.HexColor("#162d38"),
            spaceAfter=13,
        ),
        "heading": ParagraphStyle(
            "heading",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceBefore=9,
            spaceAfter=3,
            textColor=colors.HexColor("#162d38"),
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#293d45"),
        ),
        "small": ParagraphStyle(
            "small",
            fontName="Helvetica",
            fontSize=7.4,
            leading=10,
            textColor=colors.HexColor("#53666d"),
        ),
    }
    story = [
        Paragraph("SYNTHETIC PORTFOLIO EXERCISE | V1 | 25 NOVEMBER 2026", styles["tag"]),
        Paragraph("When should a fitness app<br/>ask for a goal?", styles["title"]),
    ]
    for heading, content in paragraphs[:3]:
        story.extend([Paragraph(heading, styles["heading"]), Paragraph(content, styles["body"])])
    story.append(Spacer(1, 12))
    table = Table(rows, colWidths=[163, 63, 61, 217], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0f3")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#243b45")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#bbcbd0")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#dbe3e6")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            table,
            Spacer(1, 5),
            Paragraph(
                "All rates use 20,000 accounts per arm. pp = percentage points. Newcombe / Wilson 95% intervals.",
                styles["small"],
            ),
        ]
    )
    for heading, content in paragraphs[3:]:
        story.extend([Paragraph(heading, styles["heading"]), Paragraph(content, styles["body"])])
    story.extend(
        [
            Spacer(1, 9),
            Paragraph(
                'Context only: <link href="https://www.avivemanuel.com/post/loyal-users-early-behaviors" color="#266b88">Aviv Emanuel’s public retention case</link>. Analysis, assumptions and exact counts accompany this memo.',
                styles["small"],
            ),
        ]
    )
    doc = SimpleDocTemplate(
        str(output / "decision_memo.pdf"),
        pagesize=(612, 792),
        rightMargin=54,
        leftMargin=54,
        topMargin=36,
        bottomMargin=30,
        title="SYNTHETIC - Fitness goal timing decision memo",
        author="Aviv Emanuel",
        invariant=1,
    )
    doc.build(story)
    draw_chart(result, output / "results_chart.png")
    return paragraphs


if __name__ == "__main__":
    render()
    print("Rendered memo PDF, editable Markdown source, and standalone chart.")
