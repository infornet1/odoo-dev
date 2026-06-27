# Electronic Signatures under Venezuelan Law — Implementation Guide

**Created:** 2026-06-27
**Context:** Legal research for letting parents/representatives electronically sign / accept UEIPAB enrollment documents — the **Acuerdo de Inscripción (Cotización)** and the **Contrato de Servicio Educativo** — with the strongest defensible evidentiary value.
**Status:** Research synthesis (multi-source, cited). **Not formal legal advice** — confirm the live SUSCERTE PSC roster and the PSC-vs-simple tiering with Venezuelan counsel before relying on it in litigation.

> **⚠️ Premise correction (most important accuracy point).** A common belief is that **Art. 16** lists *four* conditions including "exclusive control of the signer" and "must be backed by a PSC certificate." **The Venezuelan statute does not say that.** Two independent full-text fetches (Gaceta PDF via Justia + Universidad de Carabobo law-review reproduction) agree verbatim that **Art. 16 lists exactly THREE conditions**, and the "certified by an accredited PSC ⇒ deemed compliant" rule is a **separate article — Art. 18**. The four-condition formula matches the UNCITRAL Model Law / EU Directive 1999/93/EC, not Venezuela's Decreto 1.204.

---

## 1. Governing Legal Framework

- **Primary statute:** *Decreto con Rango y Fuerza de Ley Sobre Mensajes de Datos y Firmas Electrónicas* (**LMDFE**), **Decreto N° 1.204**, **Gaceta Oficial N° 37.148 of 28 Feb 2001**. (Some reproductions misprint "1.024" — a typo; Gaceta 37.148 / 28-Feb-2001 is consistent everywhere.)
- **Object [Art. 1]:** grants legal validity + evidentiary value to the *Firma Electrónica*, the *Mensaje de Datos*, and intelligible electronic information "independientemente de su soporte material"; regulates *Proveedores de Servicios de Certificación* (PSC) and *Certificados Electrónicos*. **Technological neutrality lives in Art. 1** (Art. 3 is about adoption by public bodies).
- **Reglamento Parcial:** *Decreto N° 3.335*, **Gaceta Oficial N° 38.086 of 14 Dec 2004** — develops PSC accreditation before SUSCERTE, auditor registry, security standards.
- **Later reforms:** none found to the 2001 Decreto-Ley itself (tagged "Vigente"; treat "never amended" as strongly supported, not positively certified).
- **Interaction with other law:**
  - **Código de Procedimiento Civil (CPC):** Art. 4 LMDFE routes data messages into the **"pruebas libres"** regime (CPC Art. 395); a **printout = photostatic copy** (practical link to CPC Art. 429), weighed under *sana crítica* (CPC Art. 507).
  - **Código Civil / Código de Comercio:** electronic signature gets the same *eficacia* as the written private instrument + *firma autógrafa* where requirements are met.
  - **Ley de Infogobierno (2013, G.O. 40.274):** Art. 24 requires the Public Power to use certificates/signatures within the State's chain of trust (primarily a public-sector mandate). *(Medium confidence on exact article.)*
  - **Ley de Registros y Notarías (LRN, G.O. 6.668 Ext., 16 Dec 2021):** supplies the electronic-equivalence path for **notarial/registral** acts (LRN Arts. 2 & 68) — see §7.

---

## 2. Key Definitions & Validity

**Definitions [Art. 2], verbatim:**
- *Mensaje de Datos*: "Toda información inteligible en formato electrónico o similar que pueda ser almacenada o intercambiada por cualquier medio."
- *Firma Electrónica*: "Información creada o utilizada por el Signatario, asociada al Mensaje de Datos, que permite atribuirle su autoría bajo el contexto en el cual ha sido empleado."
- *Certificado Electrónico*: "Mensaje de Datos proporcionado por un Proveedor de Servicios de Certificación que le atribuye certeza y validez a la Firma Electrónica."
- The law does **not** separately define "firma electrónica certificada" — that = *Firma Electrónica* + *Certificado Electrónico* + Art. 18.

**Evidentiary equivalence [Art. 4], three paragraphs:**
1. Data messages have **the same probative value the law gives to written documents** (subject to Art. 6 ¶1).
2. Offered/controlled/contested/evacuated as **pruebas libres** under the CPC (→ Art. 395).
3. A **printout has the same probative value as a photostatic copy** (→ practical link to CPC Art. 429; rebuttable if challenged in time).

In practice: data message = written-document value; offered as *prueba libre*; printout = *fotostática*; judge weighs under **sana crítica / libre convicción**. The TSJ has admitted emails/digital records as evidence (Sala Político-Administrativa, 12-Feb-2008).

---

