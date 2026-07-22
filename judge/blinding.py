"""Canonical blinded rendering of an answer, shared by EVERY cell that must see identical text.

Used by the physician workbooks (cells A' and D) AND the LLM regrade (judge/grade_expanded.py, cell C), so
human and LLM rubric/pairwise cells see the SAME answer presentation - not raw for the LLM and redacted for
the physician.

OpenEvidence is the only provider that self-identifies (its answers embed openevidence.com citation URLs and
the brand name; frontier models never name their vendor). We remove that brand/domain while keeping the
citation structure so verifiability/source-quality stay rateable.

CAVEAT (disclose in the paper): replacing the real citation domain with a neutral placeholder modifies
ABSOLUTE citation accessibility. Because the SAME rendering is applied to every cell that uses this function,
it does not bias the C-vs-D rater contrast or the format contrasts among cells rendered this way; but any
cell graded on the RAW text (e.g. the original cells B and C, before regrading) sees a different rendering -
regrade those with this function too, or disclose the difference.
"""
import re

_DOMAIN = re.compile(r'(https?://)?(www\.)?openevidence\.com', re.I)
_BRAND = re.compile(r'open\s*evidence', re.I)


def render_blinded_answer(answer_markdown):
    t = str(answer_markdown)
    t = _DOMAIN.sub('https://redacted-source.example', t)   # keep the citation, drop the identifying host
    t = _BRAND.sub('[redacted source]', t)
    return t
