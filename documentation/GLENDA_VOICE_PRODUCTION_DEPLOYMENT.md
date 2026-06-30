# Glenda Voice Calls — Production Deployment

**Status:** ✅ **DEPLOYED 2026-06-30** (capability live; parent-facing calling gated — see §1) | **Depends on:** [GLENDA_VOICE_CALL_POC.md](GLENDA_VOICE_CALL_POC.md)

## ✅ Deployed 2026-06-30 — what was done

| Step | Result |
|------|--------|
| DO firewall `ueipab-fw` | inbound + outbound **tcp/8090 restricted to VPC `10.124.0.0/20`** (prod↔gateway; NOT public) |
| DNS | `A voice.ueipab.edu.ve → 64.23.157.121` (DigitalOcean) |
| nginx + TLS | vhost on ueipab2 → `localhost:8090`, WS headers, Let's Encrypt cert; **`/place-call` denied publicly (403)** |
| Gateway | `public_host=voice.ueipab.edu.ve`; **cloudflared tunnel retired** (service stopped+disabled) |
| Odoo module | `ueipab_ai_agent` **17.0.1.60.0 installed in DB_UEIPAB** (backup `/root/ueipab_ai_agent_backup_20260630_065705.tgz`); model + menus live |
| Prod settings | `voice_call.*` seeded: gateway_url `http://10.124.0.2:8090`, callback_base `http://10.124.0.3:8075`, caller_id `+15093843032` (US interim), fresh callback_token, **enabled=True** |
| Smoke test | prod Odoo → call to Gustavo (62s); status + transcript landed on `DB_UEIPAB` record #1; `get_pricing` returns live DB_UEIPAB data |

**Networking (prod):** prod Odoo `10.124.0.3` → gateway `10.124.0.2:8090` (VPC); gateway → prod Odoo
`10.124.0.3:8075` (VPC); Twilio → `https://voice.ueipab.edu.ve` (public 443). The gateway is multi-tenant
(each place-call carries its own callback/tool URLs), so it serves both `testing` and `DB_UEIPAB`.

> ⚠️ **GATE STILL OPEN — do NOT cold-call parents yet.** Caller ID is the US interim (low VE pickup) and
> legal consent/quiet-hours sign-off is pending. `voice_call.enabled=True` only powers the staff button +
> internal use. Before any parent batch: resolve caller ID (Movistar SIM + display test) and consent.
> **Kill switch:** set `voice_call.enabled=False` in DB_UEIPAB.

---

## (original plan retained below)



Moves the outbound voice POC (validated in testing 2026-06-30) to production. The POC
ran on the dev host `ueipab2` (64.23.157.121) behind an ephemeral cloudflared tunnel,
calling from a US Twilio number against the `testing` DB. Production hardens three things:
**stable hostname, prod Odoo wiring, and the go-live gates (caller ID, consent, cost).**

---

## 0. What "production" means here

| Layer | POC (testing) | Production target |
|-------|---------------|-------------------|
| Gateway host | `ueipab2` 64.23.157.121 (dev) | **Decide:** prod droplet `10.124.0.3` *or* keep on `ueipab2` (isolated from Odoo either way) |
| Public ingress | cloudflared quick tunnel (URL changes on restart) | **`voice.ueipab.edu.ve`** → nginx + Let's Encrypt (stable) |
| Odoo | `testing` (container `odoo-dev-web`) | **`DB_UEIPAB`** (container `ueipab17`, host `10.124.0.3`) |
| Caller ID | US `+15093843032` | Movistar VE (pending SIM + display test) — else US as interim |
| Twilio | shared trial-ish acct, ~$21 bal | funded prod balance + alerts |

> ⚠️ **The gateway must NOT run inside an Odoo worker.** It holds a persistent WebSocket per
> live call; keep it as its own systemd service / container, ideally on a host with headroom.

---

## 1. Prerequisites (hard gates before any parent call)

- [ ] **Twilio:** funded balance + low-balance alert; **Venezuela Voice Geographic Permission ON**; production caller ID (see §5).
- [ ] **OpenAI:** key entitled for `gpt-realtime-2`; usage/billing limit set (Realtime audio is the dominant cost).
- [ ] **Caller-ID display test PASSED** (or accepted US-number interim) — see §5 + POC caveat.
- [ ] **Consent / disclosure / quiet-hours** policy signed off (legal) — see §6.
- [ ] **Stable hostname** `voice.ueipab.edu.ve` live with TLS — see §3.

---

## 2. Gateway deployment (host)

Same artifacts as the POC (`voice_gateway/`), promoted to a stable service.

```bash
# On the chosen gateway host (prod):
cd /opt/odoo-dev/voice_gateway        # or the prod clone path
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
# config/twilio_api.json  (gitignored) — prod Twilio creds + gateway.public_host=voice.ueipab.edu.ve
# systemd: glenda-voice.service (uvicorn :8090)  — already authored in the POC
systemctl enable --now glenda-voice.service
curl -fsS http://localhost:8090/health
```

**Retire cloudflared in prod.** The quick tunnel + `glenda-voice-tunnel.service` were a POC
convenience (and required opening DO firewall `ueipab-fw` outbound 7844). Production uses nginx
instead, so **disable the tunnel service** and the 7844 rule is no longer needed.

---

## 3. Stable hostname + nginx (replaces the tunnel)

1. **DNS (DigitalOcean):** `A  voice.ueipab.edu.ve → <gateway host public IP>` (token in
   `/var/www/dev/network/do-api.json`; the domain is DO-managed).
2. **nginx server block** proxying `:8090` with **WebSocket upgrade headers** (the `/media`
   stream is a WS — required):
   ```nginx
   server {
     server_name voice.ueipab.edu.ve;
     location / {
       proxy_pass http://127.0.0.1:8090;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_read_timeout 3600s;          # long-lived call audio
     }
   }
   ```
