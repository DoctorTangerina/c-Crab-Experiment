# Problem families for the continual-review study

Status: **second pass (2026-11-07), double-checked and closed on 2026-11-09: no open
targets.** Every Stage 4 target was relabelled by Claude without looking at the
first-pass labels. Each label rests on three pieces of evidence: the comment thread, the
code hunk the comment is anchored to, and the target's generated test (what the target
actually checks). Not used: the first-pass labels, the test-generation `comment_type`,
test outputs, agent-resolution results and tool evaluations.

Acceptance rule (set by the study owner on 2026-11-09): a target is accepted when a
separate re-check gives it the same family. The re-check read all 234 targets again in
shuffled order, from the comment thread and what the author actually changed between the
reviewed commit and the merge, without target numbers, labels or generated tests. The
study owner decided the 4 targets where it disagreed (see "How stable the labels are").
No human has read every label.

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
  `archive/target_families_not_stage4.csv`. They were not relabelled and are not used.

## Families

The three families keep the split of the first pass, which follows the functional vs.
evolvability distinction from code-review defect taxonomies (Mäntylä & Lassenius,
*What Types of Defects Are Really Discovered in Code Reviews?*, IEEE TSE, 2009), with
evolvability divided into code and text/tests. What is new is how a target gets its
family: an ordered decision procedure, a concern code for every target, and an explicit
second family for borderline targets.

| Family | The reviewer has to notice that … | Targets |
|---|---|---:|
| **A: functional correctness** | the production code does the wrong thing or can fail | 71 |
| **B: design and maintainability** | the code works as intended, but its form could be better | 103 |
| **C: tests and documentation** | a test, or text written for people, is weak or wrong | 60 |

### Decision procedure

Label the concern the comment asks the author to fix, as the target test checks it.
Apply the first rule that matches:

1. **Test concern → C.** How the code is tested: scenarios and test data, assertions,
   parametrization, fixtures and mocks, isolation, placement and naming of tests, a test
   that cannot fail, a missing case. Generic code concerns that only happen to sit in a
   test file (an unused or misplaced import, a helper's name, a re-implemented helper)
   are not test concerns: apply rules 3–4 to them.
2. **Prose concern → C.** Text written for people: docstrings, code comments, docs pages,
   README, changelog, module documentation blocks (Ansible `DOCUMENTATION`, `EXAMPLES`,
   `RETURN`), the wording or content of user-facing messages (exceptions, logs,
   warnings, CLI output), typos and links. Whether and when a message or error is
   emitted is not prose.
3. **Behaviour concern → A.** Production code, including runtime and CI configuration,
   does the wrong thing or can fail, and the comment presents the current behaviour as
   wrong or risky.
4. **Otherwise → B.** The code works as intended; the comment asks for a better form.

Tie-breakers:

- A design change that also alters behaviour: **A** when the reviewer says the current
  behaviour is wrong or risky, **B** when the reason is cleanliness, consistency or
  maintainability.
- Several requests in one comment: label the one the target test checks.
- Type annotations → **B**, unless they break at runtime on a supported version (**A**).
- Logging: whether, at what level, through which logger → **B**; wording → **C**.
- Config, CI and packaging: fixes a failure or restores what runs → **A**; housekeeping → **B**.
- A comment on a test or fixture whose expected value is wrong because the production
  behaviour is wrong → **A**, borderline with C (targets 288, 400).
- `borderline = yes` when a second family stays plausible after these rules;
  `alt_family` names it.
- `?` only when the evidence does not show what was asked. No Stage 4 target needed it.

### Concern codes

| Code | What the comment asks for | Targets | Example (`target_no`) |
|---|---|---:|---|
| `A.logic` | fix a wrong condition, computation, value, control flow or result | 39 | 477 inverted modulo conditional |
| `A.api-use` | fix a wrong call, argument or attribute, or an undefined name | 7 | 112 misspelled keyword argument |
| `A.compat` | stop breaking a supported version, platform or existing caller | 7 | 111 PEP 604 unions on Python 3.8 |
| `A.unintended-change` | revert a behaviour change the PR should not make | 7 | 16 module's return key changed |
| `A.state-resource` | fix mutable defaults, shared state, side effects, files, concurrency | 5 | 333 mutable default argument |
| `A.input-handling` | handle None, empty, missing, unorderable or oversized input | 4 | 230 indexes a row before checking its type |
| `A.error-handling` | raise, catch or propagate errors correctly | 2 | 203 C-API errors swallowed |
| `A.security` | fix a security or privacy problem | 0 | – |
| `B.redundant` | remove unnecessary, dead, unreachable, duplicated or debug code | 34 | 244 redundant `if` |
| `B.interface` | redesign an API, parameter, signature or configuration option | 17 | 166 make an argument keyword-only |
| `B.convention` | follow a project convention or idiom, drop a deprecated but working API | 15 | 94 magic number as sentinel |
| `B.structure` | move, extract, split or encapsulate code | 10 | 375 extract a validation function |
| `B.naming` | rename an identifier | 8 | 326 rename a variable |
| `B.simplify` | express the same logic more simply | 6 | 315 needless lambda wrapper |
| `B.typing` | fix or add type annotations | 5 | 468 missing `bool` annotation |
| `B.reuse` | reuse an existing helper or constant instead of repeating it | 4 | 34 derive choices from `STRATS` |
| `B.performance` | make it faster, nothing else | 4 | 69 OpenCV instead of PIL |
| `C.doc-inline` | fix a docstring or code comment | 16 | 73 docstring documents the wrong parameter |
| `C.test-design` | restructure a test: data, parametrization, placement, mocking, speed | 16 | 212 parametrize over `cache` |
| `C.test-oracle` | make a test check the right thing (assertions, cases, tests that cannot fail) | 12 | 450 test always passes |
| `C.doc-external` | fix docs pages, guides or module documentation blocks | 10 | 10 outdated link |
| `C.message` | reword a user-facing message | 6 | 198 deprecation warning names the wrong version |

## Case-level rule

A case gets a family only if **all** its targets share it. 15 mixed cases are excluded,
leaving **169 eligible cases** in 65 repos:

| Family | Cases | Repos | Targets | Est. disk | To build locally |
|---|---:|---:|---:|---:|---:|
| A | 48 | 32 | 53 | ~220 GB | 0 |
| B | 72 | 40 | 82 | ~245 GB | 2 |
| C | 49 | 28 | 56 | ~133 GB | 0 |
| **Total** | **169** | **65** | **191** | **~598 GB** | **2** |

Sizes: public images use registry size × 3.0; the two images to build use their repo's
median. Counting shared layers once, the eligible pool is 150 GB compressed, about
450 GB on disk. The 3.0 ratio comes from a single image; Phase 0 replaces these with
measured sizes.

The two images to build are `PostHog__posthog-7569@db32271` (built `ok` in the
2026-10-30 run, no longer on disk) and `skypilot-org__skypilot-3017@1f526ee` (failed in
that run). Both cases are now family B; skypilot-3017 was A in the first pass.

## How stable the labels are

- **Re-check (2026-11-09).** Same family for 230 of 234 targets (98%); those 230 were
  accepted. All 4 mismatches were borderline, and each time the re-check chose the
  `alt_family`. The study owner decided them the same day (`reviewed = yes`):

  | Target | Case | Second pass | Re-check | Decision | Why |
  |---|---|---|---|---|---|
  | 300 | sympy-19913 | A | C | **C** (case A → C) | The second-pass rationale was wrong: the printer already mapped `loggamma` correctly and only the test's expected string changed. |
  | 153 | keep-1984 | A | B | **B** (case A → B) | The reviewer asks for narrower exceptions and names no bug or risk, so rule 3 does not apply. |
  | 327 | inference-1168 | A | B | **A** (case stays mixed) | The re-check misread "same as all other places": all 9 call sites used the old condition. |
  | 147 | dvc-2596 | B | A | **B** (case stays mixed) | The reviewer worries about a name collision, but nothing fails. |

  `accepted` is `yes` for 232 targets: the 230 matches, plus 300 and 153, whose label
  moved to the re-check's family. 327 and 147 stay `accepted = no` with `reviewed = yes`.
- **What the re-check is worth.** The evidence was new, the reader was not: it was the
  same model in the same working session, with its earlier labels still in memory. The
  agreement shows this, since even the fine-grained concern code matched on 228 of 234
  targets. The re-check can expose a label that the actual fix contradicts, as with
  target 300, but its 98% must not be reported as inter-rater reliability. The only
  labels made separately are the first pass: 197 of the 232 accepted targets also match
  it, 35 do not.
- **Borderline targets.** 51 of 234 (22%): A/B 33, B/C 11, A/C 7. 39 eligible cases
  contain at least one (A 14, B 17, C 8). If every borderline target took its
  `alt_family`, 130 eligible cases would keep their family, 35 would change family and
  4 would become mixed. 49 of the 51 are accepted.
- **Agreement with the first pass** (comment text only, 2026-11-04): same family for
  199 of 234 targets (85%, Cohen's κ = 0.77). Of the 167 cases eligible in both passes,
  140 keep their family and 27 change; 2 cases became eligible and 2 became mixed.

  | First pass ↓ / second pass → | A | B | C |
  |---|---:|---:|---:|
  | A | 65 | 12 | 8 |
  | B | 6 | 85 | 3 |
  | C | 0 | 6 | 49 |

  The main shifts: redundancy and convention comments the first pass read as bugs
  (A → B, 12); documentation blocks, examples, messages and test artefacts (A → C, 8);
  type annotations, names and code structure (C → B, 6). Some first-pass labels broke
  its own rules: type annotations 389 and 468 were C, the docstring fix 287 was A.
  18 of the 35 disagreements are borderline in the second pass.
- Both passes were made by Claude, so this agreement is a consistency check, not
  inter-rater reliability. If the study reports a reliability figure, a human or another
  separately run coder has to label a sample; nothing here provides one.

## Fit with the experiment proposal

- Mirrors the demo structure: adaptation block 1 = A, block 2 = B, block 3 = C; reserved
  evaluation cases from all three families; a separate warmup set.
- With `source_split_policy = project`, a repo can hold only one role. A balanced
  repo-disjoint split of the eligible pool exists (feasibility check, not an assignment):
  warmup 11 cases (A 4, B 4, C 3) / 11 repos; adapt 79 (A 22, B 34, C 23) / 27 repos;
  eval 79 (A 22, B 34, C 23) / 27 repos. pandas (14 cases), ansible (13) and sympy (11)
  each fall wholly into one role.
- B is now the largest family. The §8.2 sizing hypothesis (30 adaptation and 30 reserved
  cases, 10 per family) fits within these counts.
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

- `target_families.csv`: one row per Stage 4 target (234) with `family`, `concern`,
  `borderline`, `alt_family`, a one-line `rationale`, the re-check result
  (`recheck_family`, `recheck_concern`, `recheck_note`), `accepted` (`yes` when `family`
  equals `recheck_family`), `reviewed`, `note` and the comment text. To correct a label,
  change `family` and `concern` together (the code's prefix must equal the family), keep
  `borderline`, `alt_family` and `accepted` consistent, set `reviewed = yes` and add a
  `note`. `target_no` keeps the Stage 3 numbering, so it has gaps.
- `archive/first_pass_disagreements.csv`: the 35 targets whose family differs between the
  two passes, with both labels and the second-pass rationale. The full first pass is in
  git history (commit `6a1c77f`).
- `archive/target_families_not_stage4.csv`: the 249 Stage 3 targets outside Stage 4,
  with first-pass labels. Not relabelled, not used.
- `case_families.csv`: generated; do not edit by hand. `concerns` lists the concern codes
  of the case's targets; `open_targets` counts targets neither accepted nor marked
  `reviewed = yes`.
- `build_case_families.py`: regenerates `case_families.csv`; stops if
  `target_families.csv` does not list exactly the Stage 4 comments or has an inconsistent
  `concern`, `borderline`, `alt_family` or `accepted`; prints how many eligible cases
  depend on a borderline target and which targets are still open.
- `build_stage4_testgen.py`: writes `../results_testgen_stage4/` (184 cases, 234 tests,
  `_manifest.json` with source hashes). Refuses to overwrite an existing folder, because
  prepared runs pin each file's hash.
- `pull_stage4_images.py`: pulls the 182 public images from GHCR and retags them as
  `reviewbench/<slug>:latest`, the name the c-CRAB code expects.
- `ghcr_sizes.json`: registry sizes and layers of the 182 public images (fetched 2026-11-04).