## 3. Plain vs. Certified Signature — Arts. 16 / 17 / 18 (the legal heart)

**Art. 16 — equivalence to a handwritten signature (THREE conditions), verbatim:**
> "La Firma Electrónica que permita vincular al Signatario con el Mensaje de Datos y atribuir la autoría de éste, tendrá la misma validez y eficacia probatoria que la ley otorga a la firma autógrafa. A tal efecto, salvo que las partes dispongan otra cosa, la Firma Electrónica deberá llenar los siguientes aspectos:
> 1. Garantizar que los datos utilizados para su generación puedan producirse sólo una vez, y asegurar, razonablemente, su confidencialidad.
> 2. Ofrecer seguridad suficiente de que no pueda ser falsificada con la tecnología existente en cada momento.
> 3. No alterar la integridad del Mensaje de Datos."

**Art. 17 — a non-compliant signature is still valuable, verbatim:**
> "La Firma Electrónica que no cumpla con los requisitos señalados en el artículo anterior no tendrá los efectos jurídicos que se le atribuyen en el presente Capítulo, sin embargo, podrá constituir un elemento de convicción valorable conforme a las reglas de la sana crítica."

→ It is **not void** and **not stripped of all value** — it loses *automatic* handwritten-equivalence but remains an "elemento de convicción" freely weighed by the judge. **The proponent bears the burden of proving authenticity/integrity.** This is the key risk provision for any "simple" signature.

**Art. 18 — certification = deemed compliance, verbatim:**
> "La Firma Electrónica, debidamente certificada por un Proveedor de Servicios de Certificación conforme a lo establecido en este Decreto-Ley, se considerará que cumple con los requisitos señalados en el artículo 16."

**Bottom line:**
- **Plain *firma electrónica*** (typed name, click-to-accept, scanned image, OTP) must *independently prove* the three Art. 16 conditions to equal a handwritten signature; if it can't → **Art. 17** (valid, judge's free appraisal).
- **Certified *firma electrónica*** (backed by a PSC *Certificado Electrónico*) is, by **Art. 18**, *automatically deemed* to meet Art. 16 → **handwritten equivalence + presumption of legitimacy**, no case-by-case proof.
- **Art. 19** imposes signatory duties (diligence to prevent misuse; notify the PSC).

---

## 4. SUSCERTE & Certification Service Providers (PSCs)

- **SUSCERTE** = *Superintendencia de Servicios de Certificación Electrónica*, created by the LMDFE in 2001 [Art. 20], competencies to accredit/supervise/control PSCs [Arts. 21–22]; currently **adscrita al Ministerio del Poder Popular para Ciencia y Tecnología (MINCYT)** *(ministry attachment has shifted over reorganizations)*. Operates the **Autoridad de Certificación Raíz del Estado** (Root CA, 2007).
- **Accredited PSCs:**
  - *Well-documented first accreditations (2008):* **Fundación Instituto de Ingeniería (FII)** — public PSC; **PROCERT, C.A.** — private PSC.
  - *Current roster (~6, one public + private):* recurring names include **FIIIDT** (public; successor of FII), **PROCERT** (now "PROCERT ITFB, C.A."), **Soluciones Tecnológicas Apacuana** (Gaceta 42.957/2024), **FirmeDigital PSC**, **Authenticsign**, possibly **Documentos Digitales PSC**. ⚠️ **Confirm the canonical current list at suscerte.gob.ve** — the SUSCERTE directory was unreachable during research.
  - **PROCERT intervention/sanction history: NOT FOUND / unverified** — could neither confirm nor deny; PROCERT appears active.
- **Obtaining a certified signature (illustrative, PROCERT):** request quote → choose certificate type → pay → submit docs → **in-person identity validation** → receive on **token/pendrive** (~5 business days). **Validity ≈ 1 year, renewable** (PSC practice; not a statutory term — see §5).
- ⚠️ DocuSign / Adobe Sign and similar are **not SUSCERTE-accredited PSCs** → in Venezuela they operate as **simple** signatures (Art. 16/17), not certified (Art. 18).

---

## 5. Electronic Certificate Requirements (Arts. 38–44)

- **Art. 38:** the *Certificado Electrónico* guarantees **authorship** + **integrity** — but does **NOT** confer notarial *fe pública*.
- **Art. 39:** **No fixed statutory validity term** — set by PSC–signatory agreement (hence the ~1-year practice).
- **Art. 40:** cancellation at signatory's request; must request on learning of misuse.
- **Art. 41:** voluntary temporary suspension.
- **Art. 42:** forced suspension/revocation causes (authority request, false data, breach, *Quiebra Técnica*); ceases on death/incapacity.
- **Art. 43 (mandatory contents):** (1) PSC identification; (2) PSC SUSCERTE code; (3) holder identification; (4) **validity start/expiry dates**; (5) signatory's electronic signature; (6) unique serial ID; (7) use limitations / liability info.
- **Art. 44:** foreign certificates valid only if guaranteed by an accredited Venezuelan PSC; otherwise → *sana crítica* only.

