# Customers Sheet vs Odoo Contact Email Sync — Pending Task

**Status:** Pending Analysis | **Date:** 2026-02-09 | **Priority:** Medium

## Context

The Google Spreadsheet "Customers" tab is the CEO's dynamic report. Column J (email) should reflect Odoo's `res.partner.email` for contacts tagged as "Representante" or "Representante PDVSA". Discrepancies were discovered during resolution bridge development.

**Spreadsheet:** `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`
**Tab:** `Customers` (rows 3-192)
**Matching:** Column A (VAT) = `res.partner.vat`, Column J (email) = `res.partner.email`

## Comparison Results (2026-02-09)

| Metric | Count |
|--------|-------|
| Matched (identical emails) | 117 |
| **Email mismatches** | **55** |
| In sheet but no Odoo Representante tag | 18 |
| In Odoo but not in sheet | 143 |

## Mismatch Classification

### Category A — Odoo has MORE emails than sheet (11 cases)

Odoo accumulated extra emails via Glenda/bounce resolution. Sheet is behind.

**Recommended action:** Add Odoo's extra emails to sheet (SAFE — additive only)

| Row | Name | VAT | Sheet Email | Odoo Adds |
|-----|------|-----|-------------|-----------|
| 7 | AMADA MELENDEZ | V8516898 | amadamelendez26@gmail.com | lajimenez@ueipab.edu.ve |
| 8 | AMBAR PARRA | V20172974 | ambarhel@gmail.com | santiagoaldana2021@gmail.com |
| 9 | AMIRA KHATIB | V12016103 | kamira1975@hotmail.com | amirakhatib1975@gmail.com |
| 21 | ANTONIO MARTINEZ | V15846797 | antonyfeli5@gmail.com | neumo.martinez@gmail.com |
| 39 | CASTO GONZALEZ | V13031325 | marianyicastellanos@gmail.com | gonzalezcju2543@gmail.com |
| 53 | DOALBERT NUNEZ | V19642609 | franhielys@gmail.com | doalbert@gmail.com;franhielysflores@gmail.com |
| 69 | GLORIA MILLAN | V17263838 | millangloria86@gmail.com | damarinm@ueipab.edu.ve |
| 114 | MARIA BOMPART | V10936221 | Bompartt@yahoo.es | bompartt70@gmail.com |
| 162 | VANESSA BRITO | V15845247 | vanessa.dbv@gmail.com | viloriafabianna@gmail.com |
| 163 | VANESSA HERNANDEZ | V19939485 | vanehdezmarchan@gmail.com | hdezvane90@gmail.com;vanehdez90@gmail.com |
| 173 | YOICIS NUNEZ | V14029000 | nunezyoicis05@gmail.com | yoicis@hotmail.com |

### Category B — Sheet has MORE emails than Odoo (12 cases)

Sheet has extra emails from manual admin entry. Odoo doesn't know about them.

**Recommended action:** Add sheet's extra emails to Odoo (SAFE — preserves admin work)

