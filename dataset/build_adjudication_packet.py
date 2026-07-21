"""Build a blinded clinician rating/adjudication packet from the stratified sample.

Collapses the 90 (question x axis x opponent) sampled items to unique (question, opponent) COMPARISONS
(the natural rating unit: a doctor rates both answers on all five axes and adjudicates them once), joins the
verbatim question + the two answers, and assigns a randomized, de-identified A/B slot per comparison.

Writes (all in dataset/adjudication/):
  ratings_template.csv  one row per comparison: item_id, specialty, question, answer_A, answer_B + BLANK
                        fill-in columns (rubric 1-4 per answer per axis; pairwise A/B/tie per axis;
                        adjudication fields per answer; overall preferred; notes).
  scales.csv            legend / allowed values for every fill-in column.
  instructions.csv      step-by-step instructions text (one instruction per row).
  blinding_key.csv      item_id, slot -> true provider.  ** KEEP PRIVATE — do NOT send to raters. **

Deterministic (seed 62). No API calls. Reads dataset/human_study_sample.csv + data/{questions,answers}.parquet.
"""
import os, csv
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
ADJ = os.path.join(HERE, 'adjudication')
OE = 'openevidence'
SEED = 62

RUBRIC_AXES = ['accuracy', 'clinical_utility', 'source_quality', 'completeness', 'verifiability']

# fill-in columns (blank for raters) and their allowed values (for the scales sheet + validation)
SCALES = [
    *[(f'rubric_A_{ax}', '1-4  (1 unacceptable, 2 marginal, 3 good, 4 excellent)') for ax in RUBRIC_AXES],
    *[(f'rubric_B_{ax}', '1-4  (1 unacceptable, 2 marginal, 3 good, 4 excellent)') for ax in RUBRIC_AXES],
    *[(f'prefer_{ax}', 'A / B / tie  (which answer is better on this axis)') for ax in RUBRIC_AXES],
    ('adj_A_factual_correctness', 'correct / minor_error / major_error'),
    ('adj_A_material_omission', 'none / minor / major'),
    ('adj_A_potential_harm', 'none / low / moderate / high'),
    ('adj_A_appropriately_qualified', 'yes / partially / no'),
    ('adj_A_citation_support', 'supported / partial / unsupported / no_citations'),
    ('adj_B_factual_correctness', 'correct / minor_error / major_error'),
    ('adj_B_material_omission', 'none / minor / major'),
    ('adj_B_potential_harm', 'none / low / moderate / high'),
    ('adj_B_appropriately_qualified', 'yes / partially / no'),
    ('adj_B_citation_support', 'supported / partial / unsupported / no_citations'),
    ('overall_preferred_answer', 'A / B / tie  (all things considered, which answer would you give a colleague)'),
    ('rater_notes', 'free text (optional): key reason, any safety concern'),
]
FILL_COLS = [name for name, _ in SCALES]

INSTRUCTIONS = [
    "PURPOSE: You are helping evaluate AI-generated answers to real point-of-care clinical questions. For each item you will see one clinical QUESTION and TWO answers, labelled Answer A and Answer B. You do not know which AI system produced either answer, and the A/B order is randomised per item. Please judge only the content.",
    "TIME: about 6-10 minutes per item. You do NOT have to complete all items in one sitting; save and continue.",
    "WHAT TO DO for each row on the 'Ratings' sheet, left to right:",
    "1) RUBRIC (rubric_A_* and rubric_B_*): score EACH answer separately on all five axes, 1-4 (1 unacceptable, 2 marginal, 3 good, 4 excellent). Score the answer's content only.",
    "2) PAIRWISE (prefer_*): for each axis, say which answer is better - A, B, or tie.",
    "3) ADJUDICATION (adj_A_* and adj_B_*): for EACH answer, record factual correctness, whether there is a clinically material omission, potential for harm if a clinician followed it, whether recommendations are appropriately qualified/hedged, and whether any cited evidence supports the claims. Use the allowed values on the 'Scales' sheet.",
    "4) OVERALL: overall_preferred_answer - all things considered, which answer would you rather give a colleague (A / B / tie). Add a brief note if useful, especially any safety concern.",
    "IMPORTANT: score independently - do not assume A and B differ, and do not let your rubric scores dictate your pairwise choice. If an answer is unsafe, flag it in adj_*_potential_harm and the notes regardless of other scores.",
    "BLINDING: please do not try to guess or look up which system wrote which answer. Return the file with only the fill-in columns completed (do not edit the question or answer text).",
    "Allowed values for every fill-in column are on the 'Scales' sheet. Questions? Contact the study author.",
]


def main():
    os.makedirs(ADJ, exist_ok=True)
    sample = pd.read_csv(os.path.join(HERE, 'human_study_sample.csv'))
    q = pd.read_parquet(os.path.join(DATA, 'questions.parquet')).set_index('question_id')
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    ans = {(r.question_id, r.provider_key): r.answer_markdown for _, r in a.iterrows()}

    # collapse to unique (question, opponent) comparisons
    comps = (sample[['question_id', 'opponent', 'specialty']]
             .drop_duplicates(subset=['question_id', 'opponent'])
             .sort_values(['question_id', 'opponent'], kind='stable')
             .reset_index(drop=True))

    rng = np.random.default_rng(SEED)
    rating_rows, key_rows = [], []
    for i, r in comps.iterrows():
        item_id = f"ITM-{i + 1:03d}"
        oe_ans = ans.get((r.question_id, OE))
        opp_ans = ans.get((r.question_id, r.opponent))
        if oe_ans is None or opp_ans is None:
            continue
        oe_is_A = bool(rng.integers(0, 2))          # randomise slot per comparison
        answer_A, answer_B = (oe_ans, opp_ans) if oe_is_A else (opp_ans, oe_ans)
        prov_A, prov_B = (OE, r.opponent) if oe_is_A else (r.opponent, OE)
        row = {'item_id': item_id, 'specialty': r.specialty,
               'clinical_question': q.loc[r.question_id, 'question_text'],
               'answer_A': answer_A, 'answer_B': answer_B}
        for c in FILL_COLS:
            row[c] = ''                              # blank for the rater
        rating_rows.append(row)
        key_rows.append({'item_id': item_id, 'question_id': r.question_id,
                         'slot_A_provider': prov_A, 'slot_B_provider': prov_B, 'opponent': r.opponent})

    cols = ['item_id', 'specialty', 'clinical_question', 'answer_A', 'answer_B'] + FILL_COLS
    pd.DataFrame(rating_rows)[cols].to_csv(os.path.join(ADJ, 'ratings_template.csv'),
                                           index=False, quoting=csv.QUOTE_ALL)
    pd.DataFrame(SCALES, columns=['fill_in_column', 'allowed_values']) \
        .to_csv(os.path.join(ADJ, 'scales.csv'), index=False, quoting=csv.QUOTE_ALL)
    pd.DataFrame({'step': range(1, len(INSTRUCTIONS) + 1), 'instruction': INSTRUCTIONS}) \
        .to_csv(os.path.join(ADJ, 'instructions.csv'), index=False, quoting=csv.QUOTE_ALL)
    pd.DataFrame(key_rows).to_csv(os.path.join(ADJ, 'blinding_key.csv'), index=False)

    print(f"comparisons (rating rows) = {len(rating_rows)}   fill-in columns = {len(FILL_COLS)}")
    print(f"wrote dataset/adjudication/: ratings_template.csv, scales.csv, instructions.csv, blinding_key.csv")
    print("** blinding_key.csv is PRIVATE - keep it; do NOT send it to the raters. **")


if __name__ == '__main__':
    main()
