"""Select abstention thresholds on validation only. No medical accuracy guarantee."""

import math


def probabilities(logits, temperature):
    if not logits or any(not math.isfinite(value) for value in logits):
        raise ValueError("Invalid logits")
    shifted = [(value - max(logits)) / temperature for value in logits]
    scores = [math.exp(value) for value in shifted]
    return [value / sum(scores) for value in scores]


def policy_statistics(logits, targets, policy):
    accepted = correct = 0
    for row, target in zip(logits, targets):
        scores = probabilities(row, policy["temperature"])
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        if (
            scores[ranked[0]] >= policy["minimum_score"]
            and scores[ranked[0]] - scores[ranked[1]] >= policy["minimum_margin"]
        ):
            accepted += 1
            correct += int(ranked[0] == target)
    return {
        "accepted": accepted,
        "total": len(targets),
        "coverage": accepted / len(targets) if targets else 0,
        "accuracy_on_accepted": correct / accepted if accepted else None,
    }


def choose_policy(validation_logits, validation_targets):
    if not validation_targets or len(validation_logits) != len(validation_targets):
        raise ValueError("Nonempty validation logits and targets required")
    classes = len(validation_logits[0])
    if classes < 2 or any(len(row) != classes for row in validation_logits):
        raise ValueError("At least two consistent classes required")
    if any(
        type(target) is not int or target not in range(classes) for target in validation_targets
    ):
        raise ValueError("Invalid validation targets")
    best = None
    for temperature in [0.75, 1.0, 1.5, 2.0]:
        for minimum_score in [0.55, 0.65, 0.75, 0.85, 0.95]:
            for minimum_margin in [0.05, 0.1, 0.2, 0.3]:
                policy = dict(
                    temperature=temperature,
                    minimum_score=minimum_score,
                    minimum_margin=minimum_margin,
                )
                stats = policy_statistics(validation_logits, validation_targets, policy)
                if stats["coverage"] < 0.25:
                    continue
                key = (
                    stats["accuracy_on_accepted"],
                    stats["coverage"],
                    minimum_score,
                    minimum_margin,
                )
                if best is None or key > best[0]:
                    best = key, policy, stats
    if best is None:
        raise ValueError(
            "No validation policy has sufficient coverage; improve the model before packaging"
        )
    return best[1], best[2]
