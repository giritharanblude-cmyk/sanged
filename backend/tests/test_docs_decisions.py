"""The Phase 0 blocking decisions must stay recorded in the docs.

T-000/Step 0.0 requires Q-15, Q-16, Q-20, Q-24 and Q-27 to be answered
before Phase 1. This test fails if a decision is removed from either the
build plan or the architecture record.
"""
import os
import re
from pathlib import Path

import pytest

BLOCKING_QUESTIONS = ("Q-15", "Q-16", "Q-20", "Q-24", "Q-27")


def _docs_root() -> Path:
    """Locate the directory holding the two documents.

    Inside the API container the repository is not present, so the dev stack
    mounts ./docs read-only and points SANGAD_DOCS_ROOT at it. When the tests
    run straight from a checkout, the docs sit next to the backend package.
    """
    configured = os.environ.get("SANGAD_DOCS_ROOT")
    if configured:
        return Path(configured)
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "docs" / "SANGAD_BUILD_PLAN.md").is_file():
            return candidate / "docs"
    raise RuntimeError(
        "Cannot locate the docs directory. Set SANGAD_DOCS_ROOT to the directory "
        "containing SANGAD_BUILD_PLAN.md and SANGAD_ARCHITECTURE_v0_3.md."
    )


DOCS_ROOT = _docs_root()
BUILD_PLAN = DOCS_ROOT / "SANGAD_BUILD_PLAN.md"
ARCHITECTURE = DOCS_ROOT / "SANGAD_ARCHITECTURE_v0_3.md"


def _build_plan_step_0_0() -> list[str]:
    text = BUILD_PLAN.read_text(encoding="utf-8")
    section = text.split("### Step 0.0", 1)[1].split("###", 1)[0]
    return section.splitlines()


DECISION_COLUMNS = 3


def test_build_plan_step_0_0_boxes_are_all_ticked() -> None:
    """Every Step 0.0 checkbox must be checked, not left open."""
    boxes = [line for line in _build_plan_step_0_0() if line.lstrip().startswith("- [")]
    assert boxes, "Step 0.0 has no checkbox lines"
    unchecked = [line for line in boxes if not line.lstrip().startswith("- [x]")]
    assert not unchecked, f"Step 0.0 still has unchecked questions: {unchecked}"
    assert len(boxes) == len(BLOCKING_QUESTIONS)


def test_build_plan_step_0_0_records_every_question() -> None:
    text = "\n".join(_build_plan_step_0_0())
    for question in BLOCKING_QUESTIONS:
        assert question in text, f"{question} is missing from the build plan Step 0.0"


def test_architecture_records_the_answers() -> None:
    """Architecture section 9.1 must carry a decision for each question."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert "### 9.1 Answers" in text, "architecture has no recorded-answers section"

    section = text.split("### 9.1 Answers", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if re.match(r"^\|\s*Q-\d+", line)]
    recorded = {re.match(r"^\|\s*(Q-\d+)", row).group(1) for row in rows}  # type: ignore[union-attr]

    assert recorded == set(BLOCKING_QUESTIONS), (
        f"architecture 9.1 records {sorted(recorded)}, expected {sorted(BLOCKING_QUESTIONS)}"
    )
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        # | # | Decision | Rationale |
        assert len(cells) == DECISION_COLUMNS
        assert cells[1], "decision cell is empty"
        assert cells[2], "rationale cell is empty"


@pytest.mark.parametrize("question", BLOCKING_QUESTIONS)
def test_answered_questions_are_not_still_marked_open(question: str) -> None:
    """A decided question must not remain a '- [ ]' checkbox."""
    text = BUILD_PLAN.read_text(encoding="utf-8")
    section = text.split("### Step 0.0", 1)[1].split("###", 1)[0]
    line = next(line for line in section.splitlines() if question in line)
    assert line.lstrip().startswith("- [x]"), f"{question} is still open: {line}"
