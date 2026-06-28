"""Run offline inference with a trained IRL Gaslight 5M artifact bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer


OUTPUT_NAMES = ["tactics", "context", "tone", "risk", "action", "embedding"]


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - values.max(axis=-1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=-1, keepdims=True)


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--float-model", action="store_true", help="Use model.onnx instead of INT8.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise SystemExit("Install onnxruntime first: pip install onnxruntime") from exc

    model_dir = args.model_dir.resolve()
    labels = json.loads((model_dir / "labels.json").read_text(encoding="utf-8"))
    catalog = json.loads((model_dir / "response_catalog.json").read_text(encoding="utf-8"))
    response_embeddings = np.load(model_dir / "response_embeddings.npy")
    tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    encoded = tokenizer.encode(args.text)
    inputs = {
        "input_ids": np.asarray([encoded.ids], dtype=np.int64),
        "attention_mask": np.asarray([encoded.attention_mask], dtype=np.int64),
    }
    model_name = "model.onnx" if args.float_model else "model.int8.onnx"
    session = ort.InferenceSession(str(model_dir / model_name), providers=["CPUExecutionProvider"])
    raw = session.run(OUTPUT_NAMES, inputs)
    outputs = dict(zip(OUTPUT_NAMES, raw))
    tactic_scores = sigmoid(outputs["tactics"])[0]
    tactic_matches = [
        {"label": labels["tactics"][index], "confidence": round(float(score), 4)}
        for index, score in sorted(enumerate(tactic_scores), key=lambda pair: pair[1], reverse=True)
        if score >= args.threshold
    ]

    prediction: dict[str, object] = {"possible_tactics": tactic_matches}
    confidence_values: list[float] = []
    for name in ("context", "tone", "risk", "action"):
        probabilities = softmax(outputs[name])[0]
        index = int(probabilities.argmax())
        confidence = float(probabilities[index])
        confidence_values.append(confidence)
        prediction[name] = {"label": labels[f"{name}s"][index], "confidence": round(confidence, 4)}

    query_embedding = outputs["embedding"][0]
    query_embedding /= max(float(np.linalg.norm(query_embedding)), 1e-8)
    similarities = response_embeddings @ query_embedding
    top_indices = np.argsort(-similarities)[: args.top_k]
    prediction["responses"] = [
        {
            "response": catalog[index]["response"],
            "score": round(float(similarities[index]), 4),
            "source": catalog[index]["source"],
        }
        for index in top_indices
    ]
    prediction["uncertain"] = not tactic_matches and max(confidence_values, default=0.0) < 0.6
    prediction["notice"] = "Possible patterns, not a diagnosis or proof of intent."
    print(json.dumps(prediction, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
