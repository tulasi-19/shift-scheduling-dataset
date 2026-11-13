#!/usr/bin/env python3
"""
reproducibility_check.py - regenerate the dataset twice with the same seed and compare
row counts + SHA-256 checksums against the delivered dataset (Step 10).

Usage: python reproducibility_check.py --dataset dataset
"""
import argparse, json, os, subprocess, sys, tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset")
    A = ap.parse_args()
    ref = json.load(open(os.path.join(A.dataset, "source_manifest.json")))
    p = ref["parameters"]
    here = os.path.dirname(os.path.abspath(__file__))
    runs = {}
    with tempfile.TemporaryDirectory() as tmp:
        for n in (1, 2):
            out = os.path.join(tmp, f"run{n}")
            cmd = [sys.executable, os.path.join(here, "generate_data.py"), "--employees", str(p["employees"]), "--teams", str(p["teams"]),
                   "--days", str(p["days"]), "--leaves", str(p["leaves"]), "--seed", str(ref["seed"]), "--start", p["start"],
                   "--absence-rate", str(p["absence_rate"]), "--formats", ",".join(p["formats"]), "--out", out]
            if p.get("swaps") is not None:
                cmd += ["--swaps", str(p["swaps"])]
            if p.get("inject_scale") is not None:
                cmd += ["--inject-scale", str(p["inject_scale"])]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
            runs[n] = json.load(open(os.path.join(out, "source_manifest.json")))
    rows = ["| File | Rows | SHA-256 (first 16) | Regen 1 | Regen 2 |", "|---|---|---|---|---|"]
    ok_all = True
    for rel, meta in sorted(ref["files"].items()):
        m1, m2 = runs[1]["files"][rel], runs[2]["files"][rel]
        same1 = m1["sha256"] == meta["sha256"] and m1["rows"] == meta["rows"]
        same2 = m2["sha256"] == meta["sha256"] and m2["rows"] == meta["rows"]
        ok_all &= same1 and same2
        rows.append(f"| {rel} | {meta['rows'] if meta['rows'] is not None else '-'} | {meta['sha256'][:16]} | "
                    f"{'IDENTICAL' if same1 else 'DIFFERENT'} | {'IDENTICAL' if same2 else 'DIFFERENT'} |")
    head = ["# Reproducibility report", "", f"Seed: `{ref['seed']}`  |  parameters: `{json.dumps(p)}`", "",
            f"Result: **{'PASS - both regenerations are byte-identical to the delivered dataset' if ok_all else 'FAIL'}**", ""]
    text = "\n".join(head + rows) + "\n"
    open(os.path.join(A.dataset, "reproducibility_report.md"), "w").write(text)
    print(text[:400])
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
