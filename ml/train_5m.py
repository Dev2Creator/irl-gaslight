"""Train the tiny IRL Gaslight defensive-language model.

This model classifies possible communication patterns and retrieves curated
responses. It does not generate free-form advice or diagnose people.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, processors, trainers
from torch import Tensor, nn
from torch.utils.data import DataLoader, Dataset


SPECIAL_TOKENS = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
CONTEXTS = ["general", "work", "school", "family", "friendship", "dating", "online"]
TONES = ["neutral", "calm", "dry", "direct"]
RISKS = ["ordinary", "concerning", "urgent"]
ACTIONS = ["clarify", "set-boundary", "document", "disengage", "seek-support"]


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = 6144
    max_length: int = 256
    d_model: int = 256
    nhead: int = 4
    num_layers: int = 5
    dim_feedforward: int = 768
    dropout: float = 0.1


@dataclass
class Example:
    text: str
    tactics: list[str]
    context: str
    tone: str
    risk: str
    action: str
    response: str
    group: str
    split: str = ""


def read_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def stable_split(group: str) -> str:
    bucket = int(hashlib.sha256(group.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "test"


def infer_context(text: str) -> str:
    lowered = text.casefold()
    keyword_map = {
        "work": ("coworker", "manager", "deadline", "work", "hr", "meeting", "teammate"),
        "school": ("classmate", "teacher", "assignment", "class", "school", "student"),
        "family": ("relative", "family", "parent", "sibling", "home"),
        "friendship": ("friend", "best friend"),
        "dating": ("date", "partner", "boyfriend", "girlfriend", "exes"),
        "online": ("online", "post", "message", "chat", "block", "account", "password"),
    }
    for context, words in keyword_map.items():
        if any(word in lowered for word in words):
            return context
    return "general"


def infer_action(text: str) -> str:
    lowered = text.casefold()
    if any(word in lowered for word in ("emergency", "threat", "stalk", "trusted", "report", "support")):
        return "seek-support"
    if any(word in lowered for word in ("document", "write", "record", "save", "preserve", "screenshot")):
        return "document"
    if any(word in lowered for word in ("leave", "end", "block", "disengage", "stop responding", "pause")):
        return "disengage"
    if any(word in lowered for word in ("boundary", "do not", "will not", "not willing", "no is")):
        return "set-boundary"
    return "clarify"


def infer_risk(text: str) -> str:
    lowered = text.casefold()
    if any(word in lowered for word in ("kill", "hurt you", "threat", "stalk", "unsafe", "afraid to leave")):
        return "urgent"
    if any(word in lowered for word in ("punish", "control", "owe me", "no one will believe", "ignore you", "insult")):
        return "concerning"
    return "ordinary"


def detected_tactics(text: str, tactics: list[dict[str, Any]]) -> list[str]:
    lowered = text.casefold()
    return [
        item["name"]
        for item in tactics
        if any(str(marker).casefold() in lowered for marker in item.get("markers", []))
    ]


def typo_variant(text: str, seed: str) -> str:
    rng = random.Random(seed)
    words = text.split()
    candidates = [index for index, word in enumerate(words) if len(word) >= 6]
    if not candidates:
        return text
    index = rng.choice(candidates)
    word = words[index]
    position = rng.randrange(1, len(word) - 1)
    words[index] = word[:position] + word[position + 1 :]
    return " ".join(words)


def augment(text: str, group: str) -> list[str]:
    clean = " ".join(text.split())
    variants = [
        clean,
        clean.casefold(),
        clean.rstrip(".!?"),
        f'They said, "{clean}"',
        f"Someone told me: {clean}",
        typo_variant(clean, group),
    ]
    swaps = {
        "you are": "you're",
        "do not": "don't",
        "cannot": "can't",
        "I am": "I'm",
        "it is": "it's",
    }
    contracted = clean
    for old, new in swaps.items():
        contracted = re.sub(re.escape(old), new, contracted, flags=re.IGNORECASE)
    variants.append(contracted)
    result: list[str] = []
    seen: set[str] = set()
    for value in variants:
        normalized = value.strip()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def build_examples(data_dir: Path) -> tuple[list[Example], list[str], list[dict[str, Any]]]:
    tactics_data = read_json(data_dir / "tactics.json")
    boundaries = read_json(data_dir / "boundaries.json")
    comebacks = read_json(data_dir / "comebacks.json")
    scenarios = read_json(data_dir / "scenarios.json")
    daily = read_json(data_dir / "daily.json")
    tactic_labels = [str(item["name"]) for item in tactics_data]
    base: list[Example] = []
    catalog: list[dict[str, Any]] = []

    for tactic in tactics_data:
        name = str(tactic["name"])
        response = str(tactic["response"])
        exit_move = str(tactic["exit"])
        for marker_index, marker in enumerate(tactic.get("markers", [])):
            group = f"tactic:{slug(name)}:{marker_index}"
            statement = str(marker)
            base.append(
                Example(
                    text=statement,
                    tactics=[name],
                    context="general",
                    tone="calm",
                    risk=infer_risk(statement + " " + tactic["description"]),
                    action=infer_action(exit_move),
                    response=response,
                    group=group,
                )
            )
        catalog.append(
            {
                "query": " ".join(str(marker) for marker in tactic.get("markers", [])),
                "response": response,
                "context": "general",
                "tone": "calm",
                "action": infer_action(exit_move),
                "source": f"tactic:{name}",
            }
        )

    for index, item in enumerate(boundaries):
        context = str(item.get("context", "general"))
        line = str(item["line"])
        prompt = f"I need a boundary for this {context} situation: {line}"
        base.append(
            Example(prompt, [], context, "calm", "ordinary", "set-boundary", line, f"boundary:{index}")
        )
        catalog.append(
            {
                "query": prompt,
                "response": line,
                "context": context,
                "tone": "calm",
                "action": "set-boundary",
                "source": f"boundary:{index}",
            }
        )

    for index, item in enumerate(comebacks):
        tone = str(item.get("tone", "calm"))
        line = str(item["line"])
        prompt = f"Someone mocked or insulted me. Give me a {tone} response."
        base.append(
            Example(prompt, [], "general", tone, "ordinary", "disengage", line, f"comeback:{index}")
        )
        catalog.append(
            {
                "query": prompt,
                "response": line,
                "context": "general",
                "tone": tone,
                "action": "disengage",
                "source": f"comeback:{index}",
            }
        )

    for index, item in enumerate(scenarios):
        prompt = str(item["prompt"])
        response = str(item["model"])
        context = infer_context(prompt)
        labels = detected_tactics(prompt, tactics_data)
        action = infer_action(response + " " + item.get("why", ""))
        base.append(
            Example(prompt, labels, context, "calm", infer_risk(prompt), action, response, f"scenario:{index}")
        )
        catalog.append(
            {
                "query": prompt,
                "response": response,
                "context": context,
                "tone": "calm",
                "action": action,
                "source": f"scenario:{index}",
            }
        )

    neutral_statements = [
        "I remember it differently; can we compare notes?",
        "I disagree, but I want to understand your reasoning.",
        "Take the time you need and answer tomorrow.",
        "No problem, your no is enough.",
        "I made a mistake and I am sorry for the impact.",
        "What outcome would feel fair to both of us?",
        "You can keep your password private.",
        "Let us discuss one specific issue at a time.",
        "I need a quiet hour before we continue this conversation.",
        "Thank you for correcting me; I will update the document.",
        "We do not need to agree to remain respectful.",
        "I will not share that story because it was told in confidence.",
        "Would you prefer feedback now or after the meeting?",
        "I can help for thirty minutes, but I cannot take over the task.",
        "Your feelings make sense even though my view is different.",
        "Please send the updated deadline in writing.",
        "I accept your decision and will not keep asking.",
        "Let us pause and return when neither of us is shouting.",
        "I do not know enough yet, so I want to verify the facts.",
        "You are allowed to change your mind.",
    ]
    for index, statement in enumerate(neutral_statements):
        base.append(
            Example(statement, [], infer_context(statement), "neutral", "ordinary", "clarify", "", f"neutral:{index}")
        )

    for index, item in enumerate(daily):
        text = str(item["text"])
        base.append(Example(text, [], "general", "neutral", "ordinary", "clarify", "", f"daily:{index}"))

    expanded: list[Example] = []
    for item in base:
        split = stable_split(item.group)
        for variant_index, text in enumerate(augment(item.text, item.group)):
            expanded.append(
                Example(
                    text=text,
                    tactics=item.tactics,
                    context=item.context if item.context in CONTEXTS else "general",
                    tone=item.tone if item.tone in TONES else "neutral",
                    risk=item.risk if item.risk in RISKS else "ordinary",
                    action=item.action if item.action in ACTIONS else "clarify",
                    response=item.response,
                    group=f"{item.group}:v{variant_index}",
                    split=split,
                )
            )
    return expanded, tactic_labels, catalog


def save_dataset(examples: list[Example], output_dir: Path, labels: dict[str, list[str]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "dataset.jsonl").open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(asdict(example), ensure_ascii=True) + "\n")
    (output_dir / "labels.json").write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")


def train_tokenizer(texts: Iterable[str], output_path: Path, config: ModelConfig) -> Tokenizer:
    tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=config.vocab_size, min_frequency=2, special_tokens=SPECIAL_TOKENS)
    tokenizer.train_from_iterator(texts, trainer=trainer)
    tokenizer.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        special_tokens=[("[CLS]", tokenizer.token_to_id("[CLS]")), ("[SEP]", tokenizer.token_to_id("[SEP]"))],
    )
    tokenizer.enable_truncation(max_length=config.max_length)
    tokenizer.enable_padding(
        length=config.max_length,
        pad_id=tokenizer.token_to_id("[PAD]"),
        pad_token="[PAD]",
    )
    tokenizer.save(str(output_path))
    return tokenizer


class GaslightDataset(Dataset[dict[str, Tensor]]):
    def __init__(self, examples: list[Example], tokenizer: Tokenizer, labels: dict[str, list[str]]) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.tactic_to_id = {value: index for index, value in enumerate(labels["tactics"])}
        self.context_to_id = {value: index for index, value in enumerate(labels["contexts"])}
        self.tone_to_id = {value: index for index, value in enumerate(labels["tones"])}
        self.risk_to_id = {value: index for index, value in enumerate(labels["risks"])}
        self.action_to_id = {value: index for index, value in enumerate(labels["actions"])}

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, Tensor]:
        example = self.examples[index]
        encoded = self.tokenizer.encode(example.text)
        tactic_targets = torch.zeros(len(self.tactic_to_id), dtype=torch.float32)
        for label in example.tactics:
            if label in self.tactic_to_id:
                tactic_targets[self.tactic_to_id[label]] = 1.0
        return {
            "input_ids": torch.tensor(encoded.ids, dtype=torch.long),
            "attention_mask": torch.tensor(encoded.attention_mask, dtype=torch.long),
            "tactics": tactic_targets,
            "context": torch.tensor(self.context_to_id[example.context], dtype=torch.long),
            "tone": torch.tensor(self.tone_to_id[example.tone], dtype=torch.long),
            "risk": torch.tensor(self.risk_to_id[example.risk], dtype=torch.long),
            "action": torch.tensor(self.action_to_id[example.action], dtype=torch.long),
        }


class Gaslight5M(nn.Module):
    def __init__(self, config: ModelConfig, labels: dict[str, list[str]]) -> None:
        super().__init__()
        self.config = config
        self.token_embedding = nn.Embedding(config.vocab_size, config.d_model, padding_idx=0)
        self.position_embedding = nn.Embedding(config.max_length, config.d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.nhead,
            dim_feedforward=config.dim_feedforward,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(
            layer,
            num_layers=config.num_layers,
            enable_nested_tensor=False,
        )
        self.final_norm = nn.LayerNorm(config.d_model)
        self.dropout = nn.Dropout(config.dropout)
        self.heads = nn.ModuleDict(
            {
                "tactics": nn.Linear(config.d_model, len(labels["tactics"])),
                "context": nn.Linear(config.d_model, len(labels["contexts"])),
                "tone": nn.Linear(config.d_model, len(labels["tones"])),
                "risk": nn.Linear(config.d_model, len(labels["risks"])),
                "action": nn.Linear(config.d_model, len(labels["actions"])),
            }
        )

    def forward(self, input_ids: Tensor, attention_mask: Tensor) -> dict[str, Tensor]:
        positions = torch.arange(input_ids.shape[1], device=input_ids.device).unsqueeze(0)
        hidden = self.token_embedding(input_ids) + self.position_embedding(positions)
        hidden = self.encoder(hidden, src_key_padding_mask=attention_mask == 0)
        pooled = self.final_norm(hidden[:, 0])
        dropped = self.dropout(pooled)
        return {name: head(dropped) for name, head in self.heads.items()} | {"embedding": pooled}


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def move_batch(batch: dict[str, Tensor], device: torch.device) -> dict[str, Tensor]:
    return {key: value.to(device) for key, value in batch.items()}


def compute_loss(
    outputs: dict[str, Tensor],
    batch: dict[str, Tensor],
    tactic_pos_weight: Tensor,
) -> Tensor:
    tactic_loss = nn.functional.binary_cross_entropy_with_logits(
        outputs["tactics"],
        batch["tactics"],
        pos_weight=tactic_pos_weight,
    )
    categorical = sum(
        nn.functional.cross_entropy(outputs[name], batch[name])
        for name in ("context", "tone", "risk", "action")
    )
    return 1.5 * tactic_loss + categorical


def classification_metrics(predictions: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    predicted = predictions.astype(bool)
    expected = targets.astype(bool)
    tp = np.logical_and(predicted, expected).sum(axis=0)
    fp = np.logical_and(predicted, np.logical_not(expected)).sum(axis=0)
    fn = np.logical_and(np.logical_not(predicted), expected).sum(axis=0)
    per_label = 2 * tp / np.maximum(2 * tp + fp + fn, 1)
    micro_tp, micro_fp, micro_fn = tp.sum(), fp.sum(), fn.sum()
    micro = 2 * micro_tp / max(2 * micro_tp + micro_fp + micro_fn, 1)
    return {"tactic_micro_f1": float(micro), "tactic_macro_f1": float(per_label.mean())}


@torch.no_grad()
def evaluate(
    model: Gaslight5M,
    loader: DataLoader,
    device: torch.device,
    tactic_pos_weight: Tensor,
) -> dict[str, float]:
    model.eval()
    losses: list[float] = []
    tactic_predictions: list[np.ndarray] = []
    tactic_targets: list[np.ndarray] = []
    correct = {name: 0 for name in ("context", "tone", "risk", "action")}
    total = 0
    for raw_batch in loader:
        batch = move_batch(raw_batch, device)
        outputs = model(batch["input_ids"], batch["attention_mask"])
        losses.append(float(compute_loss(outputs, batch, tactic_pos_weight).item()))
        tactic_predictions.append((torch.sigmoid(outputs["tactics"]) >= 0.5).cpu().numpy())
        tactic_targets.append(batch["tactics"].cpu().numpy())
        total += batch["input_ids"].shape[0]
        for name in correct:
            correct[name] += int((outputs[name].argmax(dim=-1) == batch[name]).sum().item())
    metrics = classification_metrics(np.concatenate(tactic_predictions), np.concatenate(tactic_targets))
    metrics["loss"] = float(np.mean(losses))
    metrics.update({f"{name}_accuracy": value / max(total, 1) for name, value in correct.items()})
    return metrics


def cosine_schedule(step: int, total_steps: int, warmup_steps: int) -> float:
    if step < warmup_steps:
        return step / max(warmup_steps, 1)
    progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
    return 0.5 * (1.0 + math.cos(math.pi * progress))


def train_model(
    model: Gaslight5M,
    train_loader: DataLoader,
    validation_loader: DataLoader,
    device: torch.device,
    output_dir: Path,
    epochs: int,
    learning_rate: float,
    patience: int,
    tactic_pos_weight: Tensor,
) -> dict[str, float]:
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = max(len(train_loader) * epochs, 1)
    warmup_steps = max(total_steps // 10, 1)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lambda step: cosine_schedule(step, total_steps, warmup_steps),
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    best_loss = float("inf")
    best_metrics: dict[str, float] = {}
    stale_epochs = 0
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for raw_batch in train_loader:
            batch = move_batch(raw_batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type=device.type, enabled=device.type == "cuda"):
                outputs = model(batch["input_ids"], batch["attention_mask"])
                loss = compute_loss(outputs, batch, tactic_pos_weight)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            running_loss += float(loss.item())
        metrics = evaluate(model, validation_loader, device, tactic_pos_weight)
        print(
            f"epoch={epoch:02d} train_loss={running_loss / max(len(train_loader), 1):.4f} "
            f"val_loss={metrics['loss']:.4f} tactic_micro_f1={metrics['tactic_micro_f1']:.4f}"
        )
        if metrics["loss"] < best_loss - 1e-4:
            best_loss = metrics["loss"]
            best_metrics = metrics
            stale_epochs = 0
            torch.save(model.state_dict(), output_dir / "model.pt")
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                print(f"early stopping after {epoch} epochs")
                break
    model.load_state_dict(torch.load(output_dir / "model.pt", map_location=device, weights_only=True))
    return best_metrics


@torch.no_grad()
def encode_texts(
    model: Gaslight5M,
    tokenizer: Tokenizer,
    texts: list[str],
    device: torch.device,
    batch_size: int = 128,
) -> np.ndarray:
    model.eval()
    rows: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        encodings = tokenizer.encode_batch(texts[start : start + batch_size])
        ids = torch.tensor([encoding.ids for encoding in encodings], dtype=torch.long, device=device)
        masks = torch.tensor([encoding.attention_mask for encoding in encodings], dtype=torch.long, device=device)
        embeddings = model(ids, masks)["embedding"]
        embeddings = nn.functional.normalize(embeddings, dim=-1)
        rows.append(embeddings.cpu().numpy().astype(np.float32))
    return np.concatenate(rows)


def export_onnx(model: Gaslight5M, config: ModelConfig, output_dir: Path) -> None:
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError as exc:
        raise RuntimeError("Install onnx and onnxruntime before export.") from exc

    class ExportWrapper(nn.Module):
        def __init__(self, wrapped: Gaslight5M) -> None:
            super().__init__()
            self.wrapped = wrapped

        def forward(self, input_ids: Tensor, attention_mask: Tensor) -> tuple[Tensor, ...]:
            outputs = self.wrapped(input_ids, attention_mask)
            return (
                outputs["tactics"],
                outputs["context"],
                outputs["tone"],
                outputs["risk"],
                outputs["action"],
                outputs["embedding"],
            )

    model = model.cpu().eval()
    wrapper = ExportWrapper(model)
    dummy_ids = torch.ones((1, config.max_length), dtype=torch.long)
    dummy_mask = torch.ones((1, config.max_length), dtype=torch.long)
    onnx_path = output_dir / "model.onnx"
    torch.onnx.export(
        wrapper,
        (dummy_ids, dummy_mask),
        onnx_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["tactics", "context", "tone", "risk", "action", "embedding"],
        dynamic_axes={
            "input_ids": {0: "batch"},
            "attention_mask": {0: "batch"},
            "tactics": {0: "batch"},
            "context": {0: "batch"},
            "tone": {0: "batch"},
            "risk": {0: "batch"},
            "action": {0: "batch"},
            "embedding": {0: "batch"},
        },
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    quantize_dynamic(onnx_path, output_dir / "model.int8.onnx", weight_type=QuantType.QInt8)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("artifacts/irl-gaslight-5m"))
    parser.add_argument("--epochs", type=int, default=14)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-groups", type=int, default=0, help="Limit source groups for a smoke test.")
    parser.add_argument("--skip-export", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = args.repo_root.resolve() / "irl_gaslight" / "data"
    examples, tactic_labels, catalog = build_examples(data_dir)
    if args.max_groups:
        allowed = sorted({item.group.rsplit(":v", 1)[0] for item in examples})[: args.max_groups]
        examples = [item for item in examples if item.group.rsplit(":v", 1)[0] in allowed]
        allowed_prefixes = tuple(allowed)
        catalog = [item for item in catalog if str(item["source"]).startswith(allowed_prefixes)] or catalog[:8]
    labels = {
        "tactics": tactic_labels,
        "contexts": CONTEXTS,
        "tones": TONES,
        "risks": RISKS,
        "actions": ACTIONS,
    }
    save_dataset(examples, output_dir, labels)
    train_examples = [item for item in examples if item.split == "train"]
    validation_examples = [item for item in examples if item.split == "validation"]
    test_examples = [item for item in examples if item.split == "test"]
    if not validation_examples or not test_examples:
        raise RuntimeError("Dataset split is empty. Increase --max-groups or use the full dataset.")
    print(
        f"examples train={len(train_examples)} validation={len(validation_examples)} "
        f"test={len(test_examples)}"
    )
    config = ModelConfig()
    tokenizer = train_tokenizer((item.text for item in train_examples), output_dir / "tokenizer.json", config)
    train_dataset = GaslightDataset(train_examples, tokenizer, labels)
    validation_dataset = GaslightDataset(validation_examples, tokenizer, labels)
    test_dataset = GaslightDataset(test_examples, tokenizer, labels)
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
        num_workers=0,
    )
    validation_loader = DataLoader(validation_dataset, batch_size=args.batch_size, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, num_workers=0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Gaslight5M(config, labels).to(device)
    tactic_counts = torch.zeros(len(tactic_labels), dtype=torch.float32)
    tactic_to_id = {value: index for index, value in enumerate(tactic_labels)}
    for example in train_examples:
        for tactic in example.tactics:
            if tactic in tactic_to_id:
                tactic_counts[tactic_to_id[tactic]] += 1
    tactic_pos_weight = (
        (len(train_examples) - tactic_counts) / tactic_counts.clamp_min(1)
    ).clamp(1, 20).to(device)
    count = parameter_count(model)
    print(f"device={device} trainable_parameters={count:,}")
    if not 4_800_000 <= count <= 5_200_000:
        raise RuntimeError(f"Parameter budget missed: {count:,}")
    best_validation = train_model(
        model,
        train_loader,
        validation_loader,
        device,
        output_dir,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        patience=args.patience,
        tactic_pos_weight=tactic_pos_weight,
    )
    test_metrics = evaluate(model, test_loader, device, tactic_pos_weight)
    report = {
        "parameters": count,
        "device": str(device),
        "dataset": {
            "train": len(train_examples),
            "validation": len(validation_examples),
            "test": len(test_examples),
        },
        "validation": best_validation,
        "test": test_metrics,
    }
    (output_dir / "config.json").write_text(json.dumps(asdict(config), indent=2) + "\n", encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    query_texts = [str(item["query"]) for item in catalog]
    embeddings = encode_texts(model, tokenizer, query_texts, device)
    np.save(output_dir / "response_embeddings.npy", embeddings)
    (output_dir / "response_catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    if not args.skip_export:
        export_onnx(model, config, output_dir)
    print(json.dumps(report, indent=2))
    print(f"artifacts={output_dir}")


if __name__ == "__main__":
    main()
