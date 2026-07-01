# -*- coding: utf-8 -*-
"""One-time campaign launch: mass-create enrollment.journey records for all
eligible families and import their students from Akdemia.

ELIGIBILITY:
  - Universe        : the Akdemia continuity roster (every guardian cédula),
                      NOT the Representante tag — tag coverage is incomplete
                      (~97 of ~172 continuity families carry it).
  - Resolve each guardian cédula -> ANY Odoo partner by normalized VAT
                      (tag-independent).
  - Must have >= 1 ENROLLING student ("5to. Año" graduating excluded;
                      "5to. Grado" primaria CONTINUES and is kept).
  - Guardians whose ONLY students are "5to. Año" are skipped.
  - Guardian cédulas with no matching Odoo partner are FLAGGED for partner
                      creation (listed in the report) — the run never crashes.

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
# REP_TAG removed: eligibility no longer gates on the Representante tag (tag
# coverage is incomplete — ~70 continuity families lack it). The universe is
# now the Akdemia roster, resolved to partners by VAT (tag-independent).

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


# 2) Universe — Akdemia continuity roster (NOT the Representante tag) -----------
# Pre-index every partner that has a VAT so a guardian cédula resolves O(1),
# tag-independent. Duplicate partners per VAT are broken by the same billing
# rule used downstream (posted invoices -> customer_rank -> lowest id).
vat_to_partner = {}
for _p in env['res.partner'].search([('vat', '!=', False)]):
    _k = _normalize_cedula(_p.vat)
    if _k:
        vat_to_partner.setdefault(_k, []).append(_p)


def _resolve_partner(cedula):
    """Pick one Odoo partner for a guardian cédula (co-parent billing dedup runs
    later in Pass 2). On duplicate partners prefer most posted invoices ->
    customer_rank -> lowest id; return None when no partner matches."""
    cands = vat_to_partner.get(cedula, [])
    if not cands:
        return None
    return max(cands, key=lambda p: (_posted_invoices(p), p.customer_rank, -p.id))

stats = dict(akdemia_guardians=len(index), no_partner_match=0,
             graduating_only=0, eligible_partners=0, co_parent_skipped=0,
             already_journey=0, created=0, created_no_email=0,
             import_failed=0, mixed_household=0)
samples = dict(no_partner_match=[], graduating_only=[], created=[])

# ---- Pass 1: walk the Akdemia roster, resolve to partners, collect claims ----
# elig[pid] = {'p','name','rank','inv','email','skeys':[...]}
elig = {}
student_claims = {}        # student_key -> [pid, ...]
unmatched = {}             # guardian cédula -> [enrolling names] (needs partner)
for cedula, kids in index.items():
    enrolling = [k for k in kids if not _is_graduating_grade(k.get('grade'))]
    if not enrolling:
        stats['graduating_only'] += 1   # this guardian's kids are all 5to. Año
        if len(samples['graduating_only']) < 10:
            samples['graduating_only'].append(
                (cedula, [k.get('grade') for k in kids]))
        continue
    p = _resolve_partner(cedula)
    if p is None:                       # FLAG for partner creation, do not crash
        stats['no_partner_match'] += 1
        unmatched[cedula] = [k.get('name') for k in enrolling]
        if len(samples['no_partner_match']) < 20:
            samples['no_partner_match'].append((cedula, unmatched[cedula]))
        continue
    skeys = [_student_key(k) for k in enrolling]
    if p.id in elig:                    # partner reached via 2+ guardian cédulas
        for sk in skeys:
            if sk not in elig[p.id]['skeys']:
                elig[p.id]['skeys'].append(sk)
    else:
        elig[p.id] = dict(p=p, name=p.name, rank=p.customer_rank,
                          inv=_posted_invoices(p), email=bool(p.email),
                          skeys=list(skeys))
    for sk in skeys:                    # shared kids -> claim under each co-parent
        pids = student_claims.setdefault(sk, [])
        if p.id not in pids:
            pids.append(p.id)
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

# Genuinely orphaned continuity students: claimed by NO matched guardian.
# NB: stats['no_partner_match'] counts guardian *cédulas* without a partner, but
# most of those are co-parents whose child is already covered via the OTHER
# parent — so it over-states the gap. The real actionable gap is the set of
# enrolling students that no matched guardian claimed.
all_enroll = {}            # student_key -> name (every continuity student)
for _ced, _kids in index.items():
    for _k in _kids:
        if not _is_graduating_grade(_k.get('grade')):
            all_enroll[_student_key(_k)] = _k.get('name')
orphan_students = {sk: nm for sk, nm in all_enroll.items() if sk not in student_claims}
stats['continuity_students'] = len(all_enroll)
stats['orphan_students'] = len(orphan_students)

# 4) Report --------------------------------------------------------------------
print('\n===== MODE: %s =====' % ('LIVE (committing)' if LIVE else 'DRY-RUN'))
for k in ('akdemia_guardians', 'continuity_students', 'graduating_only',
          'eligible_partners', 'co_parent_skipped', 'mixed_household',
          'already_journey', 'created', 'created_no_email', 'import_failed',
          'orphan_students'):
    print('  %-22s %s' % (k, stats[k]))
print('  %-22s %s  (guardian cédulas w/o a partner; co-parents inflate this)'
      % ('no_partner_match', stats['no_partner_match']))
print('  %-22s %s' % ('shared-student households', len(dup_students)))

print('\n--- sample CREATED (billing parent, #students won, has_email):')
for s in samples['created']:
    print('   ', s)
print('--- sample GRADUATING-ONLY (skipped — guardian cédula : grades):')
for s in samples['graduating_only']:
    print('   ', s)
print('--- ORPHAN students (no matched guardian → family truly needs a partner):')
for sk, nm in list(orphan_students.items())[:30]:
    print('    %s  (key %s)' % (nm, sk))
print('  >> %d continuity student(s) are not covered by any created journey.'
      % stats['orphan_students'])
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
