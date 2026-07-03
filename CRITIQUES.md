# Methodological critiques of the two source studies

Verified from primary sources this session: Nature methods from the PDF (`/tmp/nature_full.txt`,
Methods lines 561–614, 815–832); Real-POCQi from arXiv:2606.28960 (abstract + HTML full text).
Two critiques the reconciliation paper must raise, plus supporting cross-study confounds.

---

## Critique 1 — Comparator set omits the AI that clinicians actually use

Both studies benchmark **bare frontier API models**. Neither includes the **ChatGPT product**
(consumer app or any clinician-facing/enterprise ChatGPT deployment) as its own arm.

- **Real-POCQi comparators:** Claude Opus 4.8, Gemini 3.1 Pro, GPT-5.5, OpenEvidence. Verbatim:
  *"All systems were queried programmatically via their respective APIs."* No ChatGPT product.
- **Nature comparators:** GPT-5.2, Gemini 3.1 Pro Preview, Claude Opus 4.6 (all API); OpenEvidence +
  UpToDate Expert AI (browser); Google Search AI Overview (RCQ only). No ChatGPT product.

**Why this is a real gap, not a nitpick.** The unit clinicians touch at the point of care is a
*product*, not a raw model endpoint. The ChatGPT product wraps the base model in a system prompt,
retrieval/browsing, memory, formatting, and clinical safety guardrails — all of which materially move
the exact axes these studies score (accuracy, completeness, safety, clarity). Evaluating the bare API:

- **understates** real-world frontier performance where the product's retrieval/curation would help, and
- **overstates** it where the product's safety hedging would change tone/completeness.

The asymmetry is sharpest against **OpenEvidence, which is itself a curated clinical product** (its own
retrieval + citation layer). So both papers pit *a product* (OE) against *bare model endpoints* on the
retrieval dimension. Nature's Methods even encode this asymmetry structurally: frontier models via API,
clinical tools *"queried manually through browser interfaces."* Real-POCQi is cleaner (API for all,
including OE) but still omits the product experience entirely.

**Recommendation for our paper.** Add a **product-vs-endpoint arm**: evaluate the ChatGPT product (and,
where available, a clinician deployment) alongside the API model of the *same* base version, on the
*same* queries. This isolates how much of any "frontier vs OE" gap is the *base model* vs the *product
scaffolding around it* — the single most policy-relevant question for a clinician deciding what to use.

---

## Critique 2 — Reasoning effort is unreported (Nature) or only "automatic" (Real-POCQi)

Reasoning effort / thinking budget is the **single largest controllable performance lever** for current
models and it changes leaderboard order. Neither study pins or fully reports it.

- **Nature:** reports *"fixed, deterministic parameters,"* *"temperature was set to 0.0,"* *"a fixed
  generation seed of 62,"* and *"Search tools were enabled."* **Reasoning effort is never stated.** The
  cost table footnote confirms reasoning *was* used — *"do not include reasoning tokens"* — but at an
  **unspecified effort level**. Note also that temperature=0.0 is largely inert for reasoning models,
  which sample the reasoning trace regardless; reporting it can create a false impression of determinism.
- **Real-POCQi:** discloses more but still does not pin a level — verbatim: *"Thinking was automatically
  determined by the LLM."* Temperature=0.0, seed=42, web search enabled. "Automatic" thinking is
  provider-default and can differ by model, by prompt, and across API updates — not reproducible.

**Why this matters.** A model set to low vs high reasoning effort can swing double digits on exactly the
benchmarks in play (MedQA, HealthBench). If Nature ran frontier models at default/low effort, its
"frontier beats OE" MedQA/HealthBench margins may be *under*-powered for the frontier side; if
Real-POCQi's "automatic" thinking differed across its three frontier models, its head-to-head is not
holding reasoning constant. **Neither result is reproducible without this number.**

**What our study does differently (and verifies).** We pin **reasoning effort = high** for all four
judges and **verify token consumption on the real task** (`judge/verify_thinking.py` →
`out/thinking_evidence.json`): GPT-5.5 3,071 reasoning tokens, Grok-4.3 1,880, Gemini-3.5-flash 922
thought tokens, Opus-4.8 443 thinking tokens (Anthropic's only accepted high mode here is
`thinking.type=adaptive` + `output_config.effort=high`; adaptive emits ~0 thinking on trivial items, so
we confirmed on a real long clinical answer). This is the transparency both source studies lack.

---

## Supporting cross-study confounds (uncontrolled when comparing the two papers)

These are not "errors" in either paper but they mean the two leaderboards are **not directly
comparable**, which is itself part of the reconciliation story:

| Dimension | Nature | Real-POCQi | Consequence |
|---|---|---|---|
| GPT version | GPT-5.2 (2025-12-11) | **GPT-5.5** (newer) | Real-POCQi tested *newer* frontier models and still found them losing to OE → model version cannot explain OE's Real-POCQi win. But version differs across papers, so their absolute numbers aren't comparable. |
| Claude version | Opus 4.6 | **Opus 4.8** (newer) | same as above |
| Gemini version | 3.1 Pro Preview | 3.1 Pro | roughly matched |
| Reasoning effort | unreported | "automatic" | neither reproducible; not held constant across the two studies |
| Seed | 62 | 42 | independent runs (trivial) |
| Access path | frontier=API, clinical tools=browser | **API for all (incl. OE)** | Nature has an API-vs-browser stack asymmetry; Real-POCQi does not |
| Length handling | not normalized (deliberate) | not normalized | length is an uncontrolled driver in both; must be broken in our length-matched sub-study |
| Instrument | absolute 1–4 rubric + LLM-judge HealthBench | blinded human pairwise | the core confound our existence proof isolates (FINDINGS §5) |

**Net:** the newer-model point is the sharpest — Real-POCQi handed the frontier side its *newest*
weights and OE still won on human pairwise preference, while Nature's *older* frontier weights won under
rubric scoring. That pattern is far more consistent with an **instrument** effect than a **model-version**
effect, corroborating the existence proof.
