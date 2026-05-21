# partner.communication.ack — Form UX Improvements

**Status:** Fixes 1–8 deployed v17.0.1.6.13 (2026-05-21) | Fixes 9–10 pending  
**Module:** `ueipab_attendance_report`  
**View file:** `views/partner_communication_ack_views.xml`  
**Identified:** 2026-05-20 during Budget Vote campaign monitoring  

---

## Context

Identified while reviewing record id=204 (MARIANA MADERA, `leaving`, voted via email_link 2026-05-20 14:20).
The form is used by HR to monitor and manage the budget vote campaign (`budget_consulta_2026_2027`) and
the PDVSA continuity campaign (`pdvsa_continuacion_2026_2027`). These are critical business processes —
UX clarity directly affects data integrity.

---

## Issues & Fixes

### 🔴 HIGH PRIORITY

#### 1. `leaving` decoration color is wrong (tree view)
**Current:** `decoration-info` (blue) — signals neutral/informational  
**Problem:** A family that won't continue is at-risk. Blue is misleading.  
**Fix:** Change to `decoration-danger` (red)

```xml
<!-- BEFORE -->
decoration-info="state == 'leaving'"

<!-- AFTER -->
decoration-danger="state == 'leaving'"
```

Same fix needed on the `state` badge widget in the tree.

---

#### 2. No confirmation on "Reiniciar a Pendiente"
**Current:** One click immediately resets a confirmed vote — no warning.  
**Problem:** Accidental resets are irreversible and corrupt audit data.  
**Fix:** Add `confirm` attribute.

```xml
<!-- BEFORE -->
<button name="action_reset_pending" string="Reiniciar a Pendiente"
        type="object"
        invisible="state == 'pending'"/>

<!-- AFTER -->
<button name="action_reset_pending" string="Reiniciar a Pendiente"
        type="object"
        invisible="state == 'pending'"
        confirm="¿Está seguro de que desea reiniciar este voto? Esta acción elimina el registro de decisión del representante y no se puede deshacer."/>
```

---

#### 3. No outcome banner — HR doesn't know what the state means
**Current:** Only a statusbar badge (`pending`/`continuing`/`leaving`).  
**Problem:** HR users don't immediately understand the business impact of each state.  
**Fix:** Add a colored alert div at the top of the sheet.

```xml
<div class="alert alert-danger mb-3"
     invisible="state != 'leaving'">
    <strong>⚠️ Esta familia ha seleccionado NO continuar.</strong>
    Opción B — $236.58/mes. Requiere seguimiento.
</div>
<div class="alert alert-success mb-3"
     invisible="state != 'continuing'">
    <strong>✅ Esta familia continuará el próximo año escolar.</strong>
    Opción A — $218.88/mes.
</div>
<div class="alert alert-warning mb-3"
     invisible="state != 'pending'">
    <strong>⏳ Pendiente de respuesta.</strong>
    El representante aún no ha votado.
</div>
```

---

### 🟡 MEDIUM PRIORITY

#### 4. Raw `token` exposed in form
**Current:** UUID token visible in "Sistema" group — anyone with HR access can copy it and vote on behalf of a family.  
**Fix:** Wrap in a `groups="base.group_system"` invisible group or collapse by default.

```xml
<!-- Only show token to system admins -->
<field name="token" groups="base.group_system"/>
```

---

#### 5. `partner_phone` duplicated
**Current:** Appears in both "Representante" group (line 78) AND "Sistema" group (line 99).  
**Fix:** Remove from "Sistema" group — keep only in "Representante".

```xml
<!-- REMOVE this from the Sistema group -->
<field name="partner_phone" invisible="not partner_phone"/>
```

---

