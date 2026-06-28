#!/usr/bin/env bash
#
# freescout_ve_allowlist.sh
# Builds the FreeScout ExtraSecurity IP allowlist (Venezuela + mobile carriers +
# fixed admin pins), writes it to .env (base64) and rebuilds the config cache.
# Used both for the initial deploy and the weekly cron refresh.
#
# Enforcement is the ExtraSecurity module only (EXTRASECURITY_IPS / _ENABLED).
#
set -euo pipefail

ENV_FILE="/var/www/freescout/.env"
APP_DIR="/var/www/freescout"
VE_URL="https://www.ipdeny.com/ipblocks/data/aggregated/ve-aggregated.zone"
CARRIER_ASNS="6306 264731 21826 27889"   # Movistar, Digitel, Digitel(Telemic), Movilnet
MIN_ENTRIES=180                          # sanity floor; abort if fewer (network failure)

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# --- fixed pins (always allowed, regardless of geo) ---
cat > "$TMP/pins.txt" <<'PINS'
127.0.0.0/8
64.23.157.121
146.190.55.97
200.82.130.93
186.14.93.234
190.121.236.34
38.84.58.0/24
23.146.236.245
38.188.238.102
PINS

# --- 1) Venezuela country list (critical: abort on failure) ---
if ! curl -fsS --retry 3 -m 60 "$VE_URL" -o "$TMP/ve.zone"; then
  echo "ERROR: failed to download VE zone ($VE_URL); aborting (allowlist unchanged)." >&2
  exit 1
fi

# --- 2) Mobile carrier ASN prefixes (best-effort; skip a carrier on failure) ---
: > "$TMP/carriers.txt"
for asn in $CARRIER_ASNS; do
  if curl -fsS --retry 2 -m 45 "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS${asn}" -o "$TMP/as.json"; then
    python3 -c "import sys,json;[print(p['prefix']) for p in json.load(open('$TMP/as.json'))['data']['prefixes'] if ':' not in p['prefix']]" >> "$TMP/carriers.txt" || true
  else
    echo "WARN: carrier AS${asn} fetch failed; skipping it this run." >&2
  fi
done

# --- 3) merge + collapse (aggregate; keeps coverage, drops redundant subnets) ---
cat "$TMP/ve.zone" "$TMP/carriers.txt" "$TMP/pins.txt" \
  | tr -d '\r' | sed 's/[[:space:]]//g' | grep -E '[0-9]' > "$TMP/raw.txt"

python3 - "$TMP/raw.txt" "$TMP/list.txt" <<'PY'
import sys,ipaddress
raw,out=sys.argv[1],sys.argv[2]
nets=[]
for l in open(raw):
    l=l.strip()
    if not l: continue
    try: nets.append(ipaddress.ip_network(l, strict=False))   # bare IP -> /32
    except ValueError: pass
nets=[n for n in nets if n.version==4]   # module is IPv4-only (ip2long)
collapsed=sorted(ipaddress.collapse_addresses(nets), key=lambda n:(int(n.network_address),n.prefixlen))
with open(out,'w') as f:
    for n in collapsed: f.write(str(n)+"\n")
print(len(collapsed))
PY

COUNT="$(grep -c . "$TMP/list.txt")"
if [ "$COUNT" -lt "$MIN_ENTRIES" ]; then
  echo "ERROR: list too small ($COUNT < $MIN_ENTRIES); aborting (allowlist unchanged)." >&2
  exit 1
fi

# --- 4) base64 (single line, no wrapping) ---
B64="$(base64 -w0 "$TMP/list.txt")"

# --- 5) update .env (timestamped backup, then set the two keys) ---
cp -a "$ENV_FILE" "${ENV_FILE}.bak-$(date +%Y%m%d_%H%M%S)"
# keep only the 10 most recent backups
ls -1t "${ENV_FILE}".bak-* 2>/dev/null | tail -n +11 | xargs -r rm -f
python3 - "$ENV_FILE" "$B64" <<'PY'
import sys,re
env,b64=sys.argv[1],sys.argv[2]
s=open(env).read()
def setvar(s,k,v):
    pat=re.compile(rf'^{re.escape(k)}=.*$', re.M)
    return pat.sub(f'{k}={v}', s) if pat.search(s) else s.rstrip('\n')+f'\n{k}={v}\n'
s=setvar(s,'EXTRASECURITY_IPS', '"'+b64+'"')
s=setvar(s,'EXTRASECURITY_IPS_ENABLED','true')
open(env,'w').write(s)
PY

# --- 6) rebuild config cache ---
cd "$APP_DIR"
php artisan config:cache >/dev/null

echo "OK $(date '+%Y-%m-%d %H:%M:%S'): FreeScout VE allowlist updated — ${COUNT} CIDR entries, ENABLED=true."
