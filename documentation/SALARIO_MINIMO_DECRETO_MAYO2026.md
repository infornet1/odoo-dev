# Decreto Ingreso Mínimo Integral $240 — Análisis de Impacto Salarial (Mayo 2026)

**Fecha del Decreto:** 30 de abril de 2026 (retroactivo)
**Anunciado por:** Presidenta Encargada Delcy Rodríguez (Día del Trabajador)
**Incremento:** +26.3% respecto al monto anterior (~$190 USD)
**Análisis realizado:** 1 de mayo de 2026
**PDF ejecutivo:** `/home/ftpuser/odoo-dev/Analisis_Impacto_Salarial_Mayo2026.pdf`

---

## Estructura del Decreto

| Componente | Monto (USD) | Notas |
|---|---|---|
| **Bono de Guerra Económica** | $199.73 | Componente mayoritario, indexado BCV |
| **Cestaticket Alimentario** | $40.00 | Sin incidencia salarial (LOTTT) — **sin cambio** |
| **Salario Mínimo Base** | $0.27 | Bs. 130 — congelado desde marzo 2022 |
| **TOTAL Ingreso Mínimo Integral** | **$240.00** | Mensual en USD equivalente |

**Nota legal:** El Cestaticket es no remunerativo — no incide en prestaciones sociales, vacaciones, utilidades ni indemnizaciones por despido.

---

## Metodología del Análisis

- **Universo:** 44 empleados activos con contrato `open/pending`
- **Excluidos:** Alberto Perdomo (contrato de prueba, $4), María Jiménez (estructura V1 independiente), Gustavo Perdomo (Dirección)
- **Campo de comparación:** `wage` en `hr.contract` = `ueipab_salary_v2` + `ueipab_bonus_v2` + `ueipab_extrabonus_v2` + `cesta_ticket_usd` (~$40)
- **Cestaticket actual:** $40.00 por empleado (`cesta_ticket_usd` en cada contrato) — coincide exactamente con el decreto

---

## Empleados por Debajo del Umbral $240 — Acción Inmediata

| Empleado | Salario V2 | Bono V2 | Extra V2 | Cesta Ticket | **Total** | **Gap** |
|---|---|---|---|---|---|---|
| LUIS RODRIGUEZ | $95.69 | $55.69 | $0.00 | $40.00 | **$191.37** | **+$48.63** |
| NIDYA LIRA | $105.23 | $83.44 | $0.00 | $40.00 | **$228.67** | **+$11.33** |

**Ajuste mensual requerido:** $59.96  
**Impacto anualizado:** $719.52

### Acción recomendada

Incrementar `ueipab_bonus_v2` en cada contrato:

| Empleado | Bono V2 actual | Bono V2 objetivo | Incremento |
|---|---|---|---|
| LUIS RODRIGUEZ | $55.69 | $104.32 | +$48.63 |
| NIDYA LIRA | $83.44 | $94.77 | +$11.33 |

Aplicar con retroactividad al 30 de abril de 2026. Reemitir comprobantes de nómina correspondientes.

---

## Empleados en Banda de Riesgo ($240–$300) — 9 Empleados

Cumplen actualmente pero con margen ajustado. Vulnerables ante un próximo ajuste.

| Empleado | Total Actual | Margen sobre $240 |
|---|---|---|
| MARIELA PRADO | $250.03 | $10.03 |
| ZARETH FARIAS | $250.03 | $10.03 |
| LEIDYMAR ARAY | $268.86 | $28.86 |
| AUDREY GARCIA | $270.39 | $30.39 |
| Jesus Di Cesare | $271.87 | $31.87 |
| ROBERT QUIJADA | $271.87 | $31.87 |
| PABLO NAVARRO | $277.45 | $37.45 |
| MIRIAN HERNANDEZ | $287.25 | $47.25 |
| ANDRES MORALES | $289.11 | $49.11 |

**Prioridad en siguiente ronda salarial:** MARIELA PRADO y ZARETH FARIAS (buffer de solo $10.03).

---

## Distribución General (44 empleados)

| Banda | Cantidad | Estado |
|---|---|---|
| Bajo $240 | 2 | No conforme — ajuste urgente |
| $240–$300 | 9 | Conforme — margen ajustado |
| $300–$400 | 25 | Conforme |
| $400–$600 | 8 | Conforme — holgura amplia |

---

## Retroactividad

El decreto establece vigencia retroactiva al 30 de abril de 2026. Evaluar con el área legal si el ajuste para LUIS RODRIGUEZ y NIDYA LIRA se emite como pago complementario a la quincena de abril, o se absorbe en la nómina de mayo con nota explicativa.

---

## Estado de Cumplimiento del Cestaticket

El valor actual de `cesta_ticket_usd` en todos los contratos es **$40.00**, coincidiendo exactamente con el Cestaticket del decreto. **No se requiere ningún ajuste en este componente.**
