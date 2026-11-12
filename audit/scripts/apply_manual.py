"""Apply a human data entry (submitted from the dashboard as a GitHub issue) to tracker.csv.

Usage: python audit/scripts/apply_manual.py --body-file issue.md --author <login> --issue <n> [--date YYYY-MM-DD]

The issue body contains a ```json block written by the dashboard:
  {"hospital_id": "...", "fields": {"V": "no", "AI": 400, ...}, "evidence": "...", "sources": ["https://..."]}
Only the fields listed are changed. Values: "yes"/"no" for graded fields; AI is the max FPL percent (e.g. 400).
Each change is logged in changelog.csv with run_id <date>-manual-issue<n>, so the agent keeps
human-entered values when it later can't read the source document (see apply_results.py).
Writes audit/work/summary.md (commit message) and exits non-zero with a readable error on bad input."""
import argparse, csv, datetime, json, re, sys
from openpyxl.utils import column_index_from_string as ci
from lib import AUDIT, CHANGELOG, COLUMNS, BINARY, GRADED, read_tracker, write_tracker, grade, norm

ap = argparse.ArgumentParser()
ap.add_argument('--body-file', required=True)
ap.add_argument('--author', required=True)
ap.add_argument('--issue', required=True)
ap.add_argument('--date', default=datetime.date.today().isoformat())
a = ap.parse_args()


def fail(msg):
    (AUDIT / 'work').mkdir(exist_ok=True)
    (AUDIT / 'work' / 'error.md').write_text(msg)
    sys.exit(msg)


body = open(a.body_file, encoding='utf-8').read()
m = re.search(r'```json\s*(\{.*?\})\s*```', body, re.S)
if not m:
    fail('Could not find the data block (```json ... ```) in the issue. Please submit entries from the dashboard form.')
try:
    entry = json.loads(m.group(1))
except json.JSONDecodeError as e:
    fail(f'The data block is not valid JSON: {e}')

rows = read_tracker()
by_id = {r['hospital_id']: r for r in rows}
row = by_id.get(str(entry.get('hospital_id', '')))
if not row:
    fail(f"Unknown hospital_id {entry.get('hospital_id')!r}.")
fields = entry.get('fields') or {}
evidence = str(entry.get('evidence') or '').strip()
sources = [str(s).strip() for s in (entry.get('sources') or []) if str(s).strip()]
if not fields:
    fail('No fields were entered.')
if len(evidence) < 10:
    fail('Please include evidence (where you found each value, ideally a quote from the document).')

errors, new = [], {}
for c, v in fields.items():
    c = str(c).upper()
    if c not in GRADED:
        errors.append(f'{c}: not a graded field'); continue
    if c == 'AI':
        try:
            pctv = float(v)
        except (TypeError, ValueError):
            errors.append(f'AI: max FPL must be a number like 400 (got {v!r})'); continue
        if not 0 < pctv <= 2000:
            errors.append(f'AI: {pctv} is not a plausible FPL percent'); continue
        new['AI'] = (f'{pctv / 100:g}' if pctv >= 400 else 'no', pctv)
    else:
        vv = norm(v)
        if vv not in ('yes', 'no'):
            errors.append(f'{c}: must be yes or no (got {v!r})'); continue
        new[c] = (vv, None)
if errors:
    fail('Some values could not be accepted:\n- ' + '\n- '.join(errors))

run_id = f'{a.date}-manual-issue{a.issue}'
note = f'Manual entry by @{a.author} (issue #{a.issue}): {evidence}'[:600]
before_grade = row['O']
changes, log = [], []


def fmt_ai(v):
    try:
        return f'{int(round(float(v) * 100))}%'
    except (TypeError, ValueError):
        return norm(v) or '(blank)'


for c, (nv, pctv) in new.items():
    old = norm(row[c])
    if old == nv:
        continue
    o = fmt_ai(old) if c == 'AI' else (old or '(blank)')
    n_ = ((f'no ({int(pctv)}%)' if nv == 'no' else fmt_ai(nv)) if c == 'AI' else nv)
    changes.append(f'{c} {COLUMNS[c]}: {o} -> {n_}')
    log.append([a.date, run_id, row['hospital_id'], row['A'], row['M'], c, COLUMNS[c], o, n_, note[:300]])
    row[c] = nv

if not changes:
    fail('Nothing changed: every value entered matches what is already recorded.')

unver = [u for u in row['AS'].split(', ') if u and u != 'None' and u not in new]
row['AS'] = ', '.join(sorted(set(unver), key=ci)) or 'None'
row['AV'] = 'Final' if row['AS'] == 'None' else 'Provisional - blank cells not counted'
row['AT'] = note
row['AU'] = '\n'.join([x for x in (row['AU'] or '').split('\n') if x] + [f'{s} (manual entry, issue #{a.issue})' for s in sources])
g, auto_f, n = grade(row)
row['O'], row['P'], row['Q'] = g, str(auto_f).upper(), str(n)
row['AR'] = before_grade
row['AW'] = '; '.join(changes)
row['AX'] = str(len(changes))
row['AY'] = 'No change' if g == before_grade else f'{before_grade} -> {g}'
row['AZ'] = a.date

write_tracker(rows)
with CHANGELOG.open('a', newline='', encoding='utf-8') as f:
    csv.writer(f, lineterminator='\n').writerows(log)
(AUDIT / 'runs').mkdir(exist_ok=True)
(AUDIT / 'runs' / f'{run_id}.json').write_text(json.dumps(
    {'author': a.author, 'issue': a.issue, 'date': a.date, 'entry': entry, 'changes': changes}, indent=1))

head = f"Manual entry: {row['A']} ({len(changes)} field{'s' if len(changes) != 1 else ''}, issue #{a.issue})"
body_md = (f"Entered by @{a.author}. Grade: {row['AY']}.\n\n" + '\n'.join(f'- {x}' for x in changes) +
           f"\n\nEvidence: {evidence}\n" + (('\nSources:\n' + '\n'.join(f'- {s}' for s in sources) + '\n') if sources else '') +
           f"\nCloses #{a.issue}\n")
(AUDIT / 'work').mkdir(exist_ok=True)
(AUDIT / 'work' / 'summary.md').write_text(f'{head}\n\n{body_md}')
(AUDIT / 'work' / 'comment.md').write_text(
    f"✅ Applied to the tracker.\n\n**{row['A']}** — grade {row['AY']}\n\n" + '\n'.join(f'- {x}' for x in changes) +
    f"\n\nRemaining unverified fields: {row['AS']}. The dashboard and spreadsheet update within a few minutes.")
print(head); print(body_md)
