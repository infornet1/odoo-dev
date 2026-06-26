#!/usr/bin/env bash
# =============================================================================
# Deploy ueipab_enrollment_journey (entire enrollment business process) to PROD
#   container: ueipab17 · db: DB_UEIPAB · addons: /home/vision/ueipab17/addons
# Reads the prod SSH password from config/production.json. Run from /opt/odoo-dev.
#
#   bash scripts/deploy_enrollment_journey_prod.sh -i       # first deploy (install)
#   bash scripts/deploy_enrollment_journey_prod.sh -u       # later upgrades
#
# Prereq: sshpass installed locally. Dependency ueipab_sales already in prod.
# After this completes, run the config+verify step:
#   AKDEMIA_API_KEY='<token>' python3 scripts/prod_post_deploy_enrollment_journey.py --live
# =============================================================================
set -euo pipefail

MODE="${1:-}"
case "$MODE" in
  -i|-u) ;;
  *) echo "Usage: $0 -i|-u   (-i = first install, -u = upgrade). No default — be explicit."; exit 2;;
esac

MODULE=ueipab_enrollment_journey
LOCAL_ADDONS=/opt/odoo-dev/addons
REMOTE_ADDONS=/home/vision/ueipab17/addons
REMOTE_BACKUPS=/home/vision/ueipab17_addon_backups   # OUTSIDE addons_path (no phantom module)
CONTAINER=ueipab17
DB=DB_UEIPAB
TS=$(date +%Y%m%d_%H%M%S)
PJSON=/opt/odoo-dev/config/production.json
TGZ="/tmp/${MODULE}_${TS}.tgz"

EXPECTED_VER=$(python3 -c "import ast;print(ast.literal_eval(open('$LOCAL_ADDONS/$MODULE/__manifest__.py').read())['version'])")
HOST=$(python3 -c "import json;print(json.load(open('$PJSON'))['production']['server']['host'])")
SUSER=$(python3 -c "import json;print(json.load(open('$PJSON'))['production']['server']['user'])")
export SSHPASS=$(python3 -c "import json;print(json.load(open('$PJSON'))['production']['server']['password'])")

command -v sshpass >/dev/null || { echo "ERROR: sshpass not installed (apt-get install -y sshpass)"; exit 1; }
# sshpass -e reads the password from $SSHPASS env — never exposed in the process table.
ssh_() { sshpass -e ssh -o StrictHostKeyChecking=no "$SUSER@$HOST" "$@"; }
scp_() { sshpass -e scp -o StrictHostKeyChecking=no "$@"; }
cleanup() { rm -f "$TGZ"; ssh_ "rm -f /tmp/$(basename "$TGZ")" 2>/dev/null || true; }
trap cleanup EXIT

echo "===================================================================="
echo " DEPLOY $MODULE v$EXPECTED_VER → PROD ($HOST / $CONTAINER / $DB)  mode=$MODE"
echo "===================================================================="
read -r -p "This writes to PRODUCTION. Type 'DEPLOY' to continue: " ok
[ "$ok" = "DEPLOY" ] || { echo "aborted."; exit 1; }

echo; echo "== 1/7  Pre-flight: dependency ueipab_sales present on prod =="
ssh_ "ls $REMOTE_ADDONS | grep -qx ueipab_sales && echo '  ✓ ueipab_sales present' || { echo '  ✗ ueipab_sales MISSING — abort'; exit 1; }"

echo; echo "== 2/7  Backup any existing copy on prod (outside addons_path) =="
ssh_ "mkdir -p $REMOTE_BACKUPS; if [ -d $REMOTE_ADDONS/$MODULE ]; then cp -r $REMOTE_ADDONS/$MODULE $REMOTE_BACKUPS/${MODULE}.bak-$TS && echo '  ✓ backed up → $REMOTE_BACKUPS/${MODULE}.bak-$TS'; else echo '  (fresh install — no prior copy)'; fi"

echo; echo "== 3/7  Package + copy module to prod =="
tar czf "$TGZ" -C "$LOCAL_ADDONS" "$MODULE"
scp_ "$TGZ" "$SUSER@$HOST:/tmp/"
ssh_ "rm -rf $REMOTE_ADDONS/$MODULE && tar xzf /tmp/$(basename "$TGZ") -C $REMOTE_ADDONS && echo '  ✓ extracted to $REMOTE_ADDONS/$MODULE'"

echo; echo "== 4/7  Install/upgrade module ($MODE) — capturing odoo's real exit code =="
# Do NOT pipe to tail in the same shell: a pipe would mask odoo's exit status.
ssh_ "docker exec $CONTAINER odoo $MODE $MODULE -d $DB --stop-after-init --no-http > /tmp/${MODULE}_install.log 2>&1; rc=\$?; tail -8 /tmp/${MODULE}_install.log; echo \"  odoo exit=\$rc\"; exit \$rc"

echo; echo "== 5/7  Restart container =="
ssh_ "docker restart $CONTAINER >/dev/null && echo '  ✓ restarted'"

echo; echo "== 6/7  Wait for boot (poll up to 90s) =="
python3 - "$EXPECTED_VER" <<'PYV'
import json, sys, time, xmlrpc.client
expected = sys.argv[1]
c = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
for attempt in range(18):           # 18 × 5s = 90s
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

echo; echo "== 7/7  Verify state + version (must equal manifest $EXPECTED_VER) =="
python3 - "$EXPECTED_VER" <<'PYV'
import json, sys, xmlrpc.client
expected = sys.argv[1]
c = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
uid = xmlrpc.client.ServerProxy(c['url']+'/xmlrpc/2/common').authenticate(c['db'], c['user'], c['api_key'], {})
m = xmlrpc.client.ServerProxy(c['url']+'/xmlrpc/2/object', allow_none=True)
r = m.execute_kw(c['db'], uid, c['api_key'], 'ir.module.module', 'search_read',
                 [[['name','=','ueipab_enrollment_journey']]], {'fields':['state','installed_version']})
print('   ', r[0] if r else 'NOT FOUND')
if not r or r[0]['state'] != 'installed' or r[0]['installed_version'] != expected:
    print('   ✗ state/version mismatch (expected installed %s) — investigate /tmp/%s_install.log on prod' % (expected, 'ueipab_enrollment_journey'))
    sys.exit(1)
print('   ✓ installed %s' % expected)
PYV

echo
echo "===================================================================="
echo " DONE. Next:"
echo "   AKDEMIA_API_KEY='<token>' python3 scripts/prod_post_deploy_enrollment_journey.py --live"
echo " Rollback: restore $REMOTE_BACKUPS/${MODULE}.bak-$TS (or uninstall) + docker restart $CONTAINER"
echo "===================================================================="
