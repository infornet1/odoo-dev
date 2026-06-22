# Annual Report 2025–2026 — Content Skeleton Draft

**Status:** DRAFT skeleton · **Created:** 2026-06-22 · Companion to
[ACADEMIC_ANNUAL_REPORT_2025_2026.md](ACADEMIC_ANNUAL_REPORT_2025_2026.md)

Fill-in copy for the report page while the CEO gathers/locates the real data.
**Convention:** `[[ ... ]]` = placeholder to replace · *(nota)* = editorial note ·
Spanish = parent-facing copy (goes on the page) · English = internal guidance.

---

## A. Mensaje de la Dirección (Scene 2)

*(~120–150 words, warm + credible, signed by the CEO. Draft below — edit freely.)*

> **Estimadas familias del Andrés Bello:**
>
> Cerramos el año escolar **2025–2026** con el corazón lleno de gratitud y de
> orgullo. Este fue un año en el que nuestra comunidad demostró, una vez más, que
> la **excelencia académica** y la **formación en valores** caminan juntas.
>
> Vimos a nuestros estudiantes brillar [[en lo académico, lo deportivo y lo
> tecnológico]] —desde [[el oro regional en robótica Kurios]] hasta [[logro 2]] y
> [[logro 3]]—, y dimos un paso firme hacia el futuro con la llegada de **Glenda**,
> nuestra asistente de inteligencia artificial al servicio de cada familia.
>
> Nada de esto sería posible sin **ustedes**. Gracias por confiar en nuestro
> proyecto educativo. Con esa misma confianza, los invitamos a **reafirmar su
> continuidad** para el año **2026–2027** y seguir construyendo juntos.
>
> Con aprecio,
> **[[Nombre del Director / Gustavo Perdomo]]**
> *[[Cargo]] — Instituto Privado "Andrés Bello"*

*(Note: swap the bracketed achievements once §C is filled; keep it to one screen
on mobile.)*

---

## B. Nuestro año en números (Scene 3)

Stat band — 4 to 8 counters. **Pre-filled = internal estimates, VERIFY before
publishing; `[[ ]]` = still needed.**

| Métrica | Valor | Estado |
|---------|-------|--------|
| Estudiantes atendidos | `[[~207]]` | ⚠️ verify (budget matrix) |
| Docentes y personal | `[[~43]]` | ⚠️ verify (payroll) |
| Graduandos 2025–2026 | `[[__]]` | ⏳ needed |
| % de aprobación / promoción | `[[__ %]]` | ⏳ needed |
| Equipos en robótica Kurios | **7** | ✅ confirmed |
| Medallas / reconocimientos | `[[__]]` (oro Desafío 14 ✅) | ⏳ tally |
| Años de trayectoria | `[[__]]` | ⏳ needed |
| Eventos / actividades realizadas | `[[__]]` | ⏳ needed |

*(Pick the 4–6 strongest for the band; park the rest. Avoid publishing any number
we can't stand behind — better fewer, solid stats than many soft ones.)*

---

## C. Los 3 Momentos Académicos (Scene 4)

Three-block timeline (reuse the enrollment-journey block style). One card per
lapso. **All placeholders ⏳ — fill per momento.**

### I Momento — `[[Sep–Dic 2025]]`
- **Tema / enfoque:** `[[ej. adaptación, diagnóstico, arranque de proyectos]]`
- **Hitos:**
  1. `[[hito 1]]`
  2. `[[hito 2]]`
  3. `[[hito 3]]`
- **Foto(s):** `[[archivo(s) — subir a /flyers/partners/ o /flyers/annual/]]`

### II Momento — `[[Ene–Mar 2026]]`
- **Tema / enfoque:** `[[ ... ]]`
- **Hitos:** `[[1]]` · `[[2]]` · `[[3]]`
- **Foto(s):** `[[ ... ]]`

### III Momento — `[[Abr–Jul 2026]]`
- **Tema / enfoque:** `[[cierre, robótica Kurios, graduación]]`
- **Hitos:**
  1. **Oro regional en robótica Kurios — Desafío 14** ✅ *(ya tenemos media)*
  2. `[[hito 2]]`
  3. `[[graduación / acto de cierre]]`
- **Foto(s):** Kurios ✅ (`/flyers/kurios/`) + `[[otras]]`

*(Photos for the report go under a new `/var/www/dev/flyers/annual/` folder —
keep partner logos in `partners/` separate from scene photos.)*

---

## D. Historias que nos enorgullecen (Scene 5)

- **Robótica Kurios** ✅ — oro Desafío 14 (Isaac Carrillo · Jadasa Mayz · Andrés
  Córdoba) + los 7 equipos. Media ready in `/flyers/kurios/`. Reuse recap copy.
- **Olimpiadas ORM (lengua y matemática)** — `[[resultados/participantes, vía
  Motores por la Paz]]`. ⏳ needed.
- `[[Otro logro académico / proyecto STEAM / deportivo / cultural]]` ⏳

---

## E. Innovación: Glenda (Scene 6)

*(Benefits, not tech. Draft — edit.)*

> Este año dimos la bienvenida a **Glenda**, nuestra **asistente de inteligencia
> artificial**, disponible para acompañar a cada familia **24/7** por
> **WhatsApp** y **Telegram**: responde dudas sobre **pagos**, **información
> académica** e **inscripciones**, al instante y con un trato cercano. Somos
> [[de las primeras instituciones de la región]] en poner la IA al servicio
> directo de nuestros representantes.

*(See GLENDA_AI_AGENT_OVERVIEW.md. Confirm the "primeras de la región" claim
before publishing.)*

---

## F. Mirando al 2026–2027 + CTA (Scenes 8–9)

- **Vision line:** `[[1–2 frases de visión para el próximo año]]` ⏳
- **Early-bird / continuidad framing:** tie to pricing ground truth (promo hasta
  31 jul 2026). *(Pull live rates from `sale.order.get_pricing_ground_truth()` —
  never hard-type prices.)*
- **CTA button:** "Reafirmar mi continuidad →" → each parent's
  `/enrollment-journey/<token>` (per §4 of the design doc).

---

## Open data requests (checklist for CEO)

- [ ] Director's letter — approve/edit draft §A (+ confirm signer name/title).
- [ ] Year-in-numbers — fill/verify §B figures.
- [ ] 3 momentos — themes + hitos + photos per lapso §C.
- [ ] ORM olympics results §D.
- [ ] Confirm Glenda "primera de la región" claim §E.
- [ ] Vision line + early-bird framing §F.
- [ ] Scene photos → upload to `/var/www/dev/flyers/annual/`.