---

## 6. Practical Compliance for the School (control → statute)

To make an electronically signed enrollment contract **defensible in a Venezuelan court**:

- **Consent / acceptance:** capture an explicit, logged "Acepto / Firmar" event showing the exact contract version + a **separate T&C acceptance** [Art. 16 chapeau].
- **Identity verification:** **OTP** (SMS/email) to the parent's registered contact + **display the signer's cédula inside the document** [Art. 16].
- **Integrity / tamper-evidence:** store a **cryptographic hash** (ideally a **trusted timestamp / sello de tiempo**) of the final PDF [Art. 7 — integrity / original form].
- **Audit trail / metadata:** record **IP + date/time** of each step [Art. 8(3)].
- **Conservation / retention:** keep the signed data message **retrievable, in original (or faithfully reproduced) format, with metadata**, for the retention period; Art. 8 allows **outsourcing archival**. Keep both the electronic original and a printout [Art. 8; Art. 4 ¶3].
- **Completion certificate:** retain the platform's signature/audit-trail certificate with the contract.

> **Article mapping (corrected):** *reproduction* = **Art. 4 ¶3**; *integrity / original form* = **Art. 7**; *conservation / retention* = **Art. 8**.

---

## 7. Limitations / Exclusions

- **Art. 6 (permission, not prohibition):** where the law requires a *writing* or *firma autógrafa*, that is satisfied by a data message + electronic signature; solemnities "podrán realizarse" through the law's mechanisms.
- **The LMDFE contains NO catalogue of excluded acts** (Bentata: "does not establish specific exclusions").
- **The real limit:** acts requiring **notarial authentication (notaría) or registration (registro público / mercantil / inmobiliario)** run under the **LRN** (Arts. 2 & 68) — a *private* certificate does **not** confer *fe pública* [Art. 38]. So real-estate transfers, mortgages, company formation, certain powers can't get notarial/registral effect from a private e-signature alone.
- **Solemn family-law acts** (marriage, divorce, adoption) still require physical appearance *(practice-level, lower confidence)*.
- **Non-certified e-signatures in court:** **valid and binding between the parties** but **no presumption of authenticity** — judged under *sana crítica* [Art. 17], often as a *principio de prueba por escrito* needing corroboration. **Enrollment / adhesion / service contracts can validly be concluded electronically** — no statutory bar found *(inference; no source addressed school adhesion contracts expressly)*.

---

## 8. Risk Assessment & Recommendation for UEIPAB

| | (a) Firma electrónica **simple** (click-to-accept / typed / scanned / OTP) | (b) Firma electrónica **certificada** (SUSCERTE PSC) |
|---|---|---|
| Legal basis | Art. 17 — valid, no automatic equivalence | Art. 18 → 16 — equal to handwritten |
| Evidentiary value | *Sana crítica*; **school bears burden** of proving authenticity/integrity | **Presumption** of legitimacy; burden shifts to challenger |
| Cost / friction | Low; instant; no per-parent PSC enrollment | Higher; per-signer token + in-person ID; ~1-yr cert |
| Fit for high-volume enrollment | High | Low (impractical to certify every family) |

