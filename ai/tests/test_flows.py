"""pytest wrapper: every eval case must pass in deterministic rules mode, plus unit checks."""
import os

os.environ["NLU_MODE"] = "rules"

import pytest  # noqa: E402

from app import config  # noqa: E402
from app.responder import inr, ungrounded_numbers  # noqa: E402
from tests.run_eval import run  # noqa: E402

config.NLU_MODE = "rules"
RESULTS = run(verbose=False)


@pytest.mark.parametrize("result", RESULTS, ids=[r["id"] for r in RESULTS])
def test_eval_case(result):
    assert result["passed"], result["failures"]


def test_inr_grouping():
    assert inr(412300) == "₹4,12,300"
    assert inr(8450) == "₹8,450"


def test_grounding_guard_blocks_invented_numbers():
    payload = [{"emi_amount": 8450, "next_due_date": "2026-11-05"}]
    assert ungrounded_numbers("Your EMI is ₹8,450 due 5 November 2026.", payload) == []
    assert ungrounded_numbers("Your EMI is ₹9,000.", payload) == [9000]