| Row | Name | VAT | Odoo Email | Sheet Adds |
|-----|------|-----|------------|------------|
| 45 | DANIEL DOMINGUEZ | V17592159 | domin.anuel0608@gmail.com | nanidomin9@gmail.com |
| 58 | EDUARDO RANGEL | V14839661 | eduardo.jose.rangel79@gmail.com | nathaliavilla04@gmail.com |
| 65 | ERICK MONTILLA | V16150141 | erickmontilla21@gmail.com | genesisg.guelia@gmail.com |
| 67 | FREDDY GONZALEZ | V12681646 | freddyaquiles@gmail.com | cpcnataliavillagran@gmail.com |
| 73 | ILDEMARO ARRIOJA | V15934607 | ildemaroarrioja@gmail.com | ildemaro.arrioja@gmail.com;mariaroapo@gmail.com |
| 76 | IRIANA MACHADO | V17590801 | machadoiriana@hotmail.com;jesusalfonzo@gmail.com | jesusalfonzoa@gmail.com |
| 86 | JORGE MARTINEZ | V18144268 | martinez.jorge53@gmail.com | emighely@gmail.com |
| 92 | JOSE TABASCA | V12017339 | josetabask1975@gmail.com | mariangelamfx198032@gmail.com |
| 113 | MARIA APONTE | V18478620 | apontemarivict@gmail.com;apontemb@pdvsa.com | apontemarivic@gmail.com |
| 147 | RAUL OSUNA | V12857464 | raulosunan@gmail.com | lisbeth.campos.0408@gmail.com |
| 157 | SARELY BELLORIN | V14641839 | sarely_bellorin28@hotmail.com | sarelybellorin@gmail.com |
| 165 | VIRGILIO CASTRO | V13920446 | plazmisle@gmail.com | misleflores@gmail.com;vircaso@gmail.com |

### Category C — Completely different emails (26 cases)

Both systems have emails the other doesn't. Requires manual human review.

**Recommended action:** Merge both sets (union), then flag for admin review to prune duplicates.

| Row | Name | VAT | Sheet Email | Odoo Email |
|-----|------|-----|-------------|------------|
| 24 | ARGENIS GARCIA | V12679838 | garciaadc@gmail.com;figuerahd@gmail.com | imgarciaf@ueipab.edu.ve;figuerahd@gmail.com |
| 28 | BENITO TORREALBA | V17950206 | benito.torrealba@gmail.com;karla.gueli@gmail.com | kamila.gueli10@gmail.com |
| 46 | DANIEL VASQUEZ | V17237134 | ercilia.ulloa@gmail.com;daniel.vasquez25@gmail.com | danielvasquezulloa7@gmail.com |
| 48 | DANIELA VILLAMIZAR | V20741717 | danielavillamizarc@gmail.com | arantzavsuberov@gmail.com |
| 50 | DAVID EVANS | V14133887 | davidjevansmt@gmail.com | deiversonevans@gmail.com |
| 59 | ELIAS MUNOZ | V17010349 | eliasjose30@gmail.com;odaguis@gmail.com | odalysam86@gmail.com |
| 61 | ELVIRA MATA | V18228721 | elviramatamqz@gmail.com | miamm0605@gmail.com;elviram511@gmail.com |
| 70 | GREGORY PEREIRA | V12873319 | rubneida@gmail.com | pereirago@gmail.com |
| 79 | JEAN CARLOS SEQUEA | V13498322 | yina1901rodriguez@gmail.com | fernando1900sequea@gmail.com |
| 83 | JESUS RODRIGUEZ | V17847406 | tillerotatiana@gmail.com | jesusr.18@gmail.com |
| 87 | JOSE CONTRERAS | V17203685 | bianessy29@gmail.com | joseangelcontrerasl@gmail.com |
| 88 | JOSE ESCALONA | V12632403 | jhescalona12@gmail.com | escalonadanieljonas@gmail.com |
| 89 | JOSE OLIVIER | V15127992 | johanaquilarquez@gmail.com | rrolivier@ueipab.edu.ve |
| 90 | JOSE RODRIGUEZ | V18595666 | jr1805173@gmail.com | lebrigarodriguez@gmail.com |
| 93 | JOSMAR FIGUEROA | V15846608 | ramsoj18@gmail.com;adrianamarfer@gmail.com | ramsoj18@hotmail.com |
| 98 | KARLA SANCHEZ | V13657191 | karlimer78@gmail.com | jfcedeno@ueipab.edu.ve |
| 111 | MAILIN SUAREZ | V13610528 | maisuarezb@gmail.com | ceacosta@upipab.edu.ve |
| 118 | MARIA NIETO | V13919491 | ybagnieto8@gmail.com | maria.nieto@ueipab.edu.ve |
| 124 | MERLYS BARRIOS | V14817110 | mgbgcolegio@gmail.com | fiorelladlamb@gmail.com |
| 144 | RAIZA RENDON | V12914780 | raizajrendon@gmail.com | franklinzorrilla2016@gmail.com |
| 149 | ROBERTO VERA | V14132410 | robertovera365@outlook.com;yamelsancheztellechea@gmail.com | yamelsancheztellechesa@gmail.com |
| 153 | ROSALIA YANEZ | V16572749 | yanezrosalia429@gmail.com | isa.fuen2603@gmail.com |
| 169 | YENNY FAJARDO | V15637834 | yenseryenny@gmail.com | yenseryenny@hotmail.com |
| 170 | YENNY ROJAS | V14132251 | kityangeles@gmail.com | yaperdomo@ueipab.edu.ve |
| 175 | YOSLYN BENAVIDES | V14726350 | romaneduardo53@gmail.com | ybenavides8@gmail.com |
| 176 | ZHEN CHING | V20335821 | Lisa71736@gmail.com;yamilatabete1@hotmail.com | lianghaiying1984@gmail.com |

