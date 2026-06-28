# FreeScout — Restrict Access to Venezuela IP Ranges

**Date:** 2026-06-27 (research) · **Implemented:** 2026-06-28
**Status:** ✅ DEPLOYED — module-only enforcement, live on production
**Requested by:** Gustavo Perdomo
**Related:** [FINANZAS_EMAIL_SPOOFING_FIX.md](FINANZAS_EMAIL_SPOOFING_FIX.md) · [FREESCOUT_TURNSTILE_LOGIN_CAPTCHA.md](FREESCOUT_TURNSTILE_LOGIN_CAPTCHA.md)

> **See the [Implementation (2026-06-28)](#implementation-2026-06-28) section at the bottom for what was actually deployed.** The research/best-practices below is retained for context; the final decision was **module-only** enforcement (not nginx/ipset).

---

## Goal

Restrict access to the FreeScout help desk (`freescout.ueipab.edu.ve`) so that only
clients connecting from **known Venezuela IP ranges** are allowed, as an
attack-surface-reduction measure against foreign brute-force and scanner traffic.

The user installed the official FreeScout **Extra Security** module
(`Modules/ExtraSecurity/`, v1.0.22) which offers an "restrict user access by IP
addresses" feature, and asked whether it can be driven via API and what the best
practice is.

---

## Findings — the Extra Security module

| Question | Answer |
|----------|--------|
| Can it be configured via the FreeScout REST API? | **No.** The module exposes only two `web` routes (`get-ip`, `pow-challenge`). The REST API (ApiWebhooks module) has no settings/config endpoint at all. |
| Does its IP allowlist protect the REST API? | **No.** `checkIp()` is only hooked into `middleware.web.custom_handle` and `auth_middleware.handle` (authenticated web/admin routes). API routes use `bindings` + `ApiAuth` middleware and bypass the check. |
| Does it support IPv6? | **No.** `isIpInRange()` uses `ip2long()` — IPv4 only. |
| Lock-out safety? | Yes — on save it auto-injects the admin's current IP into the allowlist. |

Configuration is therefore only possible via the admin UI (Settings → Extra
Security) or `.env` (`EXTRASECURITY_IPS_ENABLED`, `EXTRASECURITY_IPS`). As of this
writing the feature is **OFF** (`EXTRASECURITY_IPS_ENABLED` empty). Turnstile
(checkbox) is configured for the main login but no keys are set yet.

---

## Environment

- **Web server:** nginx (active; Apache inactive). Site: `freescout.ueipab.edu.ve`.
- **No Cloudflare proxy** in front (DNS = DigitalOcean) → nginx receives the real
  client IP directly, so geo-filtering at nginx is reliable.
- **Tooling available:** `ipset`, `iptables`, `ufw` all installed.
- **Server IP:** `64.23.157.121` (DigitalOcean droplet — Odoo + FreeScout).
- **Email is unaffected** by any web geo-block: mailboxes pull/send via Google
  (`smtp.gmail.com`), not via inbound web traffic.

---

## Best practices

1. **Treat geo-allowlisting as attack-surface reduction, not a security barrier.**
   It is bypassable via VPN/proxy and IP-to-country data is never 100% accurate.
   Keep it *on top of* strong auth + reCAPTCHA/Turnstile + patching.

2. **Choose the enforcement layer by scope:**

   | Layer | Covers | Pros | Cons |
   |-------|--------|------|------|
   | Extra Security module | Admin/agent **web login only** | In-app UI; auto-adds current IP (no self-lockout) | **API not protected**, **IPv4 only**, manual upkeep |
   | nginx (`geo` / allow-deny / `ngx_http_geoip2`) | Whole site **incl. API + end-user portal** | Real client IP, 403 before PHP, IPv6-capable | Must carve out exceptions; blunter |
   | Firewall (ipset `hash:net` + iptables/ufw) | All ports/services | Most efficient (~247 CIDRs in one set) | Network-layer only; must not lock out SSH |

   The module's two gaps (API bypass + IPv4-only) mean **nginx or ipset is the
   technically stronger enforcement point** for a true country allowlist.

3. **Use an authoritative, auto-updated CIDR source — never a hardcoded list.**
   Venezuela's RIR is **LACNIC**; allocations change over time. The practical
   refreshed list is **ipdeny.com** — Venezuela is currently **247 aggregated CIDR
   blocks** (`ve-aggregated.zone`), small enough for a single ipset or nginx geo
   file. Automate a weekly/monthly cron refresh + reload (ref:
   `github.com/mkorthof/ipset-country`). IP2Location LITE is an alternative source.

---

## Pitfalls specific to this deployment

- **Starlink / VPN in Venezuela** often geolocate *outside* VE → an admin on
  Starlink/VPN would be locked out. **Reserve permanent exception IPs.**
- **Remote/traveling admins** abroad are blocked unless given an exception or a
  VPN into the droplet.
- **CGNAT** (CANTV / Movistar / Digitel) is fine — those shared ranges live inside
  the VE blocks, so legitimate mobile users still pass.
- **End-user portal** — a whole-site nginx/firewall block also hits the EUP. If any
  customers/staff access from outside VE, prefer the module-only approach (which
  spares the EUP) or add explicit exceptions.
- **SSH lockout** — if using ufw/ipset, allowlist the SSH source IP *first*.

---

## Recommended approach (layered)

1. **Back-office:** enable the Extra Security module IP restriction for agent login
   (lowest lockout risk) + keep Turnstile on.
2. **Real coverage:** add an **nginx geo allowlist** (or ipset `hash:net`) fed by
   ipdeny `ve-aggregated.zone`, with admin exception IPs baked in — this closes the
   module's API + IPv6 blind spots and covers the end-user portal.
3. **Automate** the CIDR refresh via cron so the list never goes stale.

### Sketch — nginx geo allowlist

```nginx
# /etc/nginx/conf.d/ve-allowlist.conf
geo $allowed_country {
    default          0;
    include          /etc/nginx/ve-cidr.conf;   # "<CIDR> 1;" per line, refreshed by cron
    # admin / office exceptions:
    64.23.157.121/32 1;                          # server itself
    # <office-ip>/32  1;
}
```
```nginx
# inside the freescout server { } block
if ($allowed_country = 0) { return 403; }
```

### Sketch — refresh script (cron weekly)

```bash
#!/usr/bin/env bash
set -euo pipefail
curl -fsS https://www.ipdeny.com/ipblocks/data/aggregated/ve-aggregated.zone \
  | awk '{print $1" 1;"}' > /etc/nginx/ve-cidr.conf.new
mv /etc/nginx/ve-cidr.conf.new /etc/nginx/ve-cidr.conf
nginx -t && systemctl reload nginx
```

---

## Sources

- ipdeny.com country CIDR blocks — https://www.ipdeny.com/ipblocks/
- ipset-country auto-update script — https://github.com/mkorthof/ipset-country
- IP2Location LITE (Venezuela ranges) — https://lite.ip2location.com/venezuela-(bolivarian-republic-of)-ip-address-ranges
- Palo Alto: geolocation is a policy tool, not a barrier — https://live.paloaltonetworks.com/t5/community-blogs/geolocation-and-geoblocking/ba-p/315433
- Whitelisting by country with ipset + iptables — https://dev.to/patashev/whitelisting-by-country-region-with-ipset-and-ip-tables-and-bash-automation-p8h

---

## Follow-up actions

- [x] Decide enforcement layer → **module-only** (chosen 2026-06-28).
- [x] Collect admin/office exception IPs (DO firewall + agent login-IP audit).
- [x] Implement + weekly cron refresh.
- [x] Verify EUP access expectations → module-only spares the EUP (left open).
- [x] Test allowed → 200 and non-allowed → 403 (see Verification below).

---

# Implementation (2026-06-28)

**Enforcement: ExtraSecurity module only.** Chosen over nginx/ipset to avoid touching
nginx and to deliberately spare the REST API and end-user portal. Trade-off accepted:
the **REST API is not geo-restricted** (it has its own key auth) and the EUP stays open.

### What was deployed

- `/var/www/freescout/.env`:
  - `EXTRASECURITY_IPS_ENABLED=true`
  - `EXTRASECURITY_IPS="<base64 of the CIDR list>"`
  - Applied with `php artisan config:cache` (config is cached in prod).
- **223 collapsed IPv4 CIDR entries** = ipdeny VE country list **+ mobile-carrier ASN
  prefixes** + fixed pins, deduped/aggregated with `ipaddress.collapse_addresses`.
- IPv6 is moot — `freescout.ueipab.edu.ve` has **no AAAA record**, so the module's
  IPv4-only matcher (`ip2long`) is sufficient.

### Allowlist composition

| Source | Notes |
|--------|-------|
| ipdeny `ve-aggregated.zone` | ~217 Venezuela country CIDR blocks |
| Mobile carrier ASN prefixes | Movistar `AS6306`, Digitel `AS264731` + `AS21826` (Telemic), Movilnet `AS27889` — pulled from RIPEstat. Future-proofs DHCP/CGNAT mobile; all but one block (`38.84.58.0/24`) already inside the country list |
| Fixed pins | `127.0.0.0/8` (loopback/internal HTTP), `64.23.157.121` + `146.190.55.97` (droplets ueipab2/ueipab), `200.82.130.93` (home), `186.14.93.234` (school INTER) + `190.121.236.34` (school Roraima), `38.84.58.0/24` (Digitel non-VE gap), `23.146.236.245` + `38.188.238.102` (lorena.reyes remote US IPs) |

### How exceptions were derived

- **DO Cloud Firewall** (`doctl`, fw `ueipab-fw` on droplets `ueipab` 146.190.55.97 /
  `ueipab2` 64.23.157.121): web `80/443` are open to `0.0.0.0/0`+`::/0` (no network-layer
  geo filter); SSH/FTP are restricted to admin source IPs — used to identify exceptions.
- **Mikrotik routers** (`/var/www/dev/network/network_topology.md`): school egress is
  Router 1 (750Gr3) via ISP1 INTER `186.14.93.234` and ISP2 Roraima `190.121.236.34`;
  Router 2 (HapAC3) egresses through Router 1. Both already inside the VE list; pinned anyway.
- **Agent login-IP audit** — FreeScout logs every login IP in `activity_logs`
  (`log_name=users`, `description=login`, `properties.ip`). Audited 4 agents:
  alejandra.lopez / josefina.rodriguez / jessica.bolivar = 100% VE; lorena.reyes mostly
  VE + 2 stale US IPs (now pinned). *(Useful pattern for future access audits.)*

### Automation

- **Script:** `/opt/odoo-dev/scripts/freescout_ve_allowlist.sh` — builds the list
  (ipdeny + carrier ASNs + pins → collapse → base64), backs up `.env` (keeps last 10),
  writes the two keys, runs `config:cache`. Aborts if the assembled list is `<180`
  entries (network-failure guard). Used for both initial deploy and refresh.
- **Cron:** `/etc/cron.d/freescout-ve-allowlist` — `Sun 04:00` as root →
  `/var/log/freescout-ve-allowlist.log`.

### Verification

| Test | Result |
|------|--------|
| Module matcher (`parseIpList`/`isIpInRange`) — home, school, droplets, carrier sample, lorena pins | ALLOW ✅ |
| Module matcher — `8.8.8.8`, `1.1.1.1`, `198.163.192.180` | BLOCK ✅ |
| Live `GET /login` from allowlisted source | HTTP **200** + Turnstile + password form ✅ |
| Live `GET /login` from non-allowlisted source | HTTP **403** "not allowed" ✅ |

`getClientIp()` = `request()->ip()` (no trusted proxies configured), so X-Forwarded-For
cannot bypass it. Denials are logged to `storage/logs/security.log`.

### Rollback

```bash
# disable: set EXTRASECURITY_IPS_ENABLED=  (empty) in /var/www/freescout/.env, then:
php artisan config:cache
# or restore a backup:
cp /var/www/freescout/.env.bak-<timestamp> /var/www/freescout/.env && php artisan config:cache
```

### Relationship to the existing nginx blocklist

The FreeScout vhost (`/etc/nginx/sites-available/example.com`, served as
`freescout.ueipab.edu.ve`) already carries a **targeted blocklist** from the June 2026
admin-compromise incident:

```nginx
deny 155.117.0.0/16;     # Nigerian ISP — Jun 2026 compromise/spam source
deny 149.22.0.0/16;      # Datacamp VPN — attacker IPs Jun 12–14 2026
deny 185.98.171.0/24;    # same incident
deny 146.70.45.85/32;    # single Proton VPN exit node, Jun 10 2026
```

**Kept on purpose — complementary, not obsolete.** The module allowlist now makes these
redundant *on the back-office* (all four are non-VE → already 403'd), but the nginx denies
are **site-wide** and so remain the only thing blocking those specific ranges on the
**REST API and end-user portal** (which the module does not cover), and they act at the
web-server layer before PHP. The `location ~ /\. { deny all; }` rule (dotfile/.env/.git
protection) is unrelated and must stay.

> If the **API/EUP** ever need full Venezuela restriction too, that must be done at nginx
> (the module cannot) — a separate decision, not a cleanup of the above.
