# IRL Gaslight 5M Model

This directory trains an offline, approximately five-million-parameter model for defensive communication classification and curated response retrieval.

It is intentionally **not** a free-form chatbot. A model this small is better used to identify possible patterns, estimate context/tone/risk, choose a safe action category, and retrieve a human-written response from IRL Gaslight's existing library.

## Architecture

| Component | Value |
|---|---:|
| BPE vocabulary | 6,144 |
| Sequence length | 256 |
| Hidden width | 256 |
| Attention heads | 4 |
| Transformer layers | 5 |
| Feed-forward width | 768 |
| Trainable parameters | approximately 4.94M |
| Outputs | tactic, context, tone, risk, action, embedding |

The model uses multi-label classification for manipulation tactics and categorical classification for the other tasks. Its normalized embedding retrieves responses from the curated JSON library.

## Google Colab

Open [`notebooks/train_irl_gaslight_5m.ipynb`](https://colab.research.google.com/github/Dev2Creator/irl-gaslight/blob/main/notebooks/train_irl_gaslight_5m.ipynb) in Colab, select a T4 GPU, and run all cells.

## Local smoke test

    python -m pip install torch tokenizers numpy
    python ml/train_5m.py --epochs 1 --max-groups 40 --skip-export --output artifacts/smoke

## Full training

    python -m pip install -r ml/requirements-colab.txt
    python ml/train_5m.py --epochs 14 --batch-size 64 --output artifacts/irl-gaslight-5m

## Inference

    python ml/infer_5m.py \
      --model-dir artifacts/irl-gaslight-5m \
      --text "That never happened. You imagined it."

## Safety and privacy

- Training uses only the repository's curated public JSON collections and deterministic defensive augmentations.
- It never reads `~/.irl_gaslight.json`, incident logs, OAuth tokens, Google profiles, or other personal files.
- Outputs describe possible patterns, not diagnoses or proven intent.
- The existing rule-based detector remains the fallback until a trained model passes review.
- High-risk situations should route to trusted support or emergency resources rather than a clever comeback.

## Expected artifacts

    artifacts/irl-gaslight-5m/
    |-- model.pt
    |-- model.onnx
    |-- model.int8.onnx
    |-- tokenizer.json
    |-- config.json
    |-- labels.json
    |-- metrics.json
    |-- dataset.jsonl
    |-- response_catalog.json
    `-- response_embeddings.npy

The synthetic augmentation in this baseline is deliberately conservative. Before shipping the model as a default, review the dataset, add diverse human-labeled examples, and test false positives across dialects and ordinary disagreements.
