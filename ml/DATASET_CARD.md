# Dataset Card: IRL Gaslight Defensive Baseline

## Sources

The builder reads five public, curated project collections:

- `tactics.json`
- `boundaries.json`
- `comebacks.json`
- `scenarios.json`
- `daily.json`

It also adds a small set of healthy-disagreement and neutral-language controls.

## Tasks

Each example contains text plus labels for possible tactics, context, response tone, risk, and recommended action. Some examples also reference a curated response for retrieval.

## Augmentation

Deterministic variants add casing changes, punctuation removal, conversational wrappers, contractions, and limited spelling noise. Augmentation never creates instructions for manipulating or harming another person.

## Splitting

Variants from the same source group always stay in the same train, validation, or test split. The split is a stable SHA-256 group hash using an 80/10/10 target.

## Private data exclusion

The builder never reads `~/.irl_gaslight.json`, `~/.irl`, Google OAuth files, incident logs, user profiles, or other home-directory content.

## Known gaps

This is a starter dataset, not a claim of universal coverage. Before release, add independently reviewed human examples, dialect and accessibility coverage, ambiguous negatives, and high-quality labels from multiple reviewers.