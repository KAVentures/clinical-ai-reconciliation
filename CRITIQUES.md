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

---

## Critique 3 — Instrument-level construct problems (both directions)

**3a. The absolute 1–4 rubric has a noise floor and a compression ceiling.** On Nature's RCQ benchmark the
frontier trio finishes Gemini 3.62 / GPT 3.54 / Claude 3.52 — a **0.10-point spread across the top three**
— with OE at 3.24, on n=100 at Krippendorff α ≈ 0.10–0.20. At that agreement and sample size the
between-frontier order is inside measurement noise, and the OE gap is a fraction of one rubric point. A 1–4
integer scale also has almost no headroom: competent answers pile up at 3–4, so the instrument cannot
express *how much* better one good answer is, and small stylistic preferences get amplified into rank order
because the usable dynamic range is one to two points. This compression is the mechanism by which a
−0.127-point mean gap becomes a −29 pp win-difference in our cell C (MANUSCRIPT §3.3a): the rubric floor/
ceiling turns near-ties into decisive-looking orderings. A coarse absolute rubric is a **low-resolution
instrument for near-parity systems.**

**3b. Pairwise preference has the opposite, symmetric bias.** Forced-choice preference rewards surface
features — length, formatting, citation presence, confident tone — independently of correctness.
Real-POCQi's own data show it: OE's between-groups accuracy "halo" of **+11.4 pp collapses to +1.5 pp (NS)**
once we condition on questions rated both with and without citations (`analysis/analyze.py`), i.e. much of
the preference edge tracks *citations present*, not accuracy. A preference instrument movable ~10 pp by
attaching references is as construct-contaminated, oppositely, as a compressed rubric. **Neither instrument
is a clean measure of clinical quality**; our claim is the relative one (switching biased instruments flips
the winner), not that either endpoint is truth.

**3c. The five axes are near-collinear, not five independent measurements.** Source quality and
verifiability both essentially ask "are there real citations"; accuracy/completeness/clinical-utility are
strongly co-scored. Per-axis "significance" counts are therefore not five independent confirmations, and
"OE wins on all five axes" is closer to winning on **one or two latent constructs** measured five ways. We
treat the axis set as a small number of correlated constructs and lean on accuracy + the decomposition
rather than tallying axes.

**3d. Real-POCQi itself hypothesizes the instrument matters (JudgmentBench).** Real-POCQi attributes its
divergence from rubric benchmarks to the instrument and cites **JudgmentBench** (its ref 8), which reports
that in high-expertise domains **head-to-head preference recovers expert judgment better than absolute
rubric scoring**. This (i) means our *idea* is anticipated — our contribution is the controlled execution
+ rater/instrument decomposition, not the hypothesis — and (ii) is directional: if JudgmentBench
generalizes, the pairwise (OE-favoring) instrument is the *more valid* one, so "the instruments disagree"
would sharpen to "the more valid instrument favors OE." We do **not** assert this (untested generalization;
our rubric is LLM-administered; a 1–4 scale is a weak rubric), but flag it as what the missing human-rubric
cell D would adjudicate.

---

## Critique 4 — Real-POCQi's data pipeline is winner-run, with rater-composition confounds

These are symmetric in spirit to Nature's insider RCQ pipeline; naming them is part of treating both
studies even-handedly (not weaponizing only the anti-Nature ones).

- **End-to-end control by the party under study.** OpenEvidence selected the query pool (≈3,600 → 620
  after filtering) from its **own platform traffic**, LLM-paraphrased queries (Opus 4.6) for
  de-identification, and paid the physician raters. Sampling, wording, and rater incentives are all
  insider-controlled. (Nature's RCQ is analogously NYU-deployment-run.)
- **Rater familiarity confound — supports the instrument thesis.** ~**52% of raters were OpenEvidence
  users**, and the OE accuracy edge is **larger among OE-users (~+33.8 pp) than non-users (~+22.6 pp)**.
  Habituation to OE's house format inflates the human-pairwise cell (A) for reasons unrelated to
  correctness — exactly a preference-instrument artifact a rubric would not reward. This *strengthens* the
  reconciliation: part of cell A's edge is familiarity, not accuracy.
- **Low response/completion.** Physician recruitment yielded low single-digit response/completion fractions
  (~1–2% order), so the panel is self-selected; combined with the familiarity gradient, cell A's signal
  carries a selection component we cannot remove from public data. → We do not treat cell A as ground truth;
  we lean on the within-panel instrument decomposition (MANUSCRIPT §4.5).
- **Near-parity middle, contested boundary.** Stripped to robust content, both studies resolve only the
  extremes (OE top under pairwise; GPT-class strong under rubric); each frontier trio is near-parity. The
  reproducible cross-study disagreement is narrow — **where OE sits relative to a bunched frontier cluster**
  — and that one placement is what the instrument flips.

---

## Critique 5 — Nature's access-path asymmetry and reviewer/COI overlap

- **Browser-vs-API stack asymmetry.** Nature queried frontier models via API but clinical tools
  (OpenEvidence, UpToDate) **manually through browser interfaces**. Manual browser querying introduces
  session state, UI-surfaced summaries vs raw model output, timing, and transcription variance that API
  calls avoid — a data-quality asymmetry applied precisely to the non-frontier arm it disfavors.
- **COI overlapping the winner.** The Nature senior author reports industry equity/consulting including
  **Google**; Gemini (a Google model) is the top scorer on the headline RCQ leaderboard. This is disclosed
  and not evidence of misconduct, but it is a COI that overlaps the declared winner and belongs in any
  even-handed reconciliation, symmetrically with OpenEvidence running Real-POCQi's pipeline.