#### 6. `statusbar` implies linear workflow — wrong widget
**Current:** `pending → continuing → leaving` looks like a progression.  
**Problem:** `continuing` and `leaving` are parallel alternatives (Opción A or B), not sequential steps.  
**Fix:** Replace statusbar with a `widget="badge"` field or remove it entirely — state is already shown in the outcome banner (fix #3).

```xml
<!-- CONSIDER replacing statusbar with readonly badge -->
<field name="state" widget="badge"
       decoration-warning="state == 'pending'"
       decoration-success="state == 'continuing'"
       decoration-danger="state == 'leaving'"
       readonly="1"/>
```

---

#### 7. `ack_ip` in wrong group
**Current:** IP address shown in "Votación" group alongside `sent_date` and `ack_date`.  
**Problem:** An IP address has no meaning to an HR user. It creates noise.  
**Fix:** Move to "Sistema" group.

---

### 🟢 LOW PRIORITY

#### 8. `vote_notes` editable after vote is cast
**Current:** Free-text notes editable in any state.  
**Problem:** Post-vote note edits leave no audit trail. Integrity risk.  
**Fix:** Make readonly once voted.

```xml
<field name="vote_notes" nolabel="1"
       readonly="state in ('continuing', 'leaving')"/>
```

---

#### 9. No response time display
**Nice to have:** Show how quickly the family responded after receiving the email.  
**Implementation:** Computed field `response_hours = (ack_date - sent_date).hours` displayed as  
*"Respondió 2h 15min después del envío"* — adds audit richness.  
Requires Python field addition in `partner_communication_ack.py`.

---

#### 10. No smart button to partner record
**Current:** `partner_id` shown as a Many2one field — no one-click jump to the full contact.  
**Fix:** Add a stat button in `button_box` linking to the partner's form view.

```xml
<button name="%(base.action_res_partner_form)d"
        type="action"
        class="oe_stat_button"
        icon="fa-user"
        string="Ver Contacto"
        context="{'default_id': partner_id}"/>
```

---

## Implementation Status

| # | Fix | Status |
|---|-----|--------|
| 1 | `leaving` decoration → `info` (blue, not red) | ✅ v1.6.13 |
| 2 | Confirm dialog on "Reiniciar a Pendiente" | ✅ v1.6.11 |
| 3 | Outcome banners (colored alert divs) | ✅ v1.6.11 |
| 4 | Hide raw `token` from non-admins | ✅ v1.6.11 |
| 5 | Remove duplicate `partner_phone` from Sistema | ✅ v1.6.11 |
| 6 | Replace `statusbar` widget with `badge` | ✅ v1.6.11 |
| 7 | Move `ack_ip` to Sistema group | ✅ v1.6.11 |
| 8 | `vote_notes` readonly after vote cast | ✅ v1.6.11 |
| 9 | `response_time` computed field — *"Respondió 2h 15min después del envío"* | ✅ v1.6.14 |
| 10 | Smart button → partner form (`oe_stat_button`) | ✅ v1.6.14 |

**Additional fixes (2026-05-21):**
- State labels renamed: `"Continuará"` → `"Opción A"` / `"No continuará"` → `"Opción B"` — v1.6.12
- Opción B color: `decoration-danger` (red) → `decoration-info` (blue) — both A and B are valid decisions — v1.6.13
- Outcome banners: generic text, no campaign-specific language — works for both budget vote and PDVSA campaigns

---

## ⚠️ Structural Note — Pending Refactor

**`partner.communication.ack` is misplaced in `ueipab_attendance_report`.**

The model, views, controller, and wizard were first created here for convenience, but the module has no conceptual ownership of campaign acknowledgments. The model serves:
- Budget Consultation 2026-2027 (AI Agent / Glenda campaign)
- PDVSA Continuity Campaign (AI Agent / Glenda campaign)
- Representante Continuity Campaign (planned)

**Correct home:** `ueipab_ai_agent` (already owns all campaign logic) or a new dedicated `ueipab_campaigns` module.

**Files to relocate:**
- `models/partner_communication_ack.py`
- `views/partner_communication_ack_views.xml`
- `controllers/partner_ack.py`
- `wizard/vote_assist_wizard.py` + `views/vote_assist_wizard_views.xml`
- Security rules in `security/ir.model.access.csv`

**Migration required** (model is in production DB). Low urgency — zero functional impact until refactor is done.
