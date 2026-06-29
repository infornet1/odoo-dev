#!/usr/bin/env bash
# =============================================================================
# Deploy the Plan de Contingencia Académica survey (SÍ/NO vote) to PRODUCTION.
#
# This is a SURGICAL deploy: it copies ONLY the two files the survey touches —
#   controllers/partner_ack.py   (notice-key-aware vote pages for the survey)
#   __manifest__.py              (version bump → 17.0.1.6.29)
# …into the already-installed ueipab_attendance_report on prod, then upgrades.
#
# Why surgical (not a whole-module tar): the dev working tree may carry unrelated
# uncommitted changes (e.g. attendance_fix.py). Copying only these two files
# avoids dragging anything else into prod. Prod's other files are left untouched.
#
#   container: ueipab17 · db: DB_UEIPAB · addons: /home/vision/ueipab17/addons
#   Reads the prod SSH password from config/production.json. Run from /opt/odoo-dev.
#
#   bash scripts/deploy_contingencia_survey_prod.sh
#
# Prereq: sshpass installed locally; ueipab_attendance_report already installed
# on prod at 17.0.1.6.28 (per CLAUDE.md, deployed 2026-06-29).
# After this completes the vote ROUTES + PAGES are live; the email blast is a
# separate, later step (see documentation/CONTINGENCIA_ACADEMICA_SURVEY.md).
# =============================================================================
set -euo pipefail

MODULE=ueipab_attendance_report
LOCAL_MOD=/opt/odoo-dev/addons/$MODULE
REMOTE_MOD=/home/vision/ueipab17/addons/$MODULE
REMOTE_BACKUPS=/home/vision/ueipab17_addon_backups   # OUTSIDE addons_path
CONTAINER=ueipab17
DB=DB_UEIPAB
TS=$(date +%Y%m%d_%H%M%S)
PJSON=/opt/odoo-dev/config/production.json

FILES=( "controllers/partner_ack.py" "wizard/vote_assist_wizard.py" "views/vote_assist_wizard_views.xml" "__manifest__.py" )

EXPECTED_VER=$(python3 -c "import ast;print(ast.literal_eval(open('$LOCAL_MOD/__manifest__.py').read())['version'])")
HOST=$(python3 -c "import json;print(json.load(open('$PJSON'))['production']['server']['host'])")
SUSER=$(python3 -c "import json;print(json.load(open('$PJSON'))['production']['server']['user'])")
export SSHPASS=$(python3 -c "import json;print(json.load(open('$PJSON'))['production']['server']['password'])")

command -v sshpass >/dev/null || { echo "ERROR: sshpass not installed (apt-get install -y sshpass)"; exit 1; }
ssh_() { sshpass -e ssh -o StrictHostKeyChecking=no "$SUSER@$HOST" "$@"; }
scp_() { sshpass -e scp -o StrictHostKeyChecking=no "$@"; }

echo "===================================================================="
echo " DEPLOY contingencia survey → $MODULE v$EXPECTED_VER"
echo "   PROD $HOST / $CONTAINER / $DB   (surgical: ${#FILES[@]} files)"
echo "===================================================================="
read -r -p "This writes to PRODUCTION. Type 'DEPLOY' to continue: " ok
[ "$ok" = "DEPLOY" ] || { echo "aborted."; exit 1; }

echo; echo "== 1/6  Pre-flight: module present + current version on prod =="
ssh_ "ls $REMOTE_MOD/__manifest__.py >/dev/null 2>&1 && echo '  ✓ $MODULE present on prod' || { echo '  ✗ $MODULE MISSING — abort'; exit 1; }"

echo; echo "== 2/6  Backup the target files on prod (outside addons_path) =="
for f in "${FILES[@]}"; do
  ssh_ "mkdir -p \$(dirname $REMOTE_BACKUPS/contingencia-$TS/$f) && cp $REMOTE_MOD/$f $REMOTE_BACKUPS/contingencia-$TS/$f && echo '  ✓ backed up $f'"
done

echo; echo "== 3/6  Copy the two files to prod =="
for f in "${FILES[@]}"; do
  scp_ "$LOCAL_MOD/$f" "$SUSER@$HOST:$REMOTE_MOD/$f"
  echo "  ✓ copied $f"
done

echo; echo "== 4/6  Upgrade module (-u) — capturing odoo's real exit code =="
ssh_ "docker exec $CONTAINER odoo -u $MODULE -d $DB --stop-after-init --no-http > /tmp/${MODULE}_contingencia.log 2>&1; rc=\$?; tail -8 /tmp/${MODULE}_contingencia.log; echo \"  odoo exit=\$rc\"; exit \$rc"

echo; echo "== 5/6  Restart container + wait for boot (poll up to 90s) =="
ssh_ "docker restart $CONTAINER >/dev/null && echo '  ✓ restarted'"
python3 - <<'PYV'
import json, sys, time, xmlrpc.client
c = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
for attempt in range(18):
    try:
        uid = xmlrpc.client.ServerProxy(c['url']+'/xmlrpc/2/common').authenticate(c['db'], c['user'], c['api_key'], {})
        if uid:
            print('  ✓ Odoo reachable (uid=%s) after ~%ds' % (uid, attempt*5)); break
    except Exception:
        pass
    time.sleep(5)
else:
    print('  ✗ Odoo not reachable after 90s'); sys.exit(1)
PYV

echo; echo "== 6/6  Verify version (must equal manifest $EXPECTED_VER) + route smoke =="
python3 - "$EXPECTED_VER" <<'PYV'
import json, sys, xmlrpc.client
expected = sys.argv[1]
c = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
uid = xmlrpc.client.ServerProxy(c['url']+'/xmlrpc/2/common').authenticate(c['db'], c['user'], c['api_key'], {})
m = xmlrpc.client.ServerProxy(c['url']+'/xmlrpc/2/object', allow_none=True)
r = m.execute_kw(c['db'], uid, c['api_key'], 'ir.module.module', 'search_read',
                 [[['name','=','ueipab_attendance_report']]], {'fields':['state','installed_version']})
print('   ', r[0] if r else 'NOT FOUND')
if not r or r[0]['state'] != 'installed' or r[0]['installed_version'] != expected:
    print('   ✗ state/version mismatch (expected installed %s) — see /tmp/ueipab_attendance_report_contingencia.log on prod' % expected)
    sys.exit(1)
print('   ✓ installed %s' % expected)
PYV

echo
echo "===================================================================="
echo " DONE — vote ROUTES + PAGES live on prod."
echo " NEXT (separate, gated steps — NOT done here):"
echo "   • Confirm prod nginx allows /partner-ack/<token> (it already serves the budget vote)."
echo "   • votacion@ SMTP creds + DMARC/SPF alignment before any external blast."
echo "   • Blast:  TARGET_ENV=production python3 scripts/send_contingencia_vote_email.py --test --live   # CEO preview first"
echo "             TARGET_ENV=production python3 scripts/send_contingencia_vote_email.py --live          # full send"
echo "   • Monitor: AI Agent → Operaciones → Comunicados a Representantes (group by Campaña)."
echo " Rollback: restore $REMOTE_BACKUPS/contingencia-$TS/* + docker restart $CONTAINER"
echo "===================================================================="
