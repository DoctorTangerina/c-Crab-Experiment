"""Derive case-level families and image-size estimates for the Stage 4 study pool.

Population: the 184 Stage 4 cases and their 234 targets (the Stage 4
`reference_review_comments`, each with one successful generated test).
Edit `family` (A, B, C or ?) and `concern` in target_families.csv (codes in
FAMILIES.md; the code's prefix must equal the family), keep `borderline = yes`
exactly when `alt_family` names a second plausible family, keep `accepted = yes`
exactly when `family` equals `recheck_family`, then rerun:

    .venv/Scripts/python.exe -I study_selection/build_case_families.py

Checks that target_families.csv covers exactly the Stage 4 comments, writes
study_selection/case_families.csv and prints a summary, including how many eligible
cases depend on a borderline target and which targets are still open (not accepted by
the re-check and not marked `reviewed = yes`). Read-only with respect to every other
file in the checkout. Standard library only.
"""
from __future__ import annotations

import collections
import csv
import json
import statistics
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STAGE4 = ROOT / "results_pipeline_funnel" / "stage4_agent_resolved.jsonl"
TESTGEN_ZIP = ROOT / "raw_results_compressed" / "testgen_combined.zip"
SIZES = HERE / "ghcr_sizes.json"
TARGETS = HERE / "target_families.csv"
OUT = HERE / "case_families.csv"

FAMILIES = ("A", "B", "C")
# Concern codes of the codebook in FAMILIES.md; the prefix is the family.
CONCERNS = (
    "A.logic", "A.input-handling", "A.api-use", "A.error-handling", "A.compat",
    "A.state-resource", "A.unintended-change", "A.security",
    "B.redundant", "B.reuse", "B.simplify", "B.structure", "B.interface", "B.naming",
    "B.typing", "B.convention", "B.performance",
    "C.test-design", "C.test-oracle", "C.doc-inline", "C.doc-external", "C.message",
)
# On-disk / compressed ratio, measured on one image (zulip__zulip-25349:
# 1.17 GB compressed -> 3.51 GB on disk). Replace after Phase 0 measures real sizes.
DISK_RATIO = 3.0


