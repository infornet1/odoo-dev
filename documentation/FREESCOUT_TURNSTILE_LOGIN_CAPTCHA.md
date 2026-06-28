# FreeScout — Cloudflare Turnstile CAPTCHA on Main Login

**Date:** 2026-06-28
**Status:** ✅ Deployed (live on production main login)
**Requested by:** Gustavo Perdomo
**Related:** [FREESCOUT_IP_ALLOWLIST_VENEZUELA.md](FREESCOUT_IP_ALLOWLIST_VENEZUELA.md)

---

## Goal

Add a CAPTCHA to the FreeScout agent/admin **main login form**
(`https://freescout.ueipab.edu.ve/login`) to block automated brute-force and
credential-stuffing attempts, using **Cloudflare Turnstile** via the official
FreeScout **Extra Security** module (`Modules/ExtraSecurity/`).

> Note: the domain is **not** proxied through Cloudflare (DNS is on DigitalOcean).
> Turnstile does not require that — it is a standalone CAPTCHA widget; only a
> site key + secret key are needed, retrieved from the Cloudflare account.

---

## What was done

1. **Created a Turnstile widget** on the Cloudflare account via API
   (`POST /accounts/{account_id}/challenges/widgets`):
   - Account: `perdomo.gustavo@gmail.com` (account id `2a1790164a40eb5f968bd1b7c8d9a876`)
   - Widget name: `FreeScout Main Login`
   - Domain: `freescout.ueipab.edu.ve`
   - Mode: `managed` (shows an interactive checkbox only when needed)
   - **Site key (public):** `0x4AAAAAADsURQLrsIeJlDCP`
   - **Secret key (private):** stored encrypted in `.env` (not reproduced here)

2. **Configured the Extra Security module** (settings persist to `.env`):

   | `.env` key | Value |
   |------------|-------|
   | `EXTRASECURITY_RECAPTCHA_MAIN_ENABLED` | `true` |
   | `EXTRASECURITY_RECAPTCHA_MAIN_PROVIDER` | `turnstile` |
   | `EXTRASECURITY_RECAPTCHA_MAIN_TYPE` | `checkbox` |
   | `EXTRASECURITY_RECAPTCHA_MAIN_TURNSTILE_SITE_KEY` | `0x4AAAAAADsURQLrsIeJlDCP` |
   | `EXTRASECURITY_RECAPTCHA_MAIN_TURNSTILE_SECRET_KEY` | `<\Helper::encrypt(secret)>` |

3. **Applied + cached** the config (config is cached in production):
   ```bash
   php artisan config:cache
   ```

---

## Important implementation notes

- **The secret key is stored ENCRYPTED.** The module reads it via
  `getEncryptedParameter()` → `\Helper::decrypt()` at validation time
  (`ExtraSecurityServiceProvider.php:565,856`). When setting it by hand, encrypt
  first:
  ```bash
  php artisan tinker --execute="echo \Helper::encrypt('<TURNSTILE_SECRET>');"
  ```
  (`\Helper::decrypt` is tolerant of plaintext, but store it encrypted to match
  how the module's own Settings UI saves it.)
- **Settings live in `.env`**, not the `options` table. Because production caches
  config, **always rebuild** with `php artisan config:cache` after editing `.env`.
- The cleaner alternative to hand-editing `.env` is the admin UI:
  **Settings → Extra Security → Main login**, choose provider *Turnstile*, paste
  the site + secret keys, Save (handles encryption + cache automatically).

---

## Verification performed

| Check | Result |
|-------|--------|
| Secret validity (Turnstile `siteverify` with dummy token) | `invalid-input-response` (not `invalid-input-secret`) → **secret valid** ✅ |
| Config loaded (`config('extrasecurity.recaptcha_main_*')`) | enabled=true, provider=turnstile, type=checkbox, sitekey set, secret decrypts correctly ✅ |
| Live login page (`GET /login`) | renders `cf-turnstile` div + `data-sitekey` + loads `challenges.cloudflare.com/turnstile/v0/api.js`; no errors ✅ |
| End-to-end browser login | ⚠️ not auto-testable — must be confirmed manually in an incognito window |

---

## Rollback

```bash
# Option A: disable the captcha
#   set EXTRASECURITY_RECAPTCHA_MAIN_ENABLED=  (empty) in .env, then:
php artisan config:cache

# Option B: restore the pre-change backup
cp /var/www/freescout/.env.bak-20260628_070546 /var/www/freescout/.env
php artisan config:cache
```

---

## Security debt (must be addressed)

The Cloudflare account credentials were shared in chat to perform the API setup and
**must be rotated** (the Turnstile widget keys are independent and keep working
after rotation):

- [ ] **Rotate the Cloudflare Global API Key** (`cfk_…`) — it grants full
      *Super Administrator* access to the whole account.
- [ ] **Change the Cloudflare account password** (also shared in chat).
- [ ] **Enable 2FA** on the Cloudflare account (was disabled).

---

## Possible follow-ups

- Extend Turnstile to the **End-User Portal** login / submit form (the module
  supports separate widgets: `recaptcha_eup_*`, `recaptcha_eup_submit_*`).
- Combine with the planned Venezuela IP allowlist (see related doc) for layered
  hardening.
