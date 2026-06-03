# Attendance Employee Guide — Concept & Email Template

**Status:** 🟡 DRAFT — Ready for CEO review before deployment  
**Version:** 0.3  
**Created:** 2026-05-29  
**Owner:** RRHH / Administración

---

## 1. Why This Guide Exists

The daily attendance alert system is generating friction. Employees — particularly teachers — are perceiving automated emails as surveillance rather than as a tool that works in their favor. The Yudelys Brito incident (2026-05-29) is the clearest example: she received a legitimate alert for a genuine technical issue, but instead of using the correction button (the correct path), she wrote a formal letter citing LOTTT articles 79 and 156.

**Root cause:** No employee was ever told what the system is for, who it protects, and what to do when something looks wrong.

**Goal of this guide:** Send a single warm, scenario-based email to all staff — before or immediately after the biweekly report system is fully live — that reframes the tool from "RRHH is watching you" to "you now have a transparent record that protects you."

The CEO's framing is the right one: every serious organization in the world tracks attendance for payroll integrity. The guide leans into that, gently, without being condescending.

---

## 2. Framing Philosophy

| What NOT to say | What to say instead |
|----------------|-------------------|
| "El sistema detecta anomalías" | "El sistema te avisa si algo no coincide" |
| "Incidencias en tu asistencia" | "Revisemos juntos tu registro" |
| "Debes registrar correctamente" | "Tu registro es tu respaldo ante cualquier duda" |
| "Corrección sujeta a aprobación" | "Si algo no cuadra, tienes hasta el cierre de nómina para explicarlo" |

**Tone:** Warm, collegial, institutional but human. Like a note from the director to a colleague, not an HR policy document.

---

## 3. Simulation Scenario (Yudelys Case as Template)

The guide includes one concrete walkthrough — anonymized but clearly recognizable as "a real situation that happened here." It shows:

1. Employees arrives on time but kiosk had a connectivity issue → system records late
2. That morning or the next day, employee receives the daily alert email
3. Employee clicks **"📝 Solicitar Corrección"** in the email
4. Fills in: arrival time + brief explanation of what happened
5. HR receives the request → reviews → approves → record corrected before payroll closes

**What the guide explicitly names as the wrong path:** Writing a formal complaint without first using the correction channel. Not because it's forbidden, but because the correction system is faster, easier, and resolves the issue in hours rather than days.

---

## 4. Draft Email Template (HTML)

This template is intended as a standalone one-time blast to all staff (`mail.mail` XML-RPC, queue via cron id=3). Subject line and body below.

**Subject:** Tu registro de asistencia — cómo funciona y cómo te protege

