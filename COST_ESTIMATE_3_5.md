# Cost estimate — extensions #3 (provenance interaction) and #5 (reasoning-effort comparison)

**Not executed.** These need new judge API calls (blocked pending key rotation / spend authorization). Below
is a transparent token-based estimate so you can plug in current per-model prices.

**Basis (measured).** Per-judge thinking tokens on a real grading item (`judge/out/thinking_evidence.json`):
GPT-5.5 3,071 · Grok-4.3 1,880 · Gemini-3.5-flash 922 · Opus-4.8 443 (mean ≈ 1,580). Input per rubric call
≈ question + one ~3.5 k-char answer ≈ 1,000 tokens; per pairwise call ≈ two answers ≈ 1,700 tokens. Output
JSON ≈ 80 tokens. The existing 150-question run was 2,401 rubric + 2,139 pairwise ≈ 4,540 calls.

---

## #3 — Does the format effect interact with query provenance? (OE-originated vs HealthBench)

**Data prerequisite (check first, may be free or a blocker):** Real-POCQi reports 620 OE-originated + 187
HealthBench items. Our vendored `data/answers.parquet` holds only the **620** (2,480 rows). If the full
Real-POCQi HF dataset already includes the 187 HealthBench questions **with all four systems' answers**
(likely, since Real-POCQi ran all four systems on both subsets), then **no answer generation is needed** —
re-fetch and grade. If it does **not**, this extension is **effectively blocked**: regenerating OpenEvidence
answers for new questions requires the OpenEvidence platform (no public API), which we cannot reproduce.

**Grading volume (assuming answers exist):**

| Task | Calls | Tokens/call | Tokens |
|---|---:|---:|---:|
| Rubric: 187 q × 4 systems × 4 judges | 2,992 | ~2,660 | ~7.96 M |
| Pairwise: 187 q × 3 opponents × 4 judges | 2,244 | ~3,400 | ~7.63 M |
| **Total** | **5,236** | — | **~15.6 M** (~7 M input / ~8.6 M output+thinking) |

**Cost** = 7 M × (input $/M) + 8.6 M × (output+thinking $/M), summed over the 4 judges' mix.
Illustrative blended rates (VERIFY against current pricing — the four judges span cheap Gemini-flash to
pricey GPT-5.5/Opus, and thinking tokens bill as output):

| Blended assumption | Estimate |
|---|---:|
| input ~$1.5/M, output+thinking ~$7/M | **~$70** |
| input ~$2/M, output+thinking ~$10/M | **~$100** |
| input ~$3/M, output+thinking ~$15/M | **~$150** |

**Plausible range: ~$60–160** (judge calls only; +$30–50 only in the unlikely event answers must be
regenerated, and OE answers may be unobtainable — see prerequisite). Value is high: a format×provenance
interaction directly tests the paper's home-field-provenance theme.

---

## #5 — Does judge reasoning effort change the verdict? (minimal vs high)

Two paths, very different cost:

**Path A — reuse Real-POCQi's released LLM judgments (≈ $0 API).** Real-POCQi already ran an LLM *pairwise*
experiment at minimal/automatic reasoning. If their **per-item** judgments are released and can be matched to
our items (same questions, answers, pairings), this is a **data join, not new grading** — compare their
minimal-reasoning verdicts against our high-reasoning cell B. Cost: **~$0** (engineering only). Risk: their
per-item judgments may not be released at the needed granularity, or may not match exactly.

**Path B — re-run our own judges at low/minimal reasoning (small).** Re-grade the existing 150-question cell
at low effort to compare against our high-effort results, on identical items:

| Task | Calls | Tokens/call (low effort) | Tokens |
|---|---:|---:|---:|
| Pairwise: 150 × 3 × 4 | 1,798 | ~1,900 | ~3.4 M |
| (optional) Rubric: 150 × 4 × 4 | 2,400 | ~1,200 | ~2.9 M |

Low-effort calls emit far fewer thinking tokens, so most volume is input.
**Cost: ~$10–25** (pairwise only) to **~$20–45** (pairwise + rubric), under the same rate assumptions.

**Recommendation:** try Path A first (free); fall back to Path B (~$20–45) if their per-item data don't match.

---

## Summary

| Extension | New grading? | Estimated API cost | Main caveat |
|---|---|---:|---|
| #3 provenance interaction | yes (~5.2 k judge calls) | **~$60–160** | needs the 187 HealthBench answers to exist in Real-POCQi; OE answers otherwise unobtainable |
| #5 reasoning-effort, Path A | no | **~$0** | needs Real-POCQi's per-item minimal-reasoning judgments, matchable |
| #5 reasoning-effort, Path B | yes (~1.8–4.2 k calls) | **~$20–45** | re-runs our judges at low effort on the existing 150 items |

All figures are token-based estimates under **assumed** per-token prices — confirm current rates for GPT-5.5,
Claude Opus 4.8, Grok-4.3, and Gemini-3.5-flash before authorizing spend. Rotate the shared API keys first.
