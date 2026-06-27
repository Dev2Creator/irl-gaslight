# IRL Gaslight

### Spot the spin. Hold the line. Keep your receipts.

IRL Gaslight is a local-first defensive communication CLI by Anika Mukherjee / Dev2Creator. It helps people recognize manipulation patterns, rehearse calm boundaries, answer bullies without becoming abusive, and keep factual private notes.

It does not teach gaslighting, coercion, humiliation, retaliation, or psychological abuse.

## Install for development

    python -m venv .venv
    .venv\Scripts\activate
    python -m pip install -e .

Open the IRL-Wisdom-inspired interactive command palette:

    irl-gaslight

## Commands

    irl-gaslight spot "That never happened. You imagined it."
    irl-gaslight boundary --context work
    irl-gaslight comeback --tone dry
    irl-gaslight rehearse
    irl-gaslight log
    irl-gaslight history
    irl-gaslight clear-log
    irl-gaslight daily
    irl-gaslight favorites
    irl-gaslight favorites --remove 1
    irl-gaslight resources
    irl-gaslight upgrade

Add `--copy` or `-c` to `spot`, `boundary`, `comeback`, and `daily`. In interactive mode, every lesson card also offers Copy, Save to favorites, Back, and Exit actions.

## What is inside

- Responsive ANSI title art and the warm IRL-Wisdom terminal palette
- Typer commands and a Questionary arrow-key palette
- Rich lesson panels, tables, streaks, favorites, and local history
- 110 curated defensive entries across tactics, boundaries, comebacks, scenarios, and daily grounding
- School, work, family, dating, friendship, and online examples
- PyPI version check and in-app upgrade command
- Local-only state in `~/.irl_gaslight.json`
- No account, telemetry, database, or cloud service

The detector is a phrase-based educational aid, not a diagnosis. Context, repetition, power imbalance, and safety matter more than one sentence.

## Safety

Do not use comebacks when they would increase danger. If someone is threatening, stalking, controlling, or violent, prioritize distance, trusted support, and local emergency or abuse-support services.

## Author

Created by Anika Mukherjee / Dev2Creator.

Licensed under AGPL-3.0-or-later.