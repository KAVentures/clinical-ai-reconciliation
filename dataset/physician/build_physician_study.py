"""Build the physician 2x2-completion study: two blinded rating workbooks + author-only manifests.

Completes the local factorial:
                       Pairwise        Absolute rubric
    Physicians         new A'          new D
    LLM judges         existing B      existing C

The rubric arm emulates the Nature Medicine FORMAT (one blinded answer at a time, absolute 1-4, no
competing answer) on Real-POCQi CONTENT (same questions, same fixed answers, the SAME five Real-POCQi
axes as our LLM cells: accuracy, clinical utility, source quality, completeness, verifiability). It is a
Nature-FORMAT evaluation on Real-POCQi data, NOT an exact Nature replication.

Outputs (dataset/physician/):
  PHYSICIAN_ABSOLUTE_RUBRIC.xlsx   one blinded answer per row; 5 axes 1-4 + competence/confidence/comment
  PHYSICIAN_PAIRWISE.xlsx          Answer A vs B (randomized); 5 axis preferences + overall + comp/conf/comment
  author_only/  physician_sample.csv, rubric_response_manifest.csv, pairwise_item_manifest.csv,
                assignment_manifest.csv, data_dictionary.csv, AUTHOR_README.md   (** private **)

Deterministic (seed 62). No API calls. Reads judge/out/instrument_disagreement.csv + data/{questions,answers}.parquet.
"""
import os
import re
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ de-blinding scrub
# OpenEvidence answers cite openevidence.com URLs and name the brand, which de-blinds the OE answer
# (128 of 600 answers). Frontier models never self-identify by vendor, and clinical strings like SGPT/GPT
# (the enzyme) must NOT be touched. Neutralise only the OE brand/domain, KEEPING the citation structure so
# the verifiability / source-quality axes remain rateable.
def scrub_answer(t):
    t = str(t)
    t = re.sub(r'(https?://)?(www\.)?openevidence\.com', 'https://redacted-source.example', t, flags=re.I)
    t = re.sub(r'open\s*evidence', '[redacted source]', t, flags=re.I)
    return t
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
OUTJ = os.path.join(ROOT, 'judge', 'out')
DATA = os.path.join(ROOT, 'data')
AUTHOR = os.path.join(HERE, 'author_only')
OE = 'openevidence'
FRONTIER = ['gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']
AXES = ['accuracy', 'clinical_utility', 'source_quality', 'completeness', 'verifiability']
SEED = 62
TARGET_PAIRS = 70
RATINGS_PER_ITEM = 2          # >=2 physician ratings per item per arm (3 preferable)
ITEMS_PER_REVIEWER = 20       # ~15-25 items per physician

