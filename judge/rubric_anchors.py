"""Canonical rubric: the SINGLE source of the five-axis 1-4 definitions and per-score anchors.

Imported by BOTH the physician workbook builder (dataset/physician/build_physician_study.py, shown on the
"Rubric anchors" sheet) AND the LLM cell-C regrade (judge/grade_expanded.py, embedded in the system prompt),
so the physician rubric arm (cell D) and the LLM rubric arm (cell C) use IDENTICAL instructions. Axis
definitions are verbatim from grade.py; the per-score anchors elaborate the 1-4 scale.
"""
AXES = ['accuracy', 'clinical_utility', 'source_quality', 'completeness', 'verifiability']
SCALE = {1: 'unacceptable', 2: 'marginal', 3: 'good', 4: 'excellent'}

AXIS_DEF = {
    'accuracy': "factual and clinical correctness of the claims",
    'clinical_utility': "usefulness for delivering high-quality clinical care",
    'source_quality': "quality/authority of the evidence and reasoning offered",
    'completeness': "comprehensiveness given what the question asks",
    'verifiability': "how easily a clinician could verify the answer's claims",
}
ANCHORS = {
    'accuracy': {1: "Clinically significant factual error or an unsafe recommendation; acting on it could harm a patient.",
                 2: "Broadly on track but with a material inaccuracy, outdated guidance, or an unsupported claim needing correction.",
                 3: "Clinically correct on all major points; any inaccuracies are minor and non-consequential.",
                 4: "Fully correct and precise, including relevant thresholds, nuances and caveats; nothing a specialist would correct."},
    'clinical_utility': {1: "Not usable at the point of care - vague, evasive, or fails to address the actual clinical decision.",
                         2: "Limited use - partly addresses the question but omits actionable specifics (dose, timing, threshold, next step).",
                         3: "Useful and actionable for the presenting question; a clinician could act on it with minor independent judgment.",
                         4: "Directly and efficiently resolves the clinical decision with clear, actionable guidance tailored to the scenario."},
    'source_quality': {1: "No supporting evidence or reasoning, or reasoning that is fallacious or misleading.",
                       2: "Weak or generic justification; assertions largely unsupported or backed only by low-quality reasoning.",
                       3: "Sound clinical reasoning and/or appropriate reference to relevant evidence or guidelines.",
                       4: "Well grounded in high-quality, authoritative evidence (guidelines, primary literature) with rigorous reasoning."},
    'completeness': {1: "Misses the central element of the question, or is so incomplete as to be misleading.",
                     2: "Addresses part of the question but omits important components (e.g. contraindications, alternatives, follow-up).",
                     3: "Covers the main components the question requires; only minor omissions.",
                     4: "Thorough and appropriately scoped - decision, caveats, contraindications and relevant follow-up, without padding."},
    'verifiability': {1: "Claims cannot be checked - no citations, named sources, or checkable specifics.",
                      2: "Hard to verify - few or vague references; a clinician would struggle to confirm key claims.",
                      3: "Most key claims are checkable from the citations, named sources, or specific statements provided.",
                      4: "Every material claim is readily verifiable via clear, specific, authoritative citations or references."},
}


def system_prompt():
    """The LLM cell-C system prompt embedding the EXACT anchors physicians see (for grade_expanded.py)."""
    lines = ["You are an expert U.S. physician evaluating a single AI-generated answer to a real "
             "point-of-care clinical question from a practicing clinician. You are blinded to which "
             "system produced the answer. Score the answer on five axes, each on an integer 1-4 scale "
             "(1 = unacceptable, 2 = marginal, 3 = good, 4 = excellent). Use these axis definitions and "
             "per-score anchors:"]
    for ax in AXES:
        lines.append(f"  {ax} ({AXIS_DEF[ax]}):")
        for k in (1, 2, 3, 4):
            lines.append(f"    {k} ({SCALE[k]}): {ANCHORS[ax][k]}")
    lines.append('Judge only the answer content. Respond with ONLY a JSON object, e.g. '
                 '{"accuracy":3,"clinical_utility":4,"source_quality":2,"completeness":3,"verifiability":2}')
    return "\n".join(lines)


if __name__ == '__main__':
    print(system_prompt())
