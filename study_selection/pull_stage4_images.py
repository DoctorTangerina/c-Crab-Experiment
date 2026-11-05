"""Pull the published Docker images for the Stage 4 cases from GHCR.

Each image is pulled as ghcr.io/c-crab-benchmark/<slug>:latest and retagged as
reviewbench/<slug>:latest, the name execution.container_runtime.get_docker_image_name
expects (and therefore what run_tool_eval and continual_review's bridge use).
Images already present under the reviewbench name are skipped, so the script can be
stopped and rerun. Two Stage 4 cases have no published image and must be built.

    python -I study_selection/pull_stage4_images.py --dry-run
    python -I study_selection/pull_stage4_images.py
    python -I study_selection/pull_stage4_images.py --ids manifests/eval_ids.txt
    python -I study_selection/pull_stage4_images.py --limit 20

Standard library only. Needs a running Docker daemon.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STAGE4 = ROOT / "results_pipeline_funnel" / "stage4_agent_resolved.jsonl"
SIZES = HERE / "ghcr_sizes.json"
REGISTRY = "ghcr.io/c-crab-benchmark"


def docker(*args: str, quiet: bool = False) -> int:
    out = subprocess.DEVNULL if quiet else None
    return subprocess.run(["docker", *args], stdout=out, stderr=out, check=False).returncode


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ids", type=Path, help="file with one instance_id per line (subset of Stage 4)")
    p.add_argument("--limit", type=int, help="pull at most N images in this run")
    p.add_argument("--min-free-gb", type=float, default=60.0,
                   help="stop before a pull when free space on the Docker host drive drops below this (default 60)")
    p.add_argument("--dry-run", action="store_true", help="list what would be pulled, without pulling")
    args = p.parse_args()

    if docker("info", quiet=True) != 0:
        sys.exit("Docker daemon is not reachable; start Docker Desktop first.")

    ids = [json.loads(line)["instance_id"] for line in STAGE4.open(encoding="utf-8") if line.strip()]
    if args.ids:
        wanted = {line.strip() for line in args.ids.open(encoding="utf-8-sig") if line.strip()}
        unknown = wanted - set(ids)
        if unknown:
            sys.exit(f"Not Stage 4 instance IDs: {sorted(unknown)}")
        ids = [i for i in ids if i in wanted]

    sizes = {s["slug"]: s for s in json.loads(SIZES.read_text(encoding="utf-8"))}
    todo, present, unpublished = [], [], []
    for iid in ids:
        slug = iid.split("@")[0].lower()
        if docker("image", "inspect", f"reviewbench/{slug}", quiet=True) == 0:
            present.append(iid)
        elif slug not in sizes or "error" in sizes[slug]:
            unpublished.append(iid)
        else:
            todo.append((iid, slug))
    if args.limit is not None:
        todo = todo[:args.limit]

    gb = sum(sizes[s]["compressed"] for _, s in todo) / 1e9
    print(f"Stage 4 selection: {len(ids)} | already local: {len(present)} | "
          f"to pull: {len(todo)} (~{gb:.0f} GB compressed before layer sharing) | "
          f"not published, must be built: {len(unpublished)}")
    for iid in unpublished:
        print(f"  build locally: {iid}")
    if args.dry_run:
        for iid, slug in todo:
            print(f"  would pull {REGISTRY}/{slug}:latest -> reviewbench/{slug}:latest")
        return 0

    drive = Path(ROOT.anchor or "/")
    failed = []
    for n, (iid, slug) in enumerate(todo, 1):
        free = shutil.disk_usage(drive).free / 1e9
        if free < args.min_free_gb:
            print(f"Stopping: {free:.0f} GB free on {drive} (< {args.min_free_gb:.0f} GB). Rerun later to resume.")
            break
        remote, local = f"{REGISTRY}/{slug}:latest", f"reviewbench/{slug}:latest"
        print(f"[{n}/{len(todo)}] {iid}  ({free:.0f} GB free)", flush=True)
        if docker("pull", remote) != 0 or docker("tag", remote, local) != 0:
            failed.append(iid)
            continue
        docker("rmi", remote, quiet=True)  # drops only the ghcr name; layers stay under reviewbench/
    if failed:
        print(f"Failed ({len(failed)}): rerun to retry")
        for iid in failed:
            print(f"  {iid}")
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