ARIAL = 'Arial'
HEADER_FILL = PatternFill('solid', fgColor='1F4E78')
YELLOW = PatternFill('solid', fgColor='FFF2CC')       # editable
LOCKFILL = PatternFill('solid', fgColor='F2F2F2')     # read-only reference
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# one-line axis definitions verbatim from judge/grade.py (the LLM rubric prompt)
AXIS_DEF = {
    'accuracy': "factual and clinical correctness of the claims",
    'clinical_utility': "usefulness for delivering high-quality clinical care",
    'source_quality': "quality/authority of the evidence and reasoning offered",
    'completeness': "comprehensiveness given what the question asks",
    'verifiability': "how easily a clinician could verify the answer's claims",
}
# detailed, axis-specific 1-4 anchors (elaborations faithful to the grade.py definitions + 1-4 scale)
ANCHORS = {
    'accuracy': {
        1: "Contains a clinically significant factual error or an unsafe recommendation; acting on it could harm a patient.",
        2: "Broadly on track but with a material inaccuracy, outdated guidance, or an unsupported claim needing correction before use.",
        3: "Clinically correct on all major points; any inaccuracies are minor and non-consequential.",
        4: "Fully correct and precise, including relevant thresholds, nuances and caveats; nothing a specialist would need to correct.",
    },
    'clinical_utility': {
        1: "Not usable at the point of care - vague, evasive, or fails to address the actual clinical decision.",
        2: "Limited use - partly addresses the question but omits actionable specifics (dose, timing, threshold, next step).",
        3: "Useful and actionable for the presenting question; a clinician could act on it with minor independent judgment.",
        4: "Directly and efficiently resolves the clinical decision with clear, actionable guidance tailored to the scenario.",
    },
    'source_quality': {
        1: "No supporting evidence or reasoning, or reasoning that is fallacious or misleading.",
        2: "Weak or generic justification; assertions largely unsupported or backed only by low-quality reasoning.",
        3: "Sound clinical reasoning and/or appropriate reference to relevant evidence or guidelines.",
        4: "Well grounded in high-quality, authoritative evidence (guidelines, primary literature) with transparent, rigorous reasoning.",
    },
    'completeness': {
        1: "Misses the central element of the question, or is so incomplete as to be misleading.",
        2: "Addresses part of the question but omits important components (e.g. contraindications, alternatives, follow-up).",
        3: "Covers the main components the question requires; only minor omissions.",
        4: "Thorough and appropriately scoped - the decision, caveats, contraindications and relevant follow-up, without padding.",
    },
    'verifiability': {
        1: "Claims cannot be checked - no citations, named sources, or checkable specifics.",
        2: "Hard to verify - few or vague references; a clinician would struggle to confirm key claims.",
        3: "Most key claims are checkable from the citations, named sources, or specific statements provided.",
        4: "Every material claim is readily verifiable via clear, specific, authoritative citations or references.",
    },
}
SCALE_LABEL = {1: "unacceptable", 2: "marginal", 3: "good", 4: "excellent"}

COMPETENCE = ['yes', 'partly', 'no']
CONFIDENCE = ['high', 'moderate', 'low']
PREF = ['A', 'B', 'tie']

EXTERNAL_NOTE = ("Ratings must represent your own final clinical judgment. External clinical resources may "
                 "be consulted when needed, but do not delegate completion of the rating form to another "
                 "person or system.")


