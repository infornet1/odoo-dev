# Venezuelan Labor Compensation Analysis (LOTTT)
**Business Logic & Arithmetic Formulas for Python Implementation**

## 1. Executive Summary
This document outlines the arithmetic rules required to compute *Prestaciones Sociales*, *Intereses*, *Utilidades*, and *Vacaciones* under the *Ley Orgánica del Trabajo, los Trabajadores y las Trabajadoras* (LOTTT).

**Key Architectural Concept:** The calculation requires a "Dual-path" evaluation (Guarantee vs. Retroactive) to determine the final payable amount.

---

## 2. Data Dictionary & Variables

The following variables act as the input attributes for the `Employee` class in the Python script.

| Symbol | Variable Name | Definition | Note |
| :--- | :--- | :--- | :--- |
| $t$ | **Antigüedad** (Tenure) | Time delta ($End\_Date - Start\_Date$) | Calculated in Years, Months, Days. |
| $S_n$ | **Salario Normal** | Monthly base remuneration. | Excludes *Cestaticket* and non-regular bonuses. |
| $S_i$ | **Salario Integral** | $S_n$ + Daily Aliquots of Utilities & Vacation Bonus. | **The basis for Prestaciones.** |
| $D_u$ | **Días de Utilidades** | Profit sharing days (Min: 30, Max: 120). | Defined by contract or law. |
| $D_{bv}$ | **Días Bono Vac.** | Vacation Bonus days ($15 + 1$ per year of service). | Capped at 30 days total. |
| $R_{bcv}$| **Tasa BCV** | Interest rate set by Central Bank. | Monthly variable rate. |

---

## 3. The "Salario Integral" Algorithm
*Prestaciones Sociales* are calculated based on the **Integral Salary**, not the Normal Salary. This value must be recalculated dynamically as tenure increases (because the Vacation Bonus aliquot grows with time).

### The Formula
$$S_i = S_n + \text{Aliquot}_u + \text{Aliquot}_{bv}$$

### Breakdown
1.  **Daily Normal Salary ($SD_n$):**
    $$SD_n = S_n / 30$$
2.  **Utilities Aliquot ($A_u$):**
    $$A_u = (SD_n \times D_u) / 360$$
3.  **Vacation Bonus Aliquot ($A_{bv}$):**
    $$A_{bv} = (SD_n \times D_{bv}) / 360$$
4.  **Daily Integral Salary ($SD_i$):**
    $$SD_i = SD_n + A_u + A_{bv}$$

---

## 4. Core Logic: Prestaciones Sociales (Article 142)
The system must compute two methods and pay the **higher** result.

### Method A: The Guarantee (Garantía - Trimestral)
This accumulates quarterly.
* **Frequency:** Calculated every 3 months of service.
* **Base:** 15 days of $SD_i$ (calculated at the value *of that specific quarter*).
* **Additional Days:** After the 1st year, add 2 days per year (cumulative) to the guarantee.
* **Logic:**
    $$Guarantee = \sum_{q=1}^{quarters} (15 \times SD_{i\_at\_quarter}) + \text{Additional Days}$$

### Method B: The Retroactive (Retroactivo)
This is calculated once at termination.
* **Frequency:** End of relationship only.
* **Base:** 30 days per year of service (or fraction > 6 months).
* **Value:** Calculated using the **Final/Last** $SD_i$.
* **Logic:**
    $$Retroactive = (30 \times Years) \times SD_{i\_final}$$

### Comparison (The Decision Gate)
$$Final\_Payable = \max(Guarantee, Retroactive)$$

---

## 5. Interest on Trust (Intereses sobre Prestaciones)
Interest is calculated monthly on the accumulated "Guarantee" fund (Method A).

* **Principal:** The sum of Method A up to Month $M-1$.
* **Rate:** BCV Rate (Active or Average). Usually annualized.
* **Formula:**
    $$Interest_{month} = \frac{Accumulated\_Fund \times Rate_{BCV}}{100 \times 12}$$

---

## 6. Vacation & Vacation Bonus (Liquidación)
If these are pending payment at termination. Note that usually, these are paid based on **Normal Salary** ($SD_n$), depending on the specific interpretation of the law, though some interpretations argue for Integral. **Standard practice uses Normal.**

* **Vacation Days:** $15 + (Years - 1)$ (Max 15 additional).
* **Bonus Days:** $15 + (Years - 1)$ (Max 30 total).
* **Formula:**
    $$Total\_Vacation\_Pay = (Days_{vacation} + Days_{bonus}) \times SD_n$$

---

## 7. Python Implementation Requirements

To script this effectively, the Python architecture requires:

1.  **`SalaryHistory` Class:** A list of dictionaries `[{date, amount}]` to handle inflation/raises.
2.  **`TimeEngine`:** A helper to calculate precise quarters and "fractions > 6 months".
3.  **`BCV_Loader`:** A lookup table for historical interest rates.
4.  **`Calculator`:** The main logic that iterates through the timeline, updates $S_i$ dynamically, and sums the guarantee.