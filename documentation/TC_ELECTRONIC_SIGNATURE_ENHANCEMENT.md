# T&C Electronic-Signature Enhancement — Contract & Quotation

**Created:** 2026-06-27 · **Updated:** 2026-06-30
**Status:** ✅ IMPLEMENTED + **DEPLOYED TO PROD** (e-firma + anticipo clauses live in the prod Acuerdo/Contrato PDFs). **2026-06-30: clause softened to CONDITIONAL/PERMISSIVE + scope narrowed — enrollment v1 does NOT capture e-signatures** (clause is contract text only; acceptance is in-person/manual). **B6 counsel gate CLEARED** (`enrollment.b6_counsel_signed=True`) and the **S0 enrollment blast launched**. See the 2026-06-30 entry below. (Earlier: deployed to prod 2026-06-29 via `ueipab_sales` 17.0.1.2.5 + `ueipab_enrollment_journey` 17.0.0.14.0.)
**Legal basis:** [ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md](ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md) · **Related:** [QUOTE_ACCEPTANCE_VERSIONING_PLAN.md](QUOTE_ACCEPTANCE_VERSIONING_PLAN.md)

## Implementation log

| Date | Quotation (`ueipab_sales`) | Contract (`ueipab_enrollment_journey`) |
|---|---|---|
| 2026-06-28 | v17.0.1.2.4 — **Cl.10 Aceptación electrónica** + DECLARACIÓN amended | v17.0.0.13.1 — **Cl.11 Aceptación electrónica** + acceptance note under signatures |
| 2026-06-28 | v17.0.1.2.5 — **Cl.11 Facturación fraccionada / recuperación de anticipos** | v17.0.0.13.2 — **Cl.12 Facturación fraccionada / recuperación de anticipos** |
| 2026-06-30 | v17.0.1.2.6 — **Cl.10 softened to conditional/permissive** ("Cuando la aceptación se efectúe por medios electrónicos … **podrá** registrar y conservar …") | v17.0.0.15.2 — **Cl.11 softened to conditional/permissive** (same wording swap) |

Both upgraded + PDFs re-rendered in `testing`; review copies emailed to gustavo.perdomo@ueipab.edu.ve. Deployed to production 2026-06-29; the 2026-06-30 softening deployed to both envs + prod.

## 2026-06-30 — Scope decision (no e-sig capture in v1) + clause softening

**Scope decision (CEO Gustavo, 2026-06-30):** enrollment **v1 will NOT capture electronic signatures.** There is **no e-signature acceptance flow** in v1 — nothing captures IP / UA / UTC timestamp / SHA-256 as the *binding* signature. The electronic-acceptance clause remains in the parent-facing PDFs as **contract text only**; actual acceptance in v1 is **in-person / manual (handwritten)**. The e-signature capture mechanism (the Tier-2 bundle described in this doc) is **deferred to a later version**.

**Clause softening (deployed both envs + prod):** to match that scope, the present-tense *capture* sentence in the electronic-acceptance clause was made **conditional + permissive** in BOTH PDFs so the contract no longer asserts evidentiary capture that isn't happening:

- **Acuerdo Cl.10** — `addons/ueipab_sales/reports/quotation_agreement_report.xml` — `ueipab_sales` **17.0.1.2.5 → 17.0.1.2.6**
- **Contrato Cl.11** — `addons/ueipab_enrollment_journey/reports/enrollment_contract_views.xml` — `ueipab_enrollment_journey` **17.0.0.15.1 → 17.0.0.15.2**

| | Text |
|---|---|
| **Before** | "EL PRESTADOR DE SERVICIOS **registra y conserva** la fecha/hora (UTC), la dirección IP, el identificador del dispositivo y el hash SHA-256 del documento aceptado …" |
| **After** | "**Cuando la aceptación se efectúe por medios electrónicos,** EL PRESTADOR DE SERVICIOS **podrá registrar y conservar** la fecha/hora (UTC), la dirección IP, el identificador del dispositivo y el hash SHA-256 …" |

**Rationale:** for a v1 in-person/manual signing, the clause now only bites **when electronic acceptance is actually used**, and the handwritten-signature path remains intact. **Legal basis unchanged** — Decreto-Ley Sobre Mensajes de Datos y Firmas Electrónicas: Art. 16 *("salvo que las partes dispongan otra cosa")*, Art. 4/7/8 (valor probatorio), Art. 17 (sana crítica), Art. 18 (SUSCERTE). See the article-mapping table below.

**B6 counsel gate CLEARED:** the counsel sign-off gate (B6) was subsequently cleared by the CEO (`ir.config_parameter enrollment.b6_counsel_signed=True`) and the **S0 enrollment blast launched.**

## Why