# ------------------------------------------------------------------ sample
def select_pairs():
    df = pd.read_csv(os.path.join(OUTJ, 'instrument_disagreement.csv'))
    df = df[df.rubric_winner.isin([OE] + FRONTIER) & df.pw_llm_winner.isin([OE] + FRONTIER)].copy()
    spec = pd.read_parquet(os.path.join(DATA, 'questions.parquet')).set_index('question_id')['specialty']
    df['abs_margin'] = df.rubric_margin.abs()
    df['flip'] = df.instrument_flip_llm.astype(bool)
    g = df.groupby(['question_id', 'opponent'])
    pairs = g.agg(flip_any=('flip', 'any'), n_flips=('flip', 'sum'),
                  margin_mean=('abs_margin', 'mean')).reset_index()
    # signal axis = axis with the largest |rubric margin| for that pair (the most "decisive" axis)
    sig = df.loc[df.groupby(['question_id', 'opponent']).abs_margin.idxmax(), ['question_id', 'opponent', 'axis']]
    pairs = pairs.merge(sig, on=['question_id', 'opponent']).rename(columns={'axis': 'signal_axis'})
    pairs['specialty'] = pairs.question_id.map(spec)
    pairs['margin_bucket'] = pd.qcut(pairs.margin_mean, 3, labels=['small', 'mid', 'large'], duplicates='drop')

    rng = np.random.default_rng(SEED)
    # strata = opponent x flip_any x margin bucket ; even draw toward TARGET_PAIRS
    picks = []
    strata = [(o, f, m) for o in FRONTIER for f in (True, False) for m in ['small', 'mid', 'large']]
    per = max(1, TARGET_PAIRS // len(strata) + 1)
    for (o, f, m) in strata:
        sub = pairs[(pairs.opponent == o) & (pairs.flip_any == f) & (pairs.margin_bucket == m)]
        if len(sub):
            picks.append(sub.iloc[rng.choice(len(sub), min(per, len(sub)), replace=False)])
    sel = pd.concat(picks).drop_duplicates(subset=['question_id', 'opponent']).reset_index(drop=True)
    if len(sel) > TARGET_PAIRS:
        sel = sel.iloc[rng.choice(len(sel), TARGET_PAIRS, replace=False)].reset_index(drop=True)
    return sel.sort_values(['question_id', 'opponent'], kind='stable').reset_index(drop=True)


# ------------------------------------------------------------------ styling helpers
def hdr(ws, headers, row=1):
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        c.font = Font(name=ARIAL, size=10, bold=True, color='FFFFFF')
        c.fill = HEADER_FILL; c.border = BORDER
        c.alignment = Alignment(vertical='center', wrap_text=True, horizontal='center')


def add_dropdown(ws, col_letter, options, first, last):
    dv = DataValidation(type='list', formula1='"' + ','.join(options) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f'{col_letter}{first}:{col_letter}{last}')


def instructions_sheet(wb, title, task_lines, arm):
    ws = wb.create_sheet('Instructions')
    ws['A1'] = title
    ws['A1'].font = Font(name=ARIAL, size=14, bold=True)
    ws['A3'] = 'Reviewer initials:'; ws['A4'] = 'Date started:'; ws['A5'] = 'Your specialty / clinical background:'
    for rr in (3, 4, 5):
        ws.cell(row=rr, column=1).font = Font(name=ARIAL, size=10, bold=True)
        inp = ws.cell(row=rr, column=2); inp.fill = YELLOW; inp.border = BORDER
        inp.font = Font(name=ARIAL, size=10); inp.protection = Protection(locked=False)
    ws.cell(row=5, column=2).protection = Protection(locked=False)
    r = 7
    body = task_lines + ['', EXTERNAL_NOTE,
                         'You are blinded to which AI system produced each answer. Judge only the content.',
                         'Fill only the YELLOW cells on the "Ratings" sheet (drop-downs enforce allowed values). '
                         'The question and answer text are locked; please do not alter them.',
                         'A progress counter (rows scored / remaining) is shown at the top of the "Ratings" sheet.']
    for line in body:
        c = ws.cell(row=r, column=1, value=line)
        c.font = Font(name=ARIAL, size=10, bold=line.endswith(':'))
        c.alignment = Alignment(wrap_text=True, vertical='top')
        ws.merge_cells(start_row=r, start_column=1, end_row=r + 1, end_column=9)
        r += 3
    ws.column_dimensions['A'].width = 26
    for col in 'BCDEFGHI':
        ws.column_dimensions[col].width = 12
    ws.protection.sheet = True
    return ws


def anchors_sheet(wb):
    ws = wb.create_sheet('Rubric anchors')
    hdr(ws, ['Axis', 'Definition', 'Score 1 (unacceptable)', 'Score 2 (marginal)', 'Score 3 (good)', 'Score 4 (excellent)'])
    for i, ax in enumerate(AXES, start=2):
        ws.cell(row=i, column=1, value=ax.replace('_', ' ')).font = Font(name=ARIAL, size=10, bold=True)
        ws.cell(row=i, column=2, value=AXIS_DEF[ax]).font = Font(name=ARIAL, size=10)
        for k in (1, 2, 3, 4):
            ws.cell(row=i, column=2 + k, value=ANCHORS[ax][k]).font = Font(name=ARIAL, size=10)
        for j in range(1, 7):
            ws.cell(row=i, column=j).alignment = Alignment(wrap_text=True, vertical='top')
            ws.cell(row=i, column=j).border = BORDER
    ws.column_dimensions['A'].width = 16
    ws.column_dimensions['B'].width = 30
    for col in 'CDEF':
        ws.column_dimensions[col].width = 40
    ws.freeze_panes = 'A2'; ws.protection.sheet = True
    return ws


def worked_example_sheet(wb, headers, example_row, note):
    ws = wb.create_sheet('Worked example')
    ws['A1'] = 'Worked example - for reference only (not part of your ratings)'
    ws['A1'].font = Font(name=ARIAL, size=12, bold=True)
    hdr(ws, headers, row=3)
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=4, column=j, value=example_row.get(h, ''))
        c.font = Font(name=ARIAL, size=10); c.border = BORDER
        c.alignment = Alignment(wrap_text=h in ('clinical_question', 'blinded_answer', 'answer_A', 'answer_B', 'optional_comment'),
                                vertical='top')
    ws.cell(row=6, column=1, value=note).font = Font(name=ARIAL, size=10, italic=True)
    ws.merge_cells(start_row=6, start_column=1, end_row=7, end_column=len(headers))
    ws.cell(row=6, column=1).alignment = Alignment(wrap_text=True, vertical='top')
    for j, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(j)].width = 60 if 'answer' in h or h == 'clinical_question' else 16
    ws.protection.sheet = True
    return ws


