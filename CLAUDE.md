# CLAUDE.md

## Source of Truth
- Project information lives only in the `docs/` files. This file holds instructions only.
- Read the relevant doc before answering questions or making changes:

| Question | File |
|---|---|
| What are we building, for whom | `docs/PRODUCT.md` |
| Build order, version steps, done criteria | `docs/ROADMAP.md` |
| How it is built, technical rules | `docs/ARCHITECTURE.md` |
| Irrigation science, equations, defaults, terms | `docs/DOMAIN.md` |
| Competitors, customers, interviews | `docs/MARKET.md` |
| Decisions, problems, history | `docs/JOURNEY.md` |
| Calculation test cases | `reference-cases/` |

- Don't assume features, scope, or tech stack beyond what these files record.
- Follow every decision in `docs/JOURNEY.md`. Flag any change that would break one before making it.
- Items marked "مقترح" are proposals, not decisions. Don't treat them as decided.

## Engineering Rules
- Never write an irrigation equation or default value in code from memory. It must exist in `docs/DOMAIN.md` with its source first. If it is missing, say so and ask the team to research it.
- Calculation tests read from `reference-cases/`. Never edit expected values to make a test pass.

## Mandatory Logging
After every decision or anything built, update the docs in the same turn:

| Event | Where to record |
|---|---|
| New decision | `docs/JOURNEY.md` decision log: date, decision, why, rejected alternatives |
| Something built | `docs/JOURNEY.md`: what it does, how it works, why this way |
| Expected or encountered problem | Problems table in `docs/JOURNEY.md` with status |
| Problem solved | Update the row: status ✅, the solution, and the date |
| Change to product, roadmap, architecture, or domain | Update that file, then log the decision |
| Interview or market research | `docs/MARKET.md` |
| Any of the above | One row in the journey log with the date |

- Only record what was actually decided or built. Mark proposals as "مقترح".
- If unsure whether something was decided, ask before recording it.
- Use the current date for every entry.
- Update existing sections instead of duplicating information. Link instead of copying.

## Git Push (Mandatory)
- Every change to any file in the repo is committed and pushed to `origin main` in the same turn, right after the docs update and `python tools/build_docs.py`.
- Never end a turn with uncommitted or unpushed changes.
- Commit message: short, says what changed. Never force-push.
- If the push fails, say so in the reply. Don't claim it is on GitHub.

## HTML Pages
- Every doc has a mobile-first HTML page generated into `site/`.
- After editing any `.md` file, run `python tools/build_docs.py`.
- Never edit files in `site/` by hand.

## Writing Arabic With English (RTL/LTR)
Applies to all docs and to replies in Arabic.

- Wrap Markdown files in `<div dir="rtl">` ... `</div>` with blank lines inside.
- Start every line, bullet, heading, and table cell with an Arabic word.
- Never end a line with an English word followed by punctuation.
- Put English terms, code, and file names in backticks, in the middle of the sentence.
- Avoid parentheses around English terms; use backticks.
- Put commands, formulas, and code flows in separate code blocks.
- Prefix dates in Arabic lines with an RLM mark (`‏`) so they stay in place.
- Numbers always use English digits `0-9` and `%`, never Arabic-Indic digits, in docs, pages, images, and replies.
- Keep technical terms in English when the English term is clearer.

## Communication
- Be direct, concise, structured for scanning. Core answer first.
- Reply in Egyptian Arabic unless asked otherwise.
- Challenge weak assumptions; recommend one best default with a short reason.