3. **certbot** issue cert for `voice.ueipab.edu.ve` (host already serves 443 for other vhosts).
4. Set `gateway.public_host=voice.ueipab.edu.ve` in `config/twilio_api.json`. The gateway already
   derives the WSS host from the request `Host` header, so TwiML will advertise the stable host.

Needs only **inbound 443** (already open); no 7844 dependency.

---

## 4. Odoo module deployment (DB_UEIPAB)

⚠️ **Prod addons (`/home/vision/ueipab17/addons`) is a SEPARATE git repo** (`3DVision-CA/ueipab17-cm`),
NOT this dev repo — `git pull` there will NOT carry these commits. **scp the changed files**, then
upgrade. (See CLAUDE.md "PROD DEPLOY MECHANISM".)

**New/changed files to copy into prod `ueipab_ai_agent/`:**
- `models/ai_agent_voice_call.py`, `models/res_config_settings_voice.py`, `models/__init__.py`
- `controllers/voice_webhook.py`, `controllers/__init__.py`
- `views/ai_agent_voice_call_views.xml`, `views/menus.xml`
- `security/ir.model.access.csv`, `__manifest__.py` (→ 17.0.1.60.0)

```bash
# back up prod addons first, then:
docker exec ueipab17 odoo -u ueipab_ai_agent -d DB_UEIPAB --stop-after-init
docker restart ueipab17
# verify installed_version == 17.0.1.60.0 via XML-RPC
```

---

## 5. Caller ID (the answer-rate gate)

POC findings carried forward:
- Twilio sells **no VE numbers**; a VE number can be a **Verified Caller ID** (verified once,
  then display-only) — `voice_gateway/verify_caller_id.py` is ready.
- The WhatsApp backup `+584248944898` (0424 Movistar) **cannot** be verified — it's WABA-locked
  (verification voice call failed). Use a **plain prepaid Movistar SIM** instead.
- **Unconfirmed:** whether VE carriers display a verified VE caller ID on internationally-originated
  Twilio calls or override it. **Run the display test** (verified VE number → a 2nd VE phone) before
  committing to the SIM route. If overridden → caller ID can't be fixed via Twilio; use US interim or
  pivot to **WhatsApp Business Calling** (no number/SIM; rides META_CLOUD_API_MIGRATION_PLAN.md).
- Interim: US `+15093843032` works but lowers pickup.

---

## 6. Compliance, safety, cost controls

- **Disclosure:** every call opens "…asistente virtual automatizada del Colegio Andrés Bello." (already in prompt).
- **Quiet hours / VET work hours** + **opt-out / do-not-call** list before any batch.
- **Recording:** off by default; enable only with a retention/privacy decision.
- **Privacy:** `get_balance` only by cédula, never reveal one parent's balance to another (enforced in prompt).
- **Concurrency cap** (bound RAM + cost); **per-day call cap**; Twilio balance + OpenAI usage alerts.
- **Kill switch:** `voice_call.enabled=False` disables the 📞 button instantly; `systemctl stop glenda-voice` halts the gateway.

---

## 7. Prod settings (AI Agent → Configuracion → Ajustes de Voz / `ir.config_parameter`)

| Param | Prod value |
|-------|-----------|
| `voice_call.enabled` | `True` only after gates pass |
| `voice_call.caller_id` | VE Movistar (verified) or US interim |
| `voice_call.voice` / `realtime_model` | `sage` / `gpt-realtime-2` |
| `voice_call.gateway_url` | Odoo(`ueipab17`)→gateway: `http://<bridge-gw-ip>:8090` (find via `docker inspect ueipab17`) or `https://voice.ueipab.edu.ve` |
| `voice_call.callback_base` | gateway→Odoo: prod Odoo internal URL (host port of `ueipab17`) |
| `voice_call.callback_token` | fresh random secret (NOT the testing one) |

⚠️ Prod **nginx route whitelist** must allow `/ai-agent/voice/callback` and `/ai-agent/voice/tool`
if callbacks traverse the public vhost (same pattern as the enrollment-journey whitelist note).
Prefer keeping gateway↔Odoo on the internal Docker/host network to avoid exposing them publicly.

---

## 8. Go-live checklist

- [ ] Gateway service up on prod host; `/health` OK; `voice.ueipab.edu.ve` TLS resolves.
- [ ] `config/twilio_api.json` on prod host (prod creds, `public_host=voice.ueipab.edu.ve`).
- [ ] `ueipab_ai_agent` 17.0.1.60.0 installed in `DB_UEIPAB`; menus visible.
- [ ] Prod `voice_call.*` params set; fresh `callback_token`.
- [ ] Tool endpoints return prod data (`get_pricing` from DB_UEIPAB catalog; `get_balance` real cédula).
- [ ] **Smoke call to Gustavo** through the prod Odoo button → transcript + status land on the record.
- [ ] Caller-ID decision finalized; consent/quiet-hours signed off.
- [ ] Concurrency cap + cost alerts configured.

---

## 9. Rollback

1. `voice_call.enabled=False` (button disabled; no new calls).
2. `systemctl stop glenda-voice` (gateway down).
3. Odoo: revert `ueipab_ai_agent` to the prior backup version + restart `ueipab17`.
4. The `ai.agent.voice.call` records are inert data; safe to keep.

---

## Open decisions (need a human call)

1. **Gateway host:** prod droplet vs. dev `ueipab2` (RAM/headroom).
2. **Caller ID strategy:** Movistar SIM (after display test) vs. US interim vs. WhatsApp Calling pivot.
3. **First audience:** internal smoke only → small overdue-balance batch → wider.
4. **Recording on/off** + retention.
