# -*- coding: utf-8 -*-
"""S0 (Step 0) enrollment blast — batched runner.

Sends the continuity-survey invitation to every PENDING, not-yet-blasted
enrollment.journey, in batches, committing after each batch so the run is
resumable and never double-sends (blast_sent_date is stamped per record).

Channel is decided per family by action_send_blast_email():
  - has email  -> S0 email  (From/Reply-To = inscripcion@, CC = enrollment.blast_cc)
  - no email   -> WhatsApp fallback (_send_wa_s0, canonical ai.agent WA service)

SENDER (from ir.config_parameter, already wired in prod):
  enrollment.notify_from / reply_to / contact / blast_cc

SAFETY:
  - DRY-RUN by default. Pass env LIVE=1 to actually send + commit.
  - Idempotent/resumable: only PENDING journeys with blast_sent_date unset are
    picked up; re-running continues where it stopped.
  - BATCH   (default 10)   journeys per batch
  - PAUSE   (default 30)   seconds slept between batches (SMTP/WA courtesy)
  - MAX_BATCHES (default 0=all)  stop after N batches this run (controlled waves)

RUN from the PROD host, DETACHED in the background, against DB_UEIPAB:
  # dry (plan only):
  docker exec -i ueipab17 odoo shell -d DB_UEIPAB --no-http \
    < /tmp/enrollment_s0_blast.py
  # LIVE, background, logged:
  nohup docker exec -e LIVE=1 -e BATCH=10 -e PAUSE=30 -i ueipab17 \
    odoo shell -d DB_UEIPAB --no-http < /tmp/enrollment_s0_blast.py \
    > /var/log/s0_blast_$(date +%Y%m%d_%H%M%S).log 2>&1 &
"""
import os
import time

LIVE = os.environ.get('LIVE') == '1'
BATCH = int(os.environ.get('BATCH', '10'))
PAUSE = int(os.environ.get('PAUSE', '30'))
MAX_BATCHES = int(os.environ.get('MAX_BATCHES', '0'))   # 0 = all

env = self.env  # noqa: F821 — provided by odoo shell
J = env['enrollment.journey']

# Universe: pending continuity families that have NOT been blasted yet.
recs = J.search([
    ('continuation_status', '=', 'pending'),
    ('blast_sent_date', '=', False),
    ('active', '=', True),
], order='id')

email_n = sum(1 for r in recs if r.partner_id.email)
wa_n = len(recs) - email_n
print('DB=%s | pending unsent journeys: %d  (email: %d, WA-fallback: %d)'
      % (env.cr.dbname, len(recs), email_n, wa_n))

batches = [recs[i:i + BATCH] for i in range(0, len(recs), BATCH)]
print('batch size %d -> %d batch(es); PAUSE=%ss; MAX_BATCHES=%s; MODE=%s'
      % (BATCH, len(batches), PAUSE, MAX_BATCHES or 'all',
         'LIVE (sending)' if LIVE else 'DRY-RUN'))

sent_email = sent_wa = errors = 0
for bi, batch in enumerate(batches, 1):
    if MAX_BATCHES and bi > MAX_BATCHES:
        print('reached MAX_BATCHES=%d — stopping (remaining will send next run).'
              % MAX_BATCHES)
        break
    if not LIVE:
        print('  [DRY] batch %d/%d (%d):' % (bi, len(batches), len(batch)))
        for r in batch:
            ch = 'EMAIL' if r.partner_id.email else 'WA-fallback'
            print('        %-32s %s' % (r.partner_id.name or '?', ch))
        continue
    res = batch.action_send_blast_email()
    env.cr.commit()
    # Prod's method_direct_trigger enqueues but doesn't always flush synchronously
    # -> send this batch's queued S0 emails now so delivery is deterministic.
    outq = env['mail.mail'].search([
        ('subject', 'ilike', 'Inscripción 2026-2027'), ('state', '=', 'outgoing')])
    if outq:
        outq.send(raise_exception=False)
        env.cr.commit()
    msg = res.get('params', {}).get('message', '')
    print('  batch %d/%d (%d) -> %s | flushed %d mail(s)'
          % (bi, len(batches), len(batch), msg, len(outq)))
    if bi < len(batches) and (not MAX_BATCHES or bi < MAX_BATCHES) and PAUSE:
        time.sleep(PAUSE)

if not LIVE:
    print('\nDRY-RUN complete — nothing sent. Set LIVE=1 to send.')
else:
    print('\nLIVE run complete. Re-run to continue any remaining pending journeys.')
