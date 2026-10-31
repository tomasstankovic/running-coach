#!/usr/bin/env python3
"""Turn a JSON list into ArtifactData batch writes for the plan page's database.

Usage:
  page_docs.py rows.json --collection trends --id date --out-dir docs [--versions versions.json]

rows.json is a list of objects (e.g. `readiness.py --trend 56`, or several
`analyze_session.py --json` rows). Each becomes one document in the collection, keyed by the
--id field, written to <out-dir>/<collection>/<id>.json. Prints the batch writes (<= 50 each)
to pass to ArtifactData `batch`; with --versions (a {"<collection>/<id>": version} map from an
ArtifactData list) existing documents are pinned with if_version.
"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows")
    ap.add_argument("--collection", required=True, help="trends | sessions | weeks")
    ap.add_argument("--id", required=True, help="field used as the document id, e.g. date")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--versions")
    args = ap.parse_args()
    with open(args.rows) as f:
        rows = json.load(f)
    if isinstance(rows, dict):
        rows = [rows]
    versions = {}
    if args.versions:
        with open(args.versions) as f:
            versions = json.load(f)
    os.makedirs(os.path.join(args.out_dir, args.collection), exist_ok=True)
    writes = []
    for row in rows:
        doc_id = str(row[args.id])
        path = os.path.abspath(os.path.join(args.out_dir, args.collection, f"{doc_id}.json"))
        with open(path, "w") as f:
            json.dump(row, f, ensure_ascii=False)
        write = {"op": "set", "collection": args.collection, "doc_id": doc_id, "file_path": path}
        if versions.get(f"{args.collection}/{doc_id}"):
            write["if_version"] = versions[f"{args.collection}/{doc_id}"]
        writes.append(write)
    print(json.dumps([writes[i:i + 50] for i in range(0, len(writes), 50)], indent=1))


if __name__ == "__main__":
    main()