Parents now accept the quotation **electronically** (tick the T&C box + click "Acepto" on the journey page; we capture IP + UTC timestamp + PDF SHA-256 + retained data message — the Tier-2 bundle). But **both legal documents currently contemplate only a wet/physical signature**, which contradicts the act actually performed:

- **Acuerdo de Inscripción (Cotización)** — `addons/ueipab_sales/reports/quotation_agreement_report.xml` — DECLARACIÓN DE ACEPTACIÓN says *"Al estampar la firma … sus firmas y huellas dactilares."*
- **Contrato de Servicio Educativo** — `addons/ueipab_enrollment_journey/reports/enrollment_contract_views.xml` — plain INSTITUCIÓN / REPRESENTANTE signature lines, no electronic-acceptance language.

The fix adds an explicit **electronic-acceptance clause** that binds the parties to the exact mechanism we built, plus aligns the acceptance declaration. The load-bearing legal hook is **Art. 16's *"salvo que las partes dispongan otra cosa"*** — the law expressly lets the parties **agree** what constitutes a valid electronic signature.

## Article mapping (what the clause leans on)

| Clause assertion | Article (LMDFE, G.O. 37.148/2001) |
|---|---|
| Parties may agree the e-acceptance mechanism | Art. 16 ("salvo que las partes dispongan otra cosa") |
| E-signature = same value as firma autógrafa | Art. 16 |
| Data message = same probative value as written doc; printout = fotostática | Art. 4 (¶1, ¶3) |
| Integrity / original form (hash) | Art. 7 |
| Conservation + metadata (IP, fecha/hora) | Art. 8 (incl. 8(3)) |
| Even if Art. 16 unmet → elemento de convicción / sana crítica | Art. 17 |
| Optional certified signature via SUSCERTE PSC | Art. 18 |

---

## A) Quotation — `quotation_agreement_report.xml`

### A1. New **Clause 10** (insert after Clause 9 "NOTIFICACIONES, DOMICILIO Y JURISDICCIÓN", before the DECLARACIÓN box)

> **10. ACEPTACIÓN ELECTRÓNICA Y VALIDEZ DE LA FIRMA ELECTRÓNICA**
> De conformidad con el Decreto-Ley Sobre Mensajes de Datos y Firmas Electrónicas (Gaceta Oficial N° 37.148 del 28 de febrero de 2001), las partes reconocen y aceptan que el presente Acuerdo de Inscripción y sus Términos y Condiciones podrán suscribirse y aceptarse por medios electrónicos. Conforme a la facultad prevista en el **artículo 16** *("salvo que las partes dispongan otra cosa")*, las partes **convienen** que la manifestación de voluntad del REPRESENTANTE expresada mediante la aceptación en línea —marcando la casilla de aceptación de estos Términos y Condiciones y accionando el botón "Acepto"— constituye una **Firma Electrónica** que lo vincula con el Mensaje de Datos y le atribuye su autoría, con la **misma validez y eficacia probatoria que la ley otorga a la firma autógrafa (manuscrita)**.
>
> El REPRESENTANTE reconoce que, como respaldo de dicha aceptación, EL PRESTADOR DE SERVICIOS registra y conserva la **fecha y hora (UTC)** de la aceptación, la **dirección IP** de origen, el identificador del dispositivo, y un **valor criptográfico (hash SHA-256)** del documento aceptado que garantiza su integridad e inalterabilidad. Las partes acuerdan que dichos registros, así como el Mensaje de Datos conservado y su reproducción impresa, tendrán pleno valor probatorio conforme a los **artículos 4, 7 y 8** del referido Decreto-Ley. En ausencia de los requisitos del artículo 16, la presente aceptación electrónica constituirá, en todo caso, un **elemento de convicción valorable conforme a las reglas de la sana crítica (artículo 17)**.
>
> Lo anterior se entiende sin perjuicio de que el documento pueda igualmente suscribirse mediante firma autógrafa y/o **firma electrónica certificada** por un Proveedor de Servicios de Certificación acreditado ante la SUSCERTE (**artículo 18**), cuando así lo requiera EL PRESTADOR DE SERVICIOS.

### A2. Amend the **DECLARACIÓN DE ACEPTACIÓN** box

Replace the opening of the existing declaration with text that covers both paths:

> **DECLARACIÓN DE ACEPTACIÓN:** Al estampar su firma en el documento principal "Acuerdo de Inscripción" (Ref. *{order.name}*) **o, en su caso, al aceptarlo electrónicamente conforme a la Cláusula 10**, el Representante ratifica que ha leído de manera detenida, comprende y acepta vincularse jurídicamente bajo los presentes Términos y Condiciones. **La aceptación electrónica produce los mismos efectos jurídicos que la firma autógrafa.**