def main() -> None:
    stage4 = [json.loads(line) for line in STAGE4.open(encoding="utf-8") if line.strip()]
    refs = {c["instance_id"]: {r["text"].strip() for r in c["reference_review_comments"]} for c in stage4}
    with TARGETS.open(encoding="utf-8", newline="") as stream:
        targets = list(csv.DictReader(stream))
    bad = {t["family"] for t in targets} - set(FAMILIES) - {"?"}
    if bad:
        raise SystemExit(f"Unknown family labels in {TARGETS.name}: {sorted(bad)}")
    for t in targets:
        fam, concern, alt = t["family"], t["concern"], t["alt_family"]
        problems = []
        if fam in FAMILIES and (concern not in CONCERNS or not concern.startswith(fam + ".")):
            problems.append(f"concern {concern!r} is not a code of family {fam} "
                            f"({', '.join(c for c in CONCERNS if c.startswith(fam + '.'))})")
        if alt and (alt not in FAMILIES or alt == fam):
            problems.append(f"alt_family {alt!r} must be another of {FAMILIES}")
        if (t["borderline"] == "yes") != bool(alt) or t["borderline"] not in ("", "yes"):
            problems.append("borderline must be 'yes' exactly when alt_family is set")
        if t["accepted"] != ("yes" if fam == t["recheck_family"] else "no"):
            problems.append(f"accepted must be {'yes' if fam == t['recheck_family'] else 'no'}: "
                            f"family is {fam!r}, recheck_family is {t['recheck_family']!r}")
        if problems:
            raise SystemExit(f"{TARGETS.name} target {t['target_no']}: " + "; ".join(problems))

    # target_families.csv must list each Stage 4 comment exactly once, and nothing else.
    seen = collections.Counter((t["instance_id"], t["comment_text"].strip()) for t in targets)
    expected = {(iid, text) for iid, texts in refs.items() for text in texts}
    extra, missing = set(seen) - expected, expected - set(seen)
    dupes = [k for k, n in seen.items() if n > 1]
    if extra or missing or dupes:
        raise SystemExit(f"{TARGETS.name} does not match Stage 4: {len(extra)} extra, "
                         f"{len(missing)} missing, {len(dupes)} duplicated targets")

    by_case: dict[str, list[dict]] = collections.defaultdict(list)
    for t in targets:
        by_case[t["instance_id"]].append(t)

    # Successful generated tests that are not Stage 4 targets. They are dropped from
    # results_testgen_stage4/ (build_stage4_testgen.py) so they never enter a denominator.
    excluded: dict[str, int] = {}
    with zipfile.ZipFile(TESTGEN_ZIP) as archive:
        for case in stage4:
            iid = case["instance_id"]
            result = json.loads(archive.read(f"testgen_combined/{iid}/result.json"))
            excluded[iid] = sum(1 for e in result["results"]
                                if e.get("success") is True and e["comment_text"].strip() not in refs[iid])

    sizes = {s["slug"]: s for s in json.loads(SIZES.read_text()) if "error" not in s}
    public = {slug: s["compressed"] * DISK_RATIO / 1e9 for slug, s in sizes.items()}
    repo_sizes: dict[str, list[float]] = collections.defaultdict(list)
    for slug, gb in public.items():
        repo_sizes[slug.rsplit("-", 1)[0]].append(gb)
    global_median = statistics.median(public.values())

    rows = []
    for case in stage4:
        iid = case["instance_id"]
        ts = by_case[iid]
        counts = collections.Counter(t["family"] for t in ts)
        fams = {f for f in counts if f in FAMILIES}
        if counts.get("?"):
            family = "UNCLEAR"
        elif len(fams) == 1:
            family = fams.pop()
        else:
            family = "MIXED"
        slug = iid.split("@")[0].lower()
        if slug in public:
            gb, source, basis = public[slug], "pull", "registry"
        elif repo_sizes.get(slug.rsplit("-", 1)[0]):
            gb, source, basis = statistics.median(repo_sizes[slug.rsplit("-", 1)[0]]), "build", "repo-median"
        else:
            gb, source, basis = global_median, "build", "global-median"
        rows.append({
            "instance_id": iid, "repo": case["repo"], "family": family,
            "eligible": "yes" if family in FAMILIES else "no",
            "targets_A": counts.get("A", 0), "targets_B": counts.get("B", 0),
            "targets_C": counts.get("C", 0), "targets_unclear": counts.get("?", 0),
            "borderline_targets": sum(t["borderline"] == "yes" for t in ts),
            "concerns": ";".join(sorted({t["concern"] for t in ts if t["concern"]})),
            "open_targets": sum(t["accepted"] != "yes" and t["reviewed"] != "yes" for t in ts),
            "excluded_success_tests": excluded[iid],
            "image_source": source, "est_disk_gb": f"{gb:.1f}", "size_basis": basis,
        })

    with OUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def unique_layers_gb(selected: list[dict]) -> float:
        layers = {}
        for r in selected:
            slug = r["instance_id"].split("@")[0].lower()
            if slug in sizes:
                layers.update(dict(map(tuple, sizes[slug]["layers"])))
        return sum(layers.values()) / 1e9

    eligible = [r for r in rows if r["eligible"] == "yes"]
    print(f"Stage 4 cases: {len(rows)}  targets: {len(targets)}  eligible (single family): {len(eligible)}  "
          f"excluded: {dict(collections.Counter(r['family'] for r in rows if r['eligible'] == 'no'))}")
    for fam in FAMILIES:
        sel = [r for r in eligible if r["family"] == fam]
        print(f"  family {fam}: {len(sel):3d} cases, {len({r['repo'] for r in sel}):2d} repos, "
              f"{sum(int(r['targets_' + fam]) for r in sel):3d} targets, "
              f"~{sum(float(r['est_disk_gb']) for r in sel):.0f} GB, "
              f"{sum(r['image_source'] == 'build' for r in sel)} to build")
    total = sum(float(r["est_disk_gb"]) for r in eligible)
    shared = unique_layers_gb(eligible)
    print(f"eligible: ~{total:.0f} GB on disk counting each image separately; "
          f"{shared:.0f} GB compressed after shared layers (~{shared * DISK_RATIO:.0f} GB on disk); "
          f"ratio {DISK_RATIO} from one image")
    # Sensitivity: flip every borderline target of an eligible case to its alt_family.
    flipped = collections.Counter()
    for r in eligible:
        alt_fams = {t["alt_family"] or t["family"] for t in by_case[r["instance_id"]]}
        flipped["kept" if alt_fams == {r["family"]} else
                "changed" if len(alt_fams) == 1 else "mixed"] += 1
    shaky = [r for r in eligible if int(r["borderline_targets"])]
    print(f"borderline targets: {sum(t['borderline'] == 'yes' for t in targets)}; eligible cases with one: "
          f"{len(shaky)} {dict(sorted(collections.Counter(r['family'] for r in shaky).items()))}; "
          f"flipping them all to alt_family: {flipped['kept']} kept, {flipped['changed']} change family, "
          f"{flipped['mixed']} become mixed")
    still_open = [r for r in eligible if int(r["open_targets"])]
    print(f"accepted targets: {sum(t['accepted'] == 'yes' for t in targets)} of {len(targets)}; "
          f"open: {[t['target_no'] for t in targets if t['accepted'] != 'yes' and t['reviewed'] != 'yes']}; "
          f"eligible cases with an open target: {[r['instance_id'] for r in still_open]}")
    print(f"successful tests excluded from the targets: {sum(excluded.values())}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