def ratings_sheet(wb, headers, rows, fill_cols, validations, read_cols):
    ws = wb.create_sheet('Ratings')
    n = len(rows)
    first, last = 3, n + 2
    # row 1: progress counter
    score_col = get_column_letter(headers.index(fill_cols[0]) + 1)
    ws['A1'] = 'Rows scored:'
    ws['B1'] = f'=COUNTA({score_col}{first}:{score_col}{last})'
    ws['C1'] = 'Remaining:'
    ws['D1'] = f'={n}-COUNTA({score_col}{first}:{score_col}{last})'
    ws['E1'] = f'Total items: {n}'
    for cell in ('A1', 'B1', 'C1', 'D1', 'E1'):
        ws[cell].font = Font(name=ARIAL, size=10, bold=True, color='1F4E78')
    # row 2: headers
    hdr(ws, headers, row=2)
    # data
    for i, row in enumerate(rows, start=first):
        for j, h in enumerate(headers, 1):
            c = ws.cell(row=i, column=j, value=row.get(h, ''))
            wrap = h in ('clinical_question', 'blinded_answer', 'answer_A', 'answer_B', 'optional_comment')
            c.alignment = Alignment(wrap_text=wrap, vertical='top',
                                    horizontal='center' if h in validations else 'left')
            c.font = Font(name=ARIAL, size=10); c.border = BORDER
            if h in fill_cols:
                c.fill = YELLOW; c.protection = Protection(locked=False)
            elif h in read_cols:
                c.fill = LOCKFILL; c.protection = Protection(locked=True)
    # widths, dropdowns, freeze, protection
    for j, h in enumerate(headers, 1):
        w = 60 if ('answer' in h or h == 'clinical_question') else (12 if h in validations else 16)
        ws.column_dimensions[get_column_letter(j)].width = w
    for h, opts in validations.items():
        add_dropdown(ws, get_column_letter(headers.index(h) + 1), opts, first, last)
    ws.freeze_panes = 'B3'          # keep counter+header rows and item_id column visible
    ws.protection.sheet = True      # locks non-yellow cells; yellow cells are unlocked for entry
    return ws


# ------------------------------------------------------------------ workbook builders
def build_rubric_workbook(answers_df, path):
    headers = (['item_id', 'blinded_question_id', 'clinical_question', 'blinded_answer'] +
               [f'{ax}_score' for ax in AXES] +
               ['within_reviewer_competence', 'reviewer_confidence', 'optional_comment'])
    fill_cols = [f'{ax}_score' for ax in AXES] + ['within_reviewer_competence', 'reviewer_confidence', 'optional_comment']
    read_cols = ['item_id', 'blinded_question_id', 'clinical_question', 'blinded_answer']
    validations = {**{f'{ax}_score': ['1', '2', '3', '4'] for ax in AXES},
                   'within_reviewer_competence': COMPETENCE, 'reviewer_confidence': CONFIDENCE}
    rows = [{'item_id': r.response_id, 'blinded_question_id': r.blinded_question_id,
             'clinical_question': r.clinical_question, 'blinded_answer': r.answer_text}
            for r in answers_df.itertuples()]
    wb = Workbook(); wb.remove(wb.active)
    instructions_sheet(wb, 'Physician absolute-rubric evaluation - instructions', [
        'TASK: You will see ONE clinical question and ONE AI-generated answer at a time. Score that answer '
        'on its own merits - there is no competing answer to compare against.',
        'For each answer, give an integer 1-4 on each of the five axes (accuracy, clinical utility, source '
        'quality, completeness, verifiability). 1 = unacceptable, 2 = marginal, 3 = good, 4 = excellent.',
        'Use the detailed, axis-specific anchors on the "Rubric anchors" sheet - not just the one-word labels.',
        'within_reviewer_competence: is this question within your area of competence? yes / partly / no.',
        'reviewer_confidence: your confidence in this rating - high / moderate / low.',
        'optional_comment: brief free text (e.g. any safety concern). Optional.',
    ], arm='rubric')
    anchors_sheet(wb)
    ex_headers = headers
    example = {'item_id': 'RESP-EXAMPLE', 'blinded_question_id': 'QID-EX',
               'clinical_question': '(example) In a 68-year-old with new AF and CrCl 40 mL/min, which DOAC and dose?',
               'blinded_answer': '(example answer text would appear here)',
               'accuracy_score': 3, 'clinical_utility_score': 4, 'source_quality_score': 3,
               'completeness_score': 3, 'verifiability_score': 2,
               'within_reviewer_competence': 'yes', 'reviewer_confidence': 'high',
               'optional_comment': 'Correct DOAC choice; dose caveat could be more explicit.'}
    worked_example_sheet(wb, ex_headers, example,
                         'Score each answer independently on all five axes using the anchors sheet.')
    ratings_sheet(wb, headers, rows, fill_cols, validations, read_cols)
    wb.save(path)
    return len(rows)


def build_pairwise_workbook(pw_df, path):
    headers = (['item_id', 'blinded_question_id', 'clinical_question', 'answer_A', 'answer_B'] +
               [f'{ax}_preference' for ax in AXES] +
               ['overall_preference', 'within_reviewer_competence', 'reviewer_confidence', 'optional_comment'])
    fill_cols = ([f'{ax}_preference' for ax in AXES] + ['overall_preference',
                 'within_reviewer_competence', 'reviewer_confidence', 'optional_comment'])
    read_cols = ['item_id', 'blinded_question_id', 'clinical_question', 'answer_A', 'answer_B']
    validations = {**{f'{ax}_preference': PREF for ax in AXES}, 'overall_preference': PREF,
                   'within_reviewer_competence': COMPETENCE, 'reviewer_confidence': CONFIDENCE}
    rows = [{'item_id': r.item_id, 'blinded_question_id': r.blinded_question_id,
             'clinical_question': r.clinical_question, 'answer_A': r.answer_A, 'answer_B': r.answer_B}
            for r in pw_df.itertuples()]
    wb = Workbook(); wb.remove(wb.active)
    instructions_sheet(wb, 'Physician pairwise-preference evaluation - instructions', [
        'TASK: You will see ONE clinical question and TWO AI-generated answers, Answer A and Answer B '
        '(order is randomised). For each of the five axes say which answer is better: A, B, or tie.',
        'Axes: accuracy, clinical utility, source quality, completeness, verifiability (defined the same way '
        'as on the rubric - see the row comments / the study rubric).',
        'overall_preference: all things considered, which answer would you rather give a colleague - A / B / tie.',
        'within_reviewer_competence: is this question within your area of competence? yes / partly / no.',
        'reviewer_confidence: your confidence in this comparison - high / moderate / low.',
        'optional_comment: brief free text (e.g. any safety concern). Optional.',
    ], arm='pairwise')
    example = {'item_id': 'PW-EXAMPLE', 'blinded_question_id': 'QID-EX',
               'clinical_question': '(example) In a 68-year-old with new AF and CrCl 40 mL/min, which DOAC and dose?',
               'answer_A': '(example Answer A text)', 'answer_B': '(example Answer B text)',
               'accuracy_preference': 'A', 'clinical_utility_preference': 'A', 'source_quality_preference': 'tie',
               'completeness_preference': 'A', 'verifiability_preference': 'B', 'overall_preference': 'A',
               'within_reviewer_competence': 'yes', 'reviewer_confidence': 'moderate',
               'optional_comment': 'A gives the renal dose adjustment; B is better referenced.'}
    worked_example_sheet(wb, headers, example, 'Choose A, B, or tie on each axis, then an overall preference.')
    ratings_sheet(wb, headers, rows, fill_cols, validations, read_cols)
    wb.save(path)
    return len(rows)