**Recommended pragmatic approach:**
1. **Default (Tier 2): firma electrónica simple + the full compensating-control bundle** — explicit logged consent + separate T&C acceptance + **OTP** + **cédula shown in the document** + **IP + timestamp** + **integrity hash (+ trusted timestamp)** + retained data message + audit/completion certificate. These are exactly the elements that let a judge credit the signature under *sana crítica*.
2. **Tier 1 (optional, highest-stakes clauses):** route payment-default / legal-action clauses, or anything you expect to litigate, through a **SUSCERTE-accredited PSC (PROCERT / FIIIDT)** for the Art. 18 presumption.
3. **Don't assume *fe pública*:** ordinary enrollment contracts need no notarization, but a private e-signature never confers it [Art. 38].
4. **Consumer disclosure:** parents are consumers — present clear prior disclosure (price, terms, what's accepted) and retain the informed-consent screen.

**Applied to our stack:** our `partner.communication.ack` / notice-ACK pattern (token route + **SQL-stored ACK** + CC `recursoshumanos@`) already captures the spine of a Tier-2 simple signature. To harden it for enrollment contracts, add: **IP + user-agent + UTC timestamp** capture on the ACK POST, **OTP** identity step, **cédula rendered inside the PDF**, an **integrity hash** of the exact PDF version accepted, and **retention** of the accepted data message + audit certificate. This keeps high-volume enrollment frictionless while maximizing Art. 17 defensibility.

---

## Flagged Uncertainties & Source Conflicts

1. **Art. 16 = THREE conditions, not four** (certificate-deeming = Art. 18; signatory control = Art. 19). *High confidence — verbatim ×2.*
2. **Mapping:** reproduction = Art. 4 ¶3; integrity = Art. 7; conservation = Art. 8. *High confidence.*
3. **Decree N° 1.204** (not "1.024" typo). Gaceta 37.148 / 28-Feb-2001 consistent.
4. One outlier promulgation citation (G.O. 37.076, 13-Dec-2000) = likely sanction vs. publication date; official = G.O. 37.148.
5. **Certificate validity:** no fixed statutory term (Art. 39); "1 year" is PSC practice.
6. **PROCERT intervention/sanction: unverified.**
7. **Current canonical PSC list not locked** (SUSCERTE directory unreachable) — confirm at source.
8. Doctrinal split on a bare printout's weight (TSJ RC.212/2022 vs. critics).
9. Viafirma's "no simple signature in Venezuela" conflicts with Art. 17 — treat as marketing oversimplification.
10. Several primary sources (suscerte.gob.ve PDF, oas.org, some TSJ URLs) were unreachable; article texts verified against Justia Gaceta-PDF + UC reproduction (verbatim agreement). Re-confirm against official SUSCERTE/Gaceta PDF for any court filing.
11. Infogobierno Art. 24 and LRN Arts. 2/68 cross-checked against single sources — medium confidence on exact numbers.
12. Adhesion/consumer-contract specifics are inferential.

---

## Sources

- Asamblea Nacional — Decreto N° 1.204: https://www.asambleanacional.gob.ve/leyes/sancionadas/decreto-no-1204-con-rango-y-fuerza-de-ley-de-mensajes-de-datos-y-firmas-electronicas
- Justia / Gaceta — Decreto N° 1.204 full-text PDF (verbatim Arts. 1–49): https://docs.venezuela.justia.com/federales/decretos/decreto-n-1-204.pdf
- Universidad de Carabobo, Rev. Derecho (idc24/24-14) — full law + Exposición de Motivos: https://servicio.bc.uc.edu.ve/derecho/revista/idc24/24-14.pdf
- Pandectas Digital — full law (HTML): https://pandectasdigital.blogspot.com/2016/08/ley-de-mensaje-de-datos-y-firmas.html
- CONALOT — Reglamento Parcial (Decreto 3.335 / G.O. 38.086): https://www.conalot.gob.ve/2018/05/18/decreto-no-3335-reglamento-parcial-del-decreto-ley-sobre-mensajes-de-datos-y-firmas-electronicas/
- SUSCERTE — ¿Quiénes Somos?: https://www.suscerte.gob.ve/?page_id=142
- MINCYT — SUSCERTE ente rector: https://mincyt.gob.ve/suscerte-ente-rector-y-regulador-de-la-seguridad-informatica-en-el-pais/
- Silva Dugarte (2011), "Certificación electrónica aplicada en Venezuela" (redalyc): https://www.redalyc.org/pdf/4655/465545890006.pdf
- PROCERT: https://www.procert.net.ve/
- SciELO — TSJ SPA 12-Feb-2008 (Art. 4): https://ve.scielo.org/scielo.php?script=sci_arttext&pid=S1315-62682008000300012
- Grupo Veritas Lex — valor probatorio (CPC Art. 429): https://grupoveritaslex.com/blog/valor-probatorio-de-los-mensajes-electronicos-de-datos-segunda-parte-1592
- Nayma Consultores — valor probatorio de correos (RC.212/2022): https://naymaconsultores.com/valor-probatorio-de-los-correos-electronicos-venezuela/
- Victum Legal — Utility of Electronic Signatures in Venezuela: https://victum.legal/en/utility-of-electronic-signatures-in-venezuela/
- Bentata — formalidades contractuales en la era digital (LRN, exclusions): https://bentata.com/es/de-la-des-formalizacion-material-a-la-re-formalizacion-digitallas-formalidades-contractuales-en-la-era-digital/
- Asilo Digital — Firma electrónica/digital en Venezuela: https://www.asilodigital.com/firma-electronica-digital-venezuela/
- Viafirma — Electronic signature in Venezuela (FAQ): https://www.viafirma.com/en/faqs/electronic-signature-in-venezuela/
- Soluciones Tecnológicas Apacuana (PSC, Gaceta 42.957/2024): https://www.apacuana.com/
- FirmeDigital PSC: https://firmedigital.com/
