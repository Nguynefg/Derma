"""Policy selection on synthetic logits only; does not measure a medical model."""

import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    "derma_model_policy", Path(__file__).resolve().parents[2] / "research/model_policy.py"
)
policy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy_module)


def test_policy_selected_from_validation_is_deterministic():
    logits = [[4.0, 0.0], [0.0, 4.0], [3.0, 0.0], [0.0, 3.0]]
    targets = [0, 1, 0, 1]
    policy, stats = policy_module.choose_policy(logits, targets)
    assert stats["coverage"] == 1 and stats["accuracy_on_accepted"] == 1
    assert (policy, stats) == policy_module.choose_policy(logits, targets)
    # Evaluating separate held-out data cannot change the frozen policy.
    saved = policy.copy()
    test = policy_module.policy_statistics([[0.0, 4.0]], [0], policy)
    assert test["accuracy_on_accepted"] == 0 and saved == policy


@pytest.mark.parametrize(
    "logits,targets",
    [([], []), ([[0.0, 0.0]], [0]), ([[float("nan"), 0.0]], [0]), ([[1.0, 0.0]], [3])],
)
def test_invalid_or_uninformative_validation_cannot_create_policy(logits, targets):
    with pytest.raises(ValueError):
        policy_module.choose_policy(logits, targets)
