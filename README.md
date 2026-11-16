# Same Strike, Different Story

**Language models attribute conflict events differently depending on the asker's language.**
A cross-lingual audit of attribution, death tolls and civilian shares for 22 conflict events, asked in the languages of both parties, across 8 models, with a non-political negative control and a tested mitigation.

📄 Paper: [`paper/Same_Strike_Different_Story.pdf`](paper/Same_Strike_Different_Story.pdf)

*Apart Research — AI x Epistemics Research Sprint, 13–15 November 2026 · Track 1 (Model Epistemics & Evals), Track 4 (Open)*

## Key results (6,335 responses, baseline condition unless noted)

| Question asked in | Names the reported attacker | Says "disputed / unclear" |
|---|---|---|
| Attacker's language | **64.7%** | 16.9% |
| Victim's language | **74.1%** | 10.1% |
| English | 75.9% | 13.2% |

- **Attribution shifts with the asker's language.** Gap of **9.4 points** (95% CI 5.7–13.6, event-clustered bootstrap); same direction in **8/8 models** and **5/5 conflicts**; cell-level exact McNemar p = 0.0005.
- **It is the role, not the language.** With event, language and model fixed effects, asking in the attacker's language lowers the naming rate by 9.7 points (CI 5.8–13.7); leave-one-conflict-out gaps are 7.3–11.4. The gap is 5.8 points in the three well-resourced conflicts alone.
- **Death tolls diverge more than for non-political disasters** (19% vs 8% of language pairs differ by ≥25%, Fisher p = 0.001) **but show no directional bias**: the lower-toll-in-attacker's-language pattern reported for GPT-3.5 does not replicate (Wilcoxon p = 0.11).
- **A language-invariance system instruction cuts the attribution gap by ~40%** (to 5.5 points, CI 0.9–10.5); it helps GPT-5.6-Luna, DeepSeek-V3 and Claude Haiku 5.5, and does nothing or worse for the others.
- English answers match victim's-language answers, so **English-only evaluation cannot see this effect.**

![Attribution by model and conflict](figures/fig3_attribution.png)

## Why this matters

Jonathan Stray (CHAI) argues that conflict and bad information feed each other, and that parties who receive *different facts* can escalate over an incompatibility that exists only in their perceptions ("epistemic fragmentation"). If a model reports a lower death toll to people asking in the attacker's language and a higher one to those asking in the victim's language, it hands each side its own version of the event. Steinert & Kazenwadel (2025, Journal of Peace Research) found this pattern for GPT-3.5 on two conflicts. This project measures it for current models, on five conflicts, adds attribution and civilian share, separates it from ordinary translation noise with a negative control, and tests a mitigation.

## Design

| | |
|---|---|
| Events | 22 incidents, 5 conflicts: Israel–Gaza (he/ar), Russia–Ukraine (ru/uk), Turkey–Kurdish (tr/ku), Armenia–Azerbaijan (hy/az), India–Pakistan (hi/ur); both sides appear as attacker in every conflict |
| Controls | 6 non-political disasters asked in all 11 languages (translation-noise floor) |
| Questions | death toll · civilian % · responsibility (A / B / disputed / other) in a fixed, parseable format |
| Models | GPT-4o-mini, GPT-5.6-Luna, Claude Haiku 5.5, DeepSeek-V3, Qwen 3.7-Flash, GLM-5.3-Flash, Mistral-Small-24B, Llama-3.1-8B |
| Conditions | baseline · language-invariance system instruction |
| Size | 8 models × 2 conditions × 132 cells × 3 samples = 6,336 queries (6,335 returned) |
| Translation QA | translated (Claude Haiku 5.5) → back-translated (GPT-4o-mini) → audited for equivalence and loaded wording; all audits in `results/translation_audit.jsonl` |

Measures: share of answers naming the reported attacker by question language (primary); **Fragmentation Index** FI = log₁₀(toll in attacker's language / toll in victim's language), where FI < 0 means a lower toll is reported to the attacker's side; undirected divergence compared against the non-political controls.

## Reproduce

```bash
pip install -r requirements.txt
cp .env.example .env            # add OPENROUTER_API_KEY
python scripts/translate.py     # 1. translate + back-translate + audit -> data/prompts.jsonl (already committed)
python scripts/run.py           # 2. 6,336 queries; resumable, appends to results/runs.jsonl
python scripts/analyze.py       # 3. results/summary.json, results/tables/*.csv
python scripts/figures.py       # 4. figures/*.png
python -m pytest -q tests       # parser tests (native digits, separators, ranges)
```

Every response is appended to `results/runs.jsonl` the moment it returns; rerunning skips finished cells and retries failures. The full run cost US$0.61 in API fees (`results/summary.json`, `total_cost_usd`).

## Layout

```
data/        events.jsonl, controls.jsonl, conflicts.json, prompts.jsonl (frozen translated prompts)
src/sstd/    client.py (OpenRouter), items.py (templates, conditions), parse.py, jobs.py (resumable runner)
scripts/     translate.py, run.py, analyze.py, figures.py
results/     runs.jsonl (every raw response), translation_audit.jsonl, summary.json, tables/
figures/     fig3_attribution.png (headline), fig1_event_fi.png, fig2_model_divergence.png
paper/       report.md -> compile.py -> Same_Strike_Different_Story.docx/.pdf (Apart template)
tests/       parser tests
```

## Scope and limitations

This measures **consistency across languages**, not accuracy: it does not claim which language's figure is correct, only that speakers of different languages receive different numbers. Event descriptors were written to be neutral, but place names themselves can carry connotations. Kurmanji Kurdish and Armenian are lower-resource languages for most models, which is why the negative control is reported on the same language pairs. See the paper's appendix for dual-use considerations.

## Prior work and disclosure

All code, data and results were produced during the sprint weekend. The OpenRouter client pattern is adapted from the author's concurrent sprint project, *The Accuracy-Approval Dilemma*. Prior work this extends: Steinert & Kazenwadel (2025), "How user language affects conflict fatality estimates in ChatGPT", *Journal of Peace Research* 62(4) (doi:10.1177/00223433241279381); Qi, Fernández & Bisazza, "Cross-Lingual Consistency of Factual Knowledge in Multilingual Language Models", EMNLP 2023.

## License

MIT