```html
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f0f4fa;">
<div style="background:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#1a2c5b,#2471a3);padding:28px;text-align:center;">
    <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"
         style="width:72px;height:72px;border-radius:50%;object-fit:cover;margin-bottom:14px;display:block;margin-left:auto;margin-right:auto;" alt="UEIPAB"/>
    <h2 style="color:white;margin:0;font-size:20px;font-weight:700;">Control de Asistencia</h2>
    <p style="color:rgba(255,255,255,.85);margin:6px 0 0;font-size:13px;">
      U.E.I.P.A.B. — Guía para el personal docente y administrativo
    </p>
  </div>

  <!-- INTRO -->
  <div style="padding:28px 32px 0;">
    <p style="font-size:15px;color:#1a2c5b;font-weight:600;margin:0 0 10px;">
      Estimado/a {{PRIMER_NOMBRE}},
    </p>
    <p style="font-size:14px;color:#444;line-height:1.7;margin:0 0 18px;">
      Como parte de nuestra modernización administrativa, hemos implementado un sistema
      digital de registro de asistencia. Queremos explicarte exactamente cómo funciona,
      para qué sirve — y, sobre todo, <strong>cómo te protege a ti</strong>.
    </p>
  </div>

  <!-- HOW IT WORKS -->
  <div style="padding:0 32px;">
    <div style="background:#f0f4fa;border-radius:8px;padding:20px 24px;margin-bottom:20px;">
      <p style="font-size:14px;font-weight:700;color:#1a2c5b;margin:0 0 14px;">
        ¿Cómo funciona el sistema?
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <tr>
          <td width="25%" style="padding:0 4px 0 0;vertical-align:top;">
            <div style="background:white;border-radius:6px;border:1px solid #dde3ee;padding:14px 10px;text-align:center;">
              <div style="width:28px;height:28px;background:#1a2c5b;border-radius:50%;color:white;font-size:13px;font-weight:700;line-height:28px;text-align:center;display:inline-block;margin-bottom:8px;">1</div>
              <div style="font-size:12px;font-weight:700;color:#1a2c5b;margin-bottom:5px;">Registra</div>
              <div style="font-size:11px;color:#555;line-height:1.55;">Kiosco (principal) o menú lateral de Odoo (Check In/Out) desde tu cuenta del sistema Odoo</div>
            </div>
          </td>
          <td width="25%" style="padding:0 4px;vertical-align:top;">
            <div style="background:white;border-radius:6px;border:1px solid #dde3ee;padding:14px 10px;text-align:center;">
              <div style="width:28px;height:28px;background:#1a2c5b;border-radius:50%;color:white;font-size:13px;font-weight:700;line-height:28px;text-align:center;display:inline-block;margin-bottom:8px;">2</div>
              <div style="font-size:12px;font-weight:700;color:#1a2c5b;margin-bottom:5px;">Aviso inteligente</div>
              <div style="font-size:11px;color:#555;line-height:1.55;">Solo recibirás aviso si falta tu registro de entrada o de salida — si ambos están presentes, no recibirás ningún correo</div>
            </div>
          </td>
          <td width="25%" style="padding:0 4px;vertical-align:top;">
            <div style="background:white;border-radius:6px;border:1px solid #dde3ee;padding:14px 10px;text-align:center;">
              <div style="width:28px;height:28px;background:#1a2c5b;border-radius:50%;color:white;font-size:13px;font-weight:700;line-height:28px;text-align:center;display:inline-block;margin-bottom:8px;">3</div>
              <div style="font-size:12px;font-weight:700;color:#1a2c5b;margin-bottom:5px;">Corrección</div>
              <div style="font-size:11px;color:#555;line-height:1.55;">El correo incluye "📝 Solicitar Corrección" — RRHH revisa antes del cierre</div>
            </div>
          </td>
          <td width="25%" style="padding:0 0 0 4px;vertical-align:top;">
            <div style="background:white;border-radius:6px;border:1px solid #dde3ee;padding:14px 10px;text-align:center;">
              <div style="width:28px;height:28px;background:#1a2c5b;border-radius:50%;color:white;font-size:13px;font-weight:700;line-height:28px;text-align:center;display:inline-block;margin-bottom:8px;">4</div>
              <div style="font-size:12px;font-weight:700;color:#1a2c5b;margin-bottom:5px;">Reporte quincenal</div>
              <div style="font-size:11px;color:#555;line-height:1.55;">Recibes tu resumen completo para verificarlo antes de nómina</div>
            </div>
          </td>
        </tr>
      </table>

      <!-- Teacher callout -->
      <div style="background:#fff8e1;border-left:4px solid #f0ad4e;border-radius:0 8px 8px 0;padding:14px 18px;margin-top:16px;">
        <p style="font-size:13px;font-weight:700;color:#7b5800;margin:0 0 6px;">🏫 Si eres docente</p>
        <p style="font-size:13px;color:#555;line-height:1.7;margin:0;">
          El sistema también reconoce el registro de asistencia de tus estudiantes como señal
          de tu presencia. Si registraste tus clases ese día, <strong>no recibirás un aviso
          aunque hayas olvidado el Kiosco</strong>. Además, el sistema aprende tu horario:
          los días sin clases asignadas no generan alertas.
        </p>
      </div>
    </div>
  </div>

  <!-- SCENARIO -->
  <div style="padding:0 32px;">
    <div style="border-left:4px solid #2471a3;padding:18px 20px;margin-bottom:20px;background:#f8fbff;border-radius:0 8px 8px 0;">
      <p style="font-size:14px;font-weight:700;color:#1a2c5b;margin:0 0 10px;">
        📖 Un caso concreto — así funciona en la práctica
      </p>
      <p style="font-size:13px;color:#444;line-height:1.7;margin:0 0 10px;">
        Imagina que llegas puntualmente a las 7:00 am, pero ese día el Kiosco tuvo un problema de conectividad. El sistema registra tu entrada a las 7:20 am — cuando el equipo volvió en línea.
      </p>
      <p style="font-size:13px;color:#444;line-height:1.7;margin:0 0 10px;">
        Al día siguiente por la mañana recibes el correo de aviso del sistema. El correo te muestra el registro como aparece en el sistema y te pregunta si es correcto.
      </p>
      <p style="font-size:13px;color:#444;line-height:1.7;margin:0;">
        <strong>¿Qué hacer?</strong> Haz clic en el botón de corrección y escribe: <em>"Llegué a las 7:00 am. El Kiosco presentó un inconveniente técnico esa mañana y no pude registrarme hasta las 7:20."</em>
        RRHH coordina con Tecnología, verifica el incidente y ajusta tu registro. El asunto queda resuelto en horas, sin escalaciones ni trámites adicionales.
      </p>
    </div>
  </div>

  <!-- WHY IT PROTECTS YOU -->
  <div style="padding:0 32px 20px;">
    <p style="font-size:14px;font-weight:700;color:#1a2c5b;margin:0 0 12px;">
      ¿Por qué esto te protege a ti?
    </p>
    <p style="font-size:13px;color:#444;line-height:1.7;margin:0 0 10px;">
      Tu registro de asistencia es tu respaldo documental. Si en algún momento existe una
      discrepancia sobre un día trabajado, la corrección que enviaste — con fecha, hora y
      explicación — queda guardada en el sistema como evidencia a tu favor.
    </p>
    <p style="font-size:13px;color:#444;line-height:1.7;margin:0 0 10px;">
      Toda institución seria — en Venezuela y en el mundo — lleva un registro verificable
      de asistencia. La diferencia aquí es que el sistema te avisa <em>a ti primero</em>,
      te da la herramienta para corregir, y RRHH revisa cada solicitud individualmente
      antes de que afecte tu nómina.
    </p>
  </div>

  <!-- KEY TIPS -->
  <div style="padding:0 32px 24px;">
    <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:16px 20px;">
      <p style="font-size:13px;font-weight:700;color:#7b5800;margin:0 0 10px;">
        💡 Tres recomendaciones prácticas
      </p>
      <ul style="margin:0;padding-left:18px;font-size:13px;color:#555;line-height:1.8;">
        <li><strong>Registra en el Kiosco</strong> de la Administración (método principal), o en el <strong>menú lateral de Odoo</strong> (Check In / Check Out) desde tu cuenta del sistema Odoo.</li>
        <li><strong>Si hay un fallo técnico, notifícalo ese mismo día</strong> a RRHH (recursoshumanos@ueipab.edu.ve) — cuanto antes quede constancia, más fácil es verificar.</li>
        <li><strong>Usa el botón de corrección</strong> en el correo de aviso — es la vía más rápida y queda auditada en el sistema.</li>
        <li>Si eres <strong>docente</strong>, registrar la asistencia de tus estudiantes cuenta como señal de presencia — el sistema lo reconoce automáticamente.</li>
      </ul>
    </div>
  </div>

  <!-- CLOSING -->
  <div style="padding:0 32px 28px;">
    <p style="font-size:13px;color:#555;line-height:1.7;margin:0 0 16px;">
      Este sistema existe para que la asistencia de todo el equipo sea un proceso transparente,
      justo y sin sorpresas al cierre de nómina. Si tienes alguna pregunta sobre cómo funciona,
      escríbenos a <a href="mailto:recursoshumanos@ueipab.edu.ve" style="color:#2471a3;font-weight:600;">recursoshumanos@ueipab.edu.ve</a>.
    </p>
    <p style="font-size:13px;color:#555;margin:0;">
      Cordialmente,<br/>
      <strong>Recursos Humanos</strong><br/>
      Instituto Privado Andrés Bello, CA
    </p>
  </div>

  <!-- FOOTER -->
  <div style="background:#f0f4fa;padding:14px 32px;text-align:center;border-top:1px solid #dde3ee;">
    <p style="font-size:11px;color:#888;margin:0;">
      Este mensaje es informativo. Para consultas escriba a recursoshumanos@ueipab.edu.ve.
    </p>
  </div>

</div>
</div>
```

