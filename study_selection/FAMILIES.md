# Problem families for the continual-review study

Status: **first-pass proposal, not yet validated by a human.** Labels were assigned by
Claude from the comment text only (no results, no test outcomes). The proposal requires
families to be fixed before any results exist (§8.2), so confirm or correct them first.

## Population: Stage 4

Decision (2026-11-04): the study uses c-CRAB **Stage 4**, the benchmark's final set
(Table 3 of the paper): **184 cases, 234 targets**.

Why Stage 4 and not Stage 3:

- When the benchmark was built, the repair agent (Claude Code with Sonnet-4.6) made each
  Stage 4 target pass when given the human comment (paper §4.2.4). A failed target then
  points at the review, not at the agent. In Stage 3, 155 of the 339 cases had no comment
  the agent could resolve, so they score zero under every condition.
- Adaptation feedback (the repair outcome sent to the package extractor) no longer
  includes targets that no review could make pass.
- 182 of the 184 Docker images are public on GHCR. No other Stage 3 case has one.
- The study population matches the set the paper reports on.

What this commits the study to:

- `repair_model` is fixed to `claude-sonnet-4-6`. With another repair agent the
  guarantee above does not hold.
- Conclusions cover issues this repair agent can fix. State it as a threat to validity.
- The agent resolved each target at least once while the benchmark was built, possibly
  after several attempts. It is not deterministic, so a correct review can still fail a target.
- Stage 4 does not replace the repair-without-comments control in `PROTOCOL.md`.

Unit labelled: the **234 Stage 4 targets**. Each is one Stage 4
`reference_review_comment` with its successful generated test, matched by comment text.

- Not targets: 224 other successful tests in `testgen_combined.zip` for the same cases.
  59 belong to Stage 3 comments the agent did not resolve. 165 belong to comments the
  Stage 1 filter removed. `results_testgen_stage4/` leaves all of them out.
- `comment_type` from test generation (functional / style / documentation / structural)
  was not reused: it is model-assigned, mostly "functional", and mixes code and text concerns.
- The 249 Stage 3 targets outside Stage 4 keep their first-pass labels in
  `archive/target_families_not_stage4.csv`. They are not used.

## Definitions

The split follows the functional vs. evolvability distinction from code-review defect
taxonomies (Mäntylä & Lassenius, *What Types of Defects Are Really Discovered in Code
Reviews?*, IEEE TSE, 2009), with evolvability divided into code structure and text/tests.

| Family | What the comment asks for | Examples (`target_no`) |
|---|---|---|
| **A: functional correctness** | The code behaves wrongly or can fail: wrong logic or condition, missing None/empty/edge-case handling, wrong argument, value or API call, undefined name, error handling that changes behaviour, numeric precision, compatibility breakage | 14 `is not None`; 333 mutable default argument; 477 inverted conditional |
| **B: design and maintainability** | Same behaviour, better code: duplication and refactoring, redundant or dead code, leftover debug code, API/parameter/interface design, typing annotations, identifier names, project conventions, performance-only changes | 244 redundant `if`; 375 move validation into a function; 469 unused variable; 85 consistent signatures |
| **C: tests and documentation** | Text and test artefacts: test quality (parametrize, stronger assertions, a test that cannot fail, test placement), docstrings, docs, changelog, typos in prose, user-facing messages | 212 parametrize; 450 test always passes; 71 wrong docstring; 196 error message should keep the original message |

### Boundary rules

1. Only test code changes → **C**, even when the test concerns a functional bug.
   A behaviour change in library code → **A**.
2. Typing annotations → **B**; wrong runtime type handling → **A**.
3. Identifier names → **B**; prose (docs, messages, changelog, typos in text) → **C**.
4. Adding a raise/catch/check that changes behaviour → **A**; wording of the message → **C**.
5. Performance-only suggestions → **B**.

17 targets sit on a boundary (`borderline = yes`). No Stage 4 target is unlabelled (`?`).

## Case-level rule

A case gets a family only if **all** its targets share it. 15 mixed cases are excluded,
leaving **169 eligible cases** in 65 repos:

| Family | Cases | Repos | Targets | Est. disk | To build locally |
|---|---:|---:|---:|---:|---:|
| A | 61 | 36 | 66 | ~250 GB | 1 |
| B | 64 | 39 | 73 | ~238 GB | 1 |
| C | 44 | 27 | 51 | ~123 GB | 0 |
| **Total** | **169** | **65** | **190** | **~610 GB** | **2** |

Sizes: public images use registry size × 3.0; the two images to build use their repo's
median. Counting shared layers once, the eligible pool is 154 GB compressed, about
460 GB on disk. The 3.0 ratio comes from a single image; Phase 0 replaces these with
measured sizes.

The two images to build are `PostHog__posthog-7569@db32271` (built `ok` in the
2026-10-30 run, no longer on disk) and `skypilot-org__skypilot-3017@1f526ee` (failed in
that run).

## Fit with the experiment proposal

- Mirrors the demo structure: adaptation block 1 = A, block 2 = B, block 3 = C; reserved
  evaluation cases from all three families; a separate warmup set.
- With `source_split_policy = project`, a repo can hold only one role. A balanced
  repo-disjoint split of the eligible pool exists (feasibility check, not an assignment):
  warmup 11 cases (A 5, B 4, C 2) / 6 repos; adapt 79 (A 28, B 30, C 21) / 30 repos;
  eval 79 (A 28, B 30, C 21) / 29 repos. pandas (14 cases), ansible (13) and sympy (11)
  each fall wholly into one role.
- Pilot cases must stay out of the final evaluation (§8.1); draw them from the same
  families but from cases (ideally repos) not used in the main study. With this smaller
  pool, each pilot repo is taken from the split above.

## Configuration in `continual_review`

```json
"stage3_file": "results_pipeline_funnel/stage4_agent_resolved.jsonl",
"testgen_dir": "results_testgen_stage4",
"repair_model": "claude-sonnet-4-6"
```

The key keeps its old name `stage3_file`; renaming it would change the experiment code.
Pointing it at the Stage 4 file is not enough on its own: the catalog counts every
successful test in each `result.json` as a target, so `testgen_dir` must be the Stage 4
folder. With both set, the catalog reports 184 cases and 234 targets.

## Files

- `target_families.csv`: one row per Stage 4 target (234). Edit `family`, set
  `reviewed = yes`, add a `note`. `target_no` keeps the Stage 3 numbering, so it has gaps.
- `archive/target_families_not_stage4.csv`: the 249 Stage 3 targets outside Stage 4,
  with first-pass labels. Not used.
- `case_families.csv`: generated; do not edit by hand.
- `build_case_families.py`: regenerates `case_families.csv`; stops if
  `target_families.csv` does not list exactly the Stage 4 comments.
- `build_stage4_testgen.py`: writes `../results_testgen_stage4/` (184 cases, 234 tests,
  `_manifest.json` with source hashes). Refuses to overwrite an existing folder, because
  prepared runs pin each file's hash.
- `pull_stage4_images.py`: pulls the 182 public images from GHCR and retags them as
  `reviewbench/<slug>:latest`, the name the c-CRAB code expects.
- `ghcr_sizes.json`: registry sizes and layers of the 182 public images (fetched 2026-11-04).
