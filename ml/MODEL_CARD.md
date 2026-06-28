# Model Card: IRL Gaslight 5M

## Summary

IRL Gaslight 5M is a compact multi-task transformer for defensive communication classification and curated response retrieval. The architecture contains 4,941,095 trainable parameters and exports to an approximately 5.3 MB dynamically quantized ONNX model.

The repository contains training code, not a pretrained production checkpoint. Metrics must be generated and reviewed for every trained artifact.

## Intended uses

- Flag possible manipulation-language patterns for user review.
- Estimate broad context, response tone, risk level, and next-action category.
- Retrieve a human-written boundary or grounded response.
- Run offline on an ordinary laptop.

## Out-of-scope uses

- Diagnosing a person, relationship, or mental-health condition.
- Proving intent, abuse, guilt, or deception.
- Teaching coercion, harassment, retaliation, humiliation, or gaslighting.
- Replacing emergency, legal, medical, safeguarding, or professional support.
- Automatically acting against another person.

## Architecture

- Byte-level BPE tokenizer with a 6,144-token embedding budget.
- Maximum sequence length of 256 tokens.
- Five pre-normalized transformer encoder layers.
- Hidden width 256, four attention heads, feed-forward width 768.
- Multi-label tactic head and categorical context, tone, risk, and action heads.
- A normalized 256-dimensional retrieval embedding.

## Evaluation requirements

Do not ship a checkpoint based only on training loss. Review test metrics, per-tactic false positives, ordinary disagreement examples, dialect variation, spelling noise, and urgent-risk routing. Manually inspect retrieved responses.

## Limitations

The bundled dataset is small and partly augmented. It cannot represent every culture, dialect, relationship, disability, or power dynamic. Confidence is not certainty. A phrase can be awkward without being manipulative, and manipulation can occur without any known marker phrase.

## Privacy

Training reads only repository data under `irl_gaslight/data`. It does not read local incident history, OAuth credentials, shared IRL profiles, clipboard contents, or telemetry.