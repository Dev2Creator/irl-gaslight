from pathlib import Path

import pytest


torch = pytest.importorskip("torch")
pytest.importorskip("tokenizers")

from ml.train_5m import (  # noqa: E402
    ACTIONS,
    CONTEXTS,
    RISKS,
    TONES,
    Gaslight5M,
    ModelConfig,
    build_examples,
    parameter_count,
)


def test_model_respects_five_million_parameter_budget():
    data_dir = Path(__file__).parents[1] / "irl_gaslight" / "data"
    _, tactics, _ = build_examples(data_dir)
    labels = {
        "tactics": tactics,
        "contexts": CONTEXTS,
        "tones": TONES,
        "risks": RISKS,
        "actions": ACTIONS,
    }
    count = parameter_count(Gaslight5M(ModelConfig(), labels))
    assert count == 4_941_095
    assert 4_800_000 <= count <= 5_200_000


def test_augmented_groups_do_not_cross_splits():
    data_dir = Path(__file__).parents[1] / "irl_gaslight" / "data"
    examples, _, _ = build_examples(data_dir)
    groups = {}
    for example in examples:
        base_group = example.group.rsplit(":v", 1)[0]
        groups.setdefault(base_group, set()).add(example.split)
    assert all(len(splits) == 1 for splits in groups.values())
    assert {example.split for example in examples} == {"train", "validation", "test"}