# -*- coding: utf-8 -*-
"""One-time campaign launch: mass-create enrollment.journey records for all
eligible families and import their students from Akdemia.

ELIGIBILITY:
  - Universe        : res.partner tagged "Representante" (category id 25)
  - Must have a VAT  (cédula) that matches an Akdemia guardian
  - Must have >= 1 ENROLLING student (5° Año / graduating students excluded)
  - Families whose ONLY students are graduating (5° Año) are skipped

SAFETY:
  - DRY-RUN by default. Pass env LIVE=1 to actually create + import + commit.
  - Idempotent: partners that already have a journey are skipped.

RUN (dry):
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < scripts/enrollment_journey_mass_create.py

RUN (live):
  docker exec -e LIVE=1 -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < scripts/enrollment_journey_mass_create.py
"""
import json
import os

from odoo.addons.ueipab_enrollment_journey.models.enrollment_journey import (
    _normalize_cedula, _is_graduating_grade,
)

LIVE = os.environ.get('LIVE') == '1'
REP_TAG = 25  # "Representante"

env = self.env  # noqa: F821 — provided by odoo shell
J = env['enrollment.journey']

# 1) Akdemia ground truth ------------------------------------------------------
entries = J._akdemia_fetch_students()
index = J._akdemia_index_by_guardian(entries)
print('Akdemia: %d student entries, %d guardian keys' % (len(entries), len(index)))

# In LIVE mode publish the index to the cache so per-partner import reads the
# cache (one parse) instead of hitting the network ~200 times.
if LIVE:
    env['ir.config_parameter'].sudo().set_param(
        'akdemia.students_json', json.dumps(index))
    print('Published akdemia.students_json cache for fast import.')

# Posted customer-invoice count — proxy for "billing parent" (the same parent
# the curated Customers-tab Registration VAT points to: verified 2026-06-26 that
# max(posted invoices) → customer_rank → lowest id reproduces the sheet's
# one-valid-VAT-per-family selection in every shared-household case).
def _posted_invoices(partner):
    return env['account.move'].search_count([
        ('partner_id', '=', partner.id),
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted')])


def _student_key(kid):
    return _normalize_cedula(kid.get('cedula')) or (kid.get('name') or '').strip().upper()


# 2) Universe ------------------------------------------------------------------
universe = env['res.partner'].search([('category_id', 'in', [REP_TAG])])

stats = dict(universe=len(universe), missing_vat=0, no_akdemia_match=0,
             graduating_only=0, eligible_partners=0, co_parent_skipped=0,
             already_journey=0, created=0, created_no_email=0,
             import_failed=0, mixed_household=0)
samples = dict(no_akdemia_match=[], graduating_only=[], created=[])

# ---- Pass 1: collect eligible partners + per-student claims ------------------
# elig[pid] = {'p', 'name', 'rank', 'inv', 'email', 'students':[(skey, kid)...]}
elig = {}
student_claims = {}   # student_key -> [pid, ...]
for p in universe:
    key = _normalize_cedula(p.vat)
    if not key:
        stats['missing_vat'] += 1
        continue
    kids = index.get(key)
    if not kids:
        stats['no_akdemia_match'] += 1
        if len(samples['no_akdemia_match']) < 10:
            samples['no_akdemia_match'].append((p.id, p.name, p.vat))
        continue
    enrolling = [k for k in kids if not _is_graduating_grade(k.get('grade'))]
    if not enrolling:
        stats['graduating_only'] += 1
        if len(samples['graduating_only']) < 10:
            samples['graduating_only'].append(
                (p.name, [k.get('grade') for k in kids]))
        continue
    skeys = [_student_key(k) for k in enrolling]
    elig[p.id] = dict(p=p, name=p.name, rank=p.customer_rank,
                      inv=_posted_invoices(p), email=bool(p.email),
                      skeys=skeys)
    for sk in skeys:
        student_claims.setdefault(sk, []).append(p.id)
stats['eligible_partners'] = len(elig)

# ---- Pass 2: assign each student to its billing parent (dedup co-parents) ----
def _billing_rank(pid):
    e = elig[pid]
    return (e['inv'], e['rank'], -pid)   # higher invoices/rank wins; id tiebreak

winner = {sk: max(pids, key=_billing_rank) for sk, pids in student_claims.items()}
won = {pid: [sk for sk in e['skeys'] if winner[sk] == pid] for pid, e in elig.items()}

# ---- Pass 3: create one journey per partner that wins >= 1 student -----------
for pid, e in elig.items():
    if not won[pid]:
        stats['co_parent_skipped'] += 1          # pure co-parent → no journey
        continue
    if len(won[pid]) != len(e['skeys']):
        stats['mixed_household'] += 1            # wins some, shares others (rare)
        print('  ⚠ MIXED household: %s wins %d/%d students (shared kid will also '
              'import here — manual trim)' % (e['name'], len(won[pid]), len(e['skeys'])))
    if J.search([('partner_id', '=', pid)]):
        stats['already_journey'] += 1
        continue
    if not e['email']:
        stats['created_no_email'] += 1
    if LIVE:
        j = J.create({'partner_id': pid})
        try:
            j.with_context(use_cache=True).action_import_students()
        except Exception as exc:  # noqa: BLE001
            stats['import_failed'] += 1
            print('  import FAILED %s: %s' % (e['name'], exc))
    stats['created'] += 1
    if len(samples['created']) < 10:
        samples['created'].append((e['name'], len(won[pid]), e['email']))

dup_students = {sk: pids for sk, pids in student_claims.items() if len(set(pids)) > 1}

# 4) Report --------------------------------------------------------------------
print('\n===== MODE: %s =====' % ('LIVE (committing)' if LIVE else 'DRY-RUN'))
for k in ('universe', 'missing_vat', 'no_akdemia_match', 'graduating_only',
          'eligible_partners', 'co_parent_skipped', 'mixed_household',
          'already_journey', 'created', 'created_no_email', 'import_failed'):
    print('  %-22s %s' % (k, stats[k]))
print('  %-22s %s' % ('shared-student households', len(dup_students)))

print('\n--- sample CREATED (billing parent, #students won, has_email):')
for s in samples['created']:
    print('   ', s)
print('--- sample GRADUATING-ONLY (skipped):')
for s in samples['graduating_only']:
    print('   ', s)
print('--- shared-student households -> chosen billing parent:')
for sk, pids in list(dup_students.items())[:15]:
    w = winner[sk]
    print('    student %s : %s  ->  WINNER %s (inv=%d rank=%d)' % (
        sk, [elig[i]['name'] for i in pids], elig[w]['name'],
        elig[w]['inv'], elig[w]['rank']))

if LIVE:
    env.cr.commit()
    print('\nCOMMITTED.')
else:
    env.cr.rollback()
    print('\nDRY-RUN complete — nothing persisted.')
