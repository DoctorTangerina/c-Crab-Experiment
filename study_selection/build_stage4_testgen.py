"""Write the Stage 4 test-generation folder used as `testgen_dir` by continual_review.

For each Stage 4 case, copies result.json from raw_results_compressed/testgen_combined.zip
and keeps in `results` only the successful tests whose comment is one of the case's
Stage 4 `reference_review_comments` (234 tests in total). Every other entry is dropped:
tests for comments removed by the Stage 1 filter and Stage 3 tests the agent could not
resolve. Without this, continual_review and run_tool_eval would count every successful
test in the file as a target.

    .venv/Scripts/python.exe -I study_selection/build_stage4_testgen.py

Output: results_testgen_stage4/<instance_id>/result.json plus _manifest.json.
Refuses to overwrite an existing output folder: prepared runs pin each file's hash.
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STAGE4 = ROOT / "results_pipeline_funnel" / "stage4_agent_resolved.jsonl"
TESTGEN_ZIP = ROOT / "raw_results_compressed" / "testgen_combined.zip"
OUT = ROOT / "results_testgen_stage4"
RULE = ("kept: success=True and comment_text.strip() equals the text of one Stage 4 "
        "reference_review_comment of the same instance; all other results entries dropped")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} already exists. Runs prepared on it pin its file hashes; "
                         "move it aside deliberately before rebuilding.")
    stage4 = [json.loads(line) for line in STAGE4.open(encoding="utf-8") if line.strip()]
    staged: dict[str, bytes] = {}
    kept_total = dropped_total = 0
    with zipfile.ZipFile(TESTGEN_ZIP) as archive:
        for case in stage4:
            iid = case["instance_id"]
            raw = archive.read(f"testgen_combined/{iid}/result.json")
            result = json.loads(raw)
            refs = [c["text"].strip() for c in case["reference_review_comments"]]
            kept = [e for e in result["results"]
                    if e.get("success") is True and e["comment_text"].strip() in refs]
            if sorted(e["comment_text"].strip() for e in kept) != sorted(refs):
                raise SystemExit(f"{iid}: Stage 4 comments and successful tests do not match one-to-one")
            dropped_total += len(result["results"]) - len(kept)
            kept_total += len(kept)
            result["results"] = kept
            result["derived"] = {"source": f"{TESTGEN_ZIP.relative_to(ROOT).as_posix()}:testgen_combined/{iid}/result.json",
                                 "source_sha256": sha256(raw), "rule": RULE, "kept": len(kept)}
            staged[iid] = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    for iid, data in staged.items():
        path = OUT / iid.replace("/", "__") / "result.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
    manifest = {"stage4_file": STAGE4.relative_to(ROOT).as_posix(),
                "stage4_sha256": sha256(STAGE4.read_bytes()),
                "testgen_zip_sha256": sha256(TESTGEN_ZIP.read_bytes()),
                "rule": RULE, "instances": len(staged), "targets": kept_total,
                "dropped_entries": dropped_total}
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(staged)} cases, {kept_total} targets, dropped {dropped_total} entries -> {OUT}")


if __name__ == "__main__":
    main()