# ------------------------------------------------------------------ assignment
def assign_reviewers(rubric_ids, rubric_q, pw_ids, pw_q):
    """>=RATINGS_PER_ITEM distinct reviewers per item; ~ITEMS_PER_REVIEWER each; a reviewer never sees the
    same question twice or in both arms. Returns list of dict rows + reviewer count."""
    items = ([('rubric', i, rubric_q[i]) for i in rubric_ids] +
             [('pairwise', i, pw_q[i]) for i in pw_ids])
    total_slots = len(items) * RATINGS_PER_ITEM
    n_rev = max(RATINGS_PER_ITEM + 1, -(-total_slots // ITEMS_PER_REVIEWER))  # ceil
    reviewers = [f'REV-{k + 1:02d}' for k in range(n_rev)]
    seen_q = {r: set() for r in reviewers}   # questions a reviewer already has (either arm)
    load = {r: 0 for r in reviewers}
    order = {r: 0 for r in reviewers}
    rng = np.random.default_rng(SEED)
    rows = []
    for arm, item, q in items:
        chosen = []
        cand = sorted(reviewers, key=lambda r: (load[r], rng.random()))
        for r in cand:
            if len(chosen) == RATINGS_PER_ITEM:
                break
            if q in seen_q[r] or load[r] >= ITEMS_PER_REVIEWER:
                continue
            chosen.append(r); seen_q[r].add(q); load[r] += 1; order[r] += 1
            rows.append({'reviewer_id': r, 'packet_id': f'{r}_{arm}', 'format_arm': arm,
                         'item_id': item, 'question_id': q, 'assignment_order': order[r]})
    return rows, n_rev, load


# ------------------------------------------------------------------ main
def main():
    os.makedirs(AUTHOR, exist_ok=True)
    q = pd.read_parquet(os.path.join(DATA, 'questions.parquet')).set_index('question_id')
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    ANS = {(r.question_id, r.provider_key): scrub_answer(r.answer_markdown) for _, r in a.iterrows()}

    pairs = select_pairs()
    pairs.to_csv(os.path.join(AUTHOR, 'physician_sample.csv'), index=False)

    # blinded question ids (stable per question)
    uq = sorted(set(pairs.question_id))
    qid_map = {qid: f'QID-{i + 1:03d}' for i, qid in enumerate(uq)}

    # ---- rubric arm: unique (question, provider) answers ----
    ans_keys = set()
    for r in pairs.itertuples():
        ans_keys.add((r.question_id, OE)); ans_keys.add((r.question_id, r.opponent))
    ans_keys = sorted(ans_keys)
    rng = np.random.default_rng(SEED)
    rub_rows, rub_manifest = [], []
    for i, (qid, prov) in enumerate(ans_keys):
        rid = f'RESP-{i + 1:04d}'
        rub_rows.append({'response_id': rid, 'blinded_question_id': qid_map[qid],
                         'clinical_question': q.loc[qid, 'question_text'], 'answer_text': ANS[(qid, prov)]})
        rub_manifest.append({'response_id': rid, 'blinded_question_id': qid_map[qid],
                             'question_id': qid, 'true_provider': prov})
    rub_df = pd.DataFrame(rub_rows)
    rub_q = {r['response_id']: r['question_id'] for r in rub_manifest}

    # ---- pairwise arm: one row per (question, opponent), A/B randomized independently ----
    pw_rows, pw_manifest = [], []
    for i, r in enumerate(pairs.itertuples()):
        pid = f'PW-{i + 1:03d}'
        oe_is_A = bool(rng.integers(0, 2))
        ansA, ansB = (ANS[(r.question_id, OE)], ANS[(r.question_id, r.opponent)]) if oe_is_A \
            else (ANS[(r.question_id, r.opponent)], ANS[(r.question_id, OE)])
        provA, provB = (OE, r.opponent) if oe_is_A else (r.opponent, OE)
        pw_rows.append({'item_id': pid, 'blinded_question_id': qid_map[r.question_id],
                        'clinical_question': q.loc[r.question_id, 'question_text'],
                        'answer_A': ansA, 'answer_B': ansB})
        pw_manifest.append({'item_id': pid, 'blinded_question_id': qid_map[r.question_id],
                            'question_id': r.question_id, 'opponent': r.opponent,
                            'slot_A_provider': provA, 'slot_B_provider': provB})
    pw_df = pd.DataFrame(pw_rows)
    pw_q = {r['item_id']: r['question_id'] for r in pw_manifest}

    n_rub = build_rubric_workbook(rub_df, os.path.join(HERE, 'PHYSICIAN_ABSOLUTE_RUBRIC.xlsx'))
    n_pw = build_pairwise_workbook(pw_df, os.path.join(HERE, 'PHYSICIAN_PAIRWISE.xlsx'))

    # ---- assignment ----
    assign, n_rev, load = assign_reviewers([r['response_id'] for r in rub_manifest], rub_q,
                                           [r['item_id'] for r in pw_manifest], pw_q)

    # ---- author-only manifests ----
    pd.DataFrame(rub_manifest).to_csv(os.path.join(AUTHOR, 'rubric_response_manifest.csv'), index=False)
    pd.DataFrame(pw_manifest).to_csv(os.path.join(AUTHOR, 'pairwise_item_manifest.csv'), index=False)
    pd.DataFrame(assign).to_csv(os.path.join(AUTHOR, 'assignment_manifest.csv'), index=False)
    write_data_dictionary(os.path.join(AUTHOR, 'data_dictionary.csv'))
    write_author_readme(os.path.join(AUTHOR, 'AUTHOR_README.md'), len(pairs), n_rub, n_pw, n_rev, load)

    print(f"pairs selected        : {len(pairs)}  (opponents { pairs.opponent.value_counts().to_dict() })")
    print(f"rubric answers (rows) : {n_rub}  -> PHYSICIAN_ABSOLUTE_RUBRIC.xlsx")
    print(f"pairwise items (rows) : {n_pw}  -> PHYSICIAN_PAIRWISE.xlsx")
    print(f"assignment            : {n_rev} reviewers, ~{ITEMS_PER_REVIEWER} items each, "
          f">={RATINGS_PER_ITEM} ratings/item; loads {sorted(set(load.values()))}")
    print(f"author-only outputs   : {AUTHOR}")


def write_data_dictionary(path):
    rows = []
    for wb_name, fields in [
        ('both', [('item_id', 'RESP-#### (rubric) or PW-### (pairwise)', 'blinded rating-unit id'),
                  ('blinded_question_id', 'QID-###', 'blinded question id; same id = same clinical question'),
                  ('clinical_question', 'text (locked)', 'the point-of-care question'),
                  ('within_reviewer_competence', 'yes / partly / no', 'is the item within the reviewer competence'),
                  ('reviewer_confidence', 'high / moderate / low', 'reviewer confidence in this rating'),
                  ('optional_comment', 'free text', 'optional note / safety concern')]),
        ('rubric', [('blinded_answer', 'text (locked)', 'one AI answer, provider hidden'),
                    *[(f'{ax}_score', '1 / 2 / 3 / 4', f'absolute score on {ax} (anchors on Rubric anchors sheet)') for ax in AXES]]),
        ('pairwise', [('answer_A', 'text (locked)', 'first answer (A/B order randomised per item)'),
                      ('answer_B', 'text (locked)', 'second answer'),
                      *[(f'{ax}_preference', 'A / B / tie', f'which answer is better on {ax}') for ax in AXES],
                      ('overall_preference', 'A / B / tie', 'overall preferred answer')]),
        ('author_only', [('true_provider / slot_*_provider', 'openevidence|gpt-5.5|claude-opus-4-8|gemini-3.1-pro', 'un-blinding map (never sent to reviewers)'),
                         ('reviewer_id', 'REV-##', 'assigned physician (placeholder; replace with roster)'),
                         ('format_arm', 'rubric / pairwise', 'which arm the assignment row is for'),
                         ('assignment_order', 'int', 'order the item is presented to that reviewer')]),
    ]:
        for name, allowed, desc in fields:
            rows.append({'workbook': wb_name, 'field': name, 'allowed_values': allowed, 'description': desc})
    pd.DataFrame(rows).to_csv(path, index=False)


def write_author_readme(path, n_pairs, n_rub, n_pw, n_rev, load):
    txt = f"""# Author-only files — DO NOT SEND TO REVIEWERS

These un-blind the study and define the assignment. Keep private.

- `physician_sample.csv` — the {n_pairs} selected (question, opponent) pairs + strata (flip/margin/opponent/specialty/signal_axis).
- `rubric_response_manifest.csv` — RESP-#### -> question_id + true_provider (un-blinds the rubric workbook, {n_rub} answers).
- `pairwise_item_manifest.csv` — PW-### -> question_id, opponent, slot_A/slot_B true providers (un-blinds A/B, {n_pw} items).
- `assignment_manifest.csv` — reviewer_id x item x arm; {n_rev} placeholder reviewers, ~{ITEMS_PER_REVIEWER} items each,
  >= {RATINGS_PER_ITEM} ratings/item, and NO reviewer sees the same question twice or in both arms. Loads: {sorted(set(load.values()))}.
- `data_dictionary.csv` — every field + allowed values.

Determinism: random seed = {SEED} (sample selection, A/B randomisation, assignment).

## To run the study
1. Replace REV-## with your real physician roster in `assignment_manifest.csv` (or re-run with your N).
   The two workbooks are MASTER instruments (all items). Slice each reviewer's ~15-25 assigned rows into a
   per-reviewer copy before sending (ask the author tool to generate per-reviewer files if wanted).
2. Send reviewers ONLY `PHYSICIAN_ABSOLUTE_RUBRIC.xlsx` / `PHYSICIAN_PAIRWISE.xlsx` (their slice). Never send this folder.
3. On return, join on item_id via the manifests to un-blind, then run the 2x2 (D vs C, A' vs B, interaction).

## Caveat (record in the paper)
The physician rubric uses DETAILED axis-specific anchors (this study), whereas the LLM rubric (cell C) used
the shorter grade.py anchors. The construct (five Real-POCQi axes) is identical, but the anchor wording is
richer for physicians — so D vs C mixes rater with anchor detail. Disclose this. Specialty matching is not
available; retain all ratings and run a sensitivity analysis excluding out-of-competence / low-confidence rows.
"""
    open(path, 'w').write(txt)


if __name__ == '__main__':
    main()