**Notable patterns in Cat C:**
- Row 149 ROBERTO VERA: `yamelsancheztellechea` vs `yamelsancheztellechesa` — likely a typo
- Row 169 YENNY FAJARDO: `@gmail.com` vs `@hotmail.com` — same user, different provider
- Several cases have `@ueipab.edu.ve` in Odoo (institutional) vs personal gmail in sheet — may be different parents (father vs mother)

### Category D — Odoo empty, sheet has email (6 cases)

Odoo lost the email during bounce cleanup (permanent failure removed it). Sheet preserved the original.

**Recommended action:** Restore sheet's email to Odoo (SAFE — restores lost data)

| Row | Name | VAT | Sheet Email |
|-----|------|-----|-------------|
| 3 | ADRIANGELA CANDIAGO | V19964384 | adriangelacandiago16@gmail.com |
| 19 | ANMIRTH VARGAS | V14015755 | 1303anmirth@gmail.com |
| 94 | JOYCE MOGOLLON | V17008520 | mogollonjoy@gmail.com |
| 130 | NATACHA HERNANDEZ | V19939143 | nchleotaud@gmail.com |
| 155 | RUTHBELIS MARIN | V13610559 | mruthd2@gmail.com |
| 178 | ANNA QUINTERO | V14805636 | karinaquintero219@gmail.com |

## Recommended Strategy

**MERGE approach — neither source overwrites the other:**

| Phase | Action | Count | Automation |
|-------|--------|-------|------------|
| 1 | Cat A: Add Odoo extras → Sheet | 11 | Auto-safe |
| 2 | Cat B: Add Sheet extras → Odoo | 12 | Auto-safe |
| 3 | Cat D: Restore Sheet email → Odoo | 6 | Auto-safe |
| 4 | Cat C: Merge union + flag for review | 26 | Semi-auto (merge) + manual (review) |
| **Total** | | **55** | **29 auto + 26 review** |

## Additional Gaps

- **18 contacts** in Sheet without Representante tag in Odoo — may need tag assignment
- **143 Odoo Representante contacts** not in Sheet rows 3-192 — Sheet may need expansion

## Impact on Glenda

Email consistency between Odoo and the Sheet directly affects:
- **Bounce detection accuracy** — if Sheet has a stale email, bounces may not be linked correctly
- **Resolution completeness** — resolution bridge updates Sheet, but only for emails it knows about
- **CEO reporting** — Sheet should reflect the operational truth for management visibility

## Next Steps

- [ ] Decide on merge strategy (approve/modify the recommended approach above)
- [ ] Build sync script with dry-run safety
- [ ] Run Cat A+B+D (29 auto-safe merges)
- [ ] Review Cat C (26 manual cases) with admin/Alejandra
- [ ] Decide on the 18 untagged + 143 missing contacts scope
