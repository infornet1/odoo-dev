# Payslip Acknowledgment Status Report

**Last Updated:** 2026-04-07
**Environment:** Production (`DB_UEIPAB`)

How to ask Claude for this report and the SQL queries behind it.

---

## How to Request This Report

Just ask:

> "Can you check payslip acknowledgment status in production, grouped by employee, for those pending?"

Or variations like:
- "Show me pending ack payslips by employee in production"
- "Which employees haven't acknowledged their payslips?"
- "Ack status report grouped by employee"

Claude will query production and return a formatted table. You can also ask to split it into groups of N rows per table.

---

## SQL Queries

### Summary by Employee + Pending Batches

```sql
SELECT
    e.name                                                        AS employee,
    COUNT(s.id)                                                   AS pending,
    MIN(r.date_end)                                               AS oldest,
    MAX(r.date_end)                                               AS newest,
    STRING_AGG(r.name, ', ' ORDER BY r.date_end ASC)             AS pending_batches
FROM hr_payslip s
JOIN hr_employee e ON e.id = s.employee_id
JOIN hr_payslip_run r ON r.id = s.payslip_run_id
WHERE r.state        = 'close'
  AND s.state        IN ('done', 'paid')
  AND s.is_acknowledged = false
GROUP BY e.name
ORDER BY COUNT(s.id) DESC, e.name ASC;
```

### Summary by Batch (how many pending per closed batch)

```sql
SELECT
    r.name          AS batch,
    r.date_end      AS period_end,
    COUNT(s.id)     AS pending
FROM hr_payslip s
JOIN hr_payslip_run r ON r.id = s.payslip_run_id
WHERE r.state        = 'close'
  AND s.state        IN ('done', 'paid')
  AND s.is_acknowledged = false
GROUP BY r.name, r.date_end
ORDER BY r.date_end DESC;
```

### Employee Emails (for pending ack employees)

```sql
SELECT DISTINCT e.name AS employee, e.work_email
FROM hr_payslip s
JOIN hr_employee e ON e.id = s.employee_id
JOIN hr_payslip_run r ON r.id = s.payslip_run_id
WHERE r.state = 'close'
  AND s.state IN ('done', 'paid')
  AND s.is_acknowledged = false
ORDER BY e.name ASC;
```

### Total Counts (quick overview)

```sql
SELECT
    SUM(CASE WHEN s.is_acknowledged         THEN 1 ELSE 0 END) AS acknowledged,
    SUM(CASE WHEN NOT s.is_acknowledged     THEN 1 ELSE 0 END) AS pending,
    COUNT(s.id)                                                  AS total
FROM hr_payslip s
JOIN hr_payslip_run r ON r.id = s.payslip_run_id
WHERE r.state = 'close'
  AND s.state IN ('done', 'paid');
```

---

## Key Fields on `hr_payslip`

| Column | Type | Description |
|--------|------|-------------|
| `is_acknowledged` | Boolean | `true` = employee clicked the confirmation link |
| `acknowledged_date` | Datetime | When acknowledgment was recorded |
| `acknowledged_ip` | Char | IP address of the employee's device |
| `acknowledged_user_agent` | Char | Browser/device info at acknowledgment time |
| `ack_reminder_count` | Integer | How many reminder emails have been sent |
| `ack_reminder_last_date` | Datetime | Date of the last reminder sent |

---

## How to Run via Claude

Claude runs these queries against the production PostgreSQL container directly:

```bash
sshpass -p '<password>' ssh root@10.124.0.3 \
  "docker exec ueipab17_postgres_1 psql -U odoo DB_UEIPAB -c \"<SQL>\""
```

No Odoo shell required — direct SQL is sufficient for read-only reporting.

---

## Report Output Format

Claude returns the results as a markdown table. If there are many rows, ask to split them:

> "Can you separate the table in groups of 8?"

Claude will split the results into multiple tables of 8 rows each, numbered by global row position.

To get a plain-text email list (one per line, copy-paste ready):

> "Can you list all emails of pending ack employees?"

Claude returns one email per line with no extra formatting.

---

## Related Documentation

- [Payslip Acknowledgment System](PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) — full feature documentation
- [Batch Email Wizard](BATCH_EMAIL_WIZARD.md) — how to send payslip emails
- [Changelog](CHANGELOG.md) — version history