*(Keep the "Iniciales del Representante" line for the printed/wet path.)*

---

## B) Contract — `enrollment_contract_views.xml`

### B1. New **Clause 11** (insert after Clause 10 "DOMICILIO ELECTRÓNICO, CITACIONES Y JURISDICCIÓN", before the signature block)

Same canonical text as A1, with two wording swaps for the contract context:
- "el presente **Contrato de Servicio Educativo** y sus Términos y Condiciones" (instead of "Acuerdo de Inscripción").
- Reference document: "la **Orden de Servicio** antecedente" where applicable.

> **11. ACEPTACIÓN ELECTRÓNICA Y VALIDEZ DE LA FIRMA ELECTRÓNICA**
> De conformidad con el Decreto-Ley Sobre Mensajes de Datos y Firmas Electrónicas (Gaceta Oficial N° 37.148 del 28/02/2001), las partes reconocen y aceptan que el presente Contrato de Servicio Educativo y sus Términos y Condiciones podrán suscribirse y aceptarse por medios electrónicos. Conforme al **artículo 16** *("salvo que las partes dispongan otra cosa")*, las partes **convienen** que la aceptación en línea del REPRESENTANTE —marcando la casilla de aceptación y accionando el botón "Acepto"— constituye una **Firma Electrónica** con la **misma validez y eficacia probatoria que la firma autógrafa**. EL PRESTADOR DE SERVICIOS registra y conserva la **fecha/hora (UTC)**, la **dirección IP**, el identificador del dispositivo y el **hash SHA-256** del documento aceptado; dichos registros, el Mensaje de Datos conservado y su reproducción impresa tendrán pleno valor probatorio conforme a los **artículos 4, 7 y 8**, y en su defecto serán valorables conforme a la **sana crítica (artículo 17)**. Ello sin perjuicio de la firma autógrafa y/o de la **firma electrónica certificada** por un PSC acreditado ante la SUSCERTE (**artículo 18**) cuando la institución lo requiera.

### B2. Acceptance note under the signature block

Below the INSTITUCIÓN / REPRESENTANTE signature lines, add a small line:

> *Cuando el presente contrato sea aceptado por medios electrónicos conforme a la Cláusula 11, la firma manuscrita podrá ser sustituida por la aceptación electrónica registrada por la institución, con plenos efectos jurídicos.*

---

---

## C) Fractioned invoicing / advance recovery (anticipos) — added 2026-06-28

Authorizes the institution to issue **multiple fiscal invoices against a single advance payment (Anticipo)** so it is recovered/applied progressively. Two named scenarios: **inscripción/matrícula** and **cierre de períodos académicos**. Key protection: states it is **not double-billing** (imputación progresiva de un pago ya realizado). Emission per SENIAT rules + **BCV rate at each invoice's emission date**; cambiaria differences link to the existing ajustes clause (quotation Cl.4 / contract Cl.3).

- **Quotation** → **Clause 11** (after e-firma Cl.10, before the DECLARACIÓN box).
- **Contract** → **Clause 12** (after e-firma Cl.11, before the signature block).
- **Legal basis:** SENIAT facturación (Providencia SNAT/2011/00071 — one factura per operación/concepto) + the BCV-rate-at-invoice-date principle already in both T&C.

Canonical text lives in the rendered templates (`quotation_agreement_report.xml`, `enrollment_contract_views.xml`). Institution-wide scope (EL PRESTADOR DE SERVICIOS), not high-school-only.

## Implementation notes (when approved)

- **Pure QWeb/XML edits** in the two report templates — no model/migration. Standard `<p>`/`<ul>` blocks matching each doc's existing T&C styling (quotation: `font-size:7.8pt` blue headers; contract: `font-size:8pt #1a2c5b` headers).
- **Version bumps:** `ueipab_sales` (quotation) + `ueipab_enrollment_journey` (contract); upgrade each module in `testing` (templates live in DB after `-u`).
- **i18n:** body_html templates are static Spanish in XML — no JSONB/lang concern (unlike `mail.template`).
- **Verify:** re-render both PDFs (`_render_qweb_pdf`) and confirm the new clause + amended declaration appear; the QR seal/verify routes are unaffected.
- **Prod:** ships with the normal scp deploy of each module; no extra steps.

## Caveats

- Drafting support, **not formal legal advice.** The Art. 16 *"las partes disponen"* wording is load-bearing — have counsel confirm before production use.
- Numbering assumes current clause counts (quotation→10, contract→11); re-check if the T&C are edited before this lands.
- Consider pairing with deferred enhancement #2 (acceptance "acta" page appended to the accepted PDF) so the captured evidence is visible inside the very document the clause describes — see legal doc §9.