---

## 5. Deployment Plan

| Step | Action | Owner |
|------|--------|-------|
| 1 | CEO reviews email copy and approves tone | Gustavo |
| 2 | Send preview to `gustavo.perdomo@ueipab.edu.ve` | Dev |
| 3 | Blast to all active employees via `mail.mail` XML-RPC | Dev |
| 4 | Trigger mail queue cron id=3 | Dev |

**Recipients:** All `hr.employee` records with a `work_email`, excluding test accounts (ids 574, 764) and special-schedule employees are still included (they benefit from knowing the process too).

**Timing:** Ideally sent **before** the next biweekly report or at the same time as the first morning alert cycle — so employees read the guide before they get their first alert.

---

## 6. Future: Web Page Version

Once the email lands, a persistent URL (e.g. `/attendance-guide/` — similar to `/mora-policy/`) would let employees re-read the guide at any time. The correction button in future alert emails could include a "¿Cómo funciona?" link pointing there.

This is low-priority until the email version is validated. Implementation would follow the same pattern as `ueipab_ari_portal` controllers.

---

## 7. EPOPP Connection

Section §4.4 of the EPOPP references this guide. The framing aligns with the institution's transparency-first operating philosophy: attendance records protect both the institution and the employee, and the correction channel is the designed path for any genuine discrepancy.

---

*Created 2026-05-29 — prompted by Yudelys Brito formal complaint (2026-05-29) illustrating the UX gap between system intent and employee perception.*
