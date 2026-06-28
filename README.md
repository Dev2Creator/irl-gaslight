<div align="center">

# IRL Gaslight

### Spot the spin. Hold the line. Keep your receipts.

A warm, keyboard-driven defensive communication CLI for recognizing manipulation, rehearsing boundaries, answering bullies without becoming one, and keeping factual local notes.

[![PyPI](https://img.shields.io/pypi/v/irl-gaslight?style=flat-square&color=E47C55&label=PyPI)](https://pypi.org/project/irl-gaslight/)
[![Python](https://img.shields.io/pypi/pyversions/irl-gaslight?style=flat-square&color=D7C0AA)](https://pypi.org/project/irl-gaslight/)
[![License](https://img.shields.io/github/license/Dev2Creator/irl-gaslight?style=flat-square&color=614B39)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Dev2Creator/irl-gaslight?style=flat-square&color=3478F6)](https://github.com/Dev2Creator/irl-gaslight/stargazers)

[Install](#install) · [Explore](#what-is-inside) · [Commands](#commands) · [Identity](#shared-irl-identity-and-google-oauth) · [Safety](#safety-first)

</div>

---

    ██╗ ██████╗  ██╗
    ██║ ██╔══██╗ ██║        IRL GASLIGHT
    ██║ ██████╔╝ ██║        ─────────────
    ██║ ██╔══██╗ ██║        A calmer answer,
    ██║ ██║  ██║ ███████╗   right when pressure hits.
    ╚═╝ ╚═╝  ╚═╝ ╚══════╝

IRL Gaslight turns a terminal window into a small reality-check toolkit. Open the command palette, choose what happened, and leave with a response you can actually say—not another argument designed to exhaust you.

It does **not** teach gaslighting, coercion, humiliation, retaliation, or psychological abuse.

## Install

    pip install --upgrade irl-gaslight

Then open the interactive experience:

    irl-gaslight

Use the arrow keys to move and press Enter to choose. On first launch, the shared IRL identity ritual can create your local profile and optionally link Google.

## What is inside

| Path | What you get |
|---|---|
| Pattern check | Phrase-based signals for 20 manipulation tactics |
| Boundaries | Calm lines with consequences you control |
| Comebacks | Calm, dry, and direct answers without abuse |
| Rehearsal | Practice against realistic pressure scenarios |
| Incident log | Factual notes stored only on your machine |
| Daily grounding | One deterministic reality check each day |
| Favorites | A personal response shelf stored locally |
| Safety resources | Clear signals for stepping beyond a comeback |
| Shared identity | Name, pronunciation, pronouns, avatar, and oath |
| Google OAuth | Optional local account link shared across IRL tools |

The library contains **110 curated defensive entries** across work, school, family, dating, friendship, and online situations. The interface includes a daily streak, clipboard support, favorites, responsive ANSI title art, and the warm burnt-orange IRL-Wisdom command-palette aesthetic.

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
    irl-gaslight resources
    irl-gaslight upgrade

Add <code>--copy</code> or <code>-c</code> to supported response commands:

    irl-gaslight boundary --context school --copy

Interactive lesson cards also offer Copy, Save to favorites, Back, and Exit actions.

## Shared IRL identity and Google OAuth

IRL Gaslight uses the same local identity system as IRL Wisdom. A profile created in one ecosystem CLI can appear in the others.

    irl-gaslight profile
    irl-gaslight profile edit
    irl-gaslight profile reset
    irl-gaslight avatar
    irl-gaslight oath
    irl-gaslight oauth configure path/to/client_secret.json
    irl-gaslight oauth login
    irl-gaslight oauth status
    irl-gaslight oauth logout

The Google flow uses OAuth 2.0 Authorization Code with PKCE, a random state value, and a temporary localhost callback. The imported OAuth client is stored locally in `~/.irl/google_client.json`, tokens in `~/.irl/google_oauth.json`, and profile data in `~/.irl/profile.json`. Secrets are never committed or bundled into the package.

Google linking is optional. Cancelling, going offline, or skipping login does not block the defensive tools.

For a browserless terminal:

    irl-gaslight oauth login --no-browser

## The upgrade ritual

IRL Gaslight checks PyPI, compares versions, and asks before installing:

    irl-gaslight upgrade

For scripts and confident terminals:

    irl-gaslight upgrade --yes

## How it works

    irl-gaslight
    ├── Typer commands
    ├── Questionary command palette
    ├── Rich terminal rendering
    ├── Local JSON defensive library
    ├── irl_identity
    │   ├── first-launch profile ritual
    │   ├── avatars and Wisdom oath
    │   └── Google OAuth with PKCE
    ├── ~/.irl_gaslight.json
    │   ├── favorites
    │   ├── incident notes
    │   └── daily streak
    └── ~/.irl
        ├── profile.json
        └── google_oauth.json

There is no application database, telemetry, or cloud sync. Gaslight state, the shared profile, and OAuth tokens stay on the local device.

## Safety first

The detector is a phrase-based educational aid, not a diagnosis. Context, repetition, power imbalance, and safety matter more than one sentence.

Do not use a comeback when it could increase danger. If someone is threatening, stalking, controlling, or violent, prioritize distance, trusted support, and local emergency or abuse-support services. Use `irl-gaslight resources` for the built-in safety checklist.

## Train the 5M offline model

The optional ML workspace trains a ~4.94M-parameter classifier and curated-response retriever without reading private logs or OAuth data.

- [Open the one-click Colab notebook](https://colab.research.google.com/github/Dev2Creator/irl-gaslight/blob/main/notebooks/train_irl_gaslight_5m.ipynb)
- [Read the model training guide](ml/README.md)

## Development

    git clone https://github.com/Dev2Creator/irl-gaslight.git
    cd irl-gaslight
    python -m venv .venv
    .venv\Scripts\activate
    python -m pip install -e .
    irl-gaslight

Build and validate a release:

    python -m pytest -q
    python -m build
    python -m twine check dist/*

## Author

Created by **Anika Mukherjee**

Email: [cuteypieanika@gmail.com](mailto:cuteypieanika@gmail.com)

GitHub: [@Dev2Creator](https://github.com/Dev2Creator)

## Copyright and license

Copyright © 2026 Anika Mukherjee.

The source code is licensed under the [GNU Affero General Public License v3 or later](LICENSE).

---

<div align="center">

Built for people who want their footing back before they choose their next words.

</div>
