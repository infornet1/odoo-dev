# FreeScout — Restrict Access to Venezuela IP Ranges

**Date:** 2026-06-27
**Status:** Researched — not yet implemented (awaiting decision on enforcement layer + admin exception IPs)
**Requested by:** Gustavo Perdomo
**Related:** [FINANZAS_EMAIL_SPOOFING_FIX.md](FINANZAS_EMAIL_SPOOFING_FIX.md)

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

- [ ] Decide enforcement layer (module-only vs nginx/ipset whole-site).
- [ ] Collect admin/office exception IPs (incl. any Starlink/VPN egress IPs).
- [ ] Implement chosen layer + cron refresh of `ve-aggregated.zone`.
- [ ] Verify end-user portal access expectations (VE-only customers?).
- [ ] Test from a non-VE IP to confirm 403, and from a VE/exception IP to confirm pass.
