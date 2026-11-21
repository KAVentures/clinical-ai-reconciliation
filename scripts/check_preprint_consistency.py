#!/usr/bin/env python3
"""Audit primary estimates against the immutable archived analysis summary."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
results = json.loads((ROOT / "judge/out/robust_analysis.json").read_text())["primary_instrument"]
labels = {"accuracy": "Accuracy", "clinical_utility": "Clinical utility",
          "source_quality": "Source quality", "completeness": "Completeness",
          "verifiability": "Verifiability"}

def format_number(value):
    return f"{value:.1f}".replace("-", "−")

def format_ci(values):
    return "[" + format_number(values[0]) + ", " + format_number(values[1]) + "]"

for path in ("MANUSCRIPT.md", "README.md"):
    document = (ROOT / path).read_text()
    for key, label in labels.items():
        r = results[key]
        row = (f"| {label} | {format_number(r['instrument_mean'])} | "
               f"{format_ci(r['instrument_ci_fixed'])} | "
               f"{format_ci(r['instrument_simultaneous_ci'])} | "
               f"{r['instrument_p_holm']:.4f} | ✓ |")
        assert document.count(row) == 1, f"{path}: mismatched primary result: {label}"
    assert any(marker in document.lower() for marker in ("not registered", "prospective study registry", "prospectively registered")), path

assert "not prospectively registered" in (ROOT / "reconciliation_protocol.md").read_text()
assert "not executed or registered prospectively" in (ROOT / "HUMAN_STUDY_PROTOCOL.md").read_text()
manuscript = (ROOT / "MANUSCRIPT.md").read_text()
assert "## Abstract" in manuscript and "## References" in manuscript
print("PASS: primary estimates, proposal provenance and manuscript sections verified")
