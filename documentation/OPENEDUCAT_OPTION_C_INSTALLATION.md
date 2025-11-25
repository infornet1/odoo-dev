# OpenEducat Option C Installation - Complete Procedure
**Date:** 2025-11-24
**Option:** C - Complete Installation (All 14 Modules)
**Target:** Testing Database
**Status:** COMPLETED

---

## Installation Summary

**Completed:** 2025-11-24
**Duration:** ~45 minutes
**Result:** SUCCESS - All 14 modules installed

### Modules Installed (14 total)

| # | Module | Version | Status |
|---|--------|---------|--------|
| 1 | openeducat_core | 17.0.1.0 | Installed |
| 2 | openeducat_activity | 17.0.1.0 | Installed |
| 3 | openeducat_admission | 17.0.1.0 | Installed |
| 4 | openeducat_assignment | 17.0.1.0 | Installed |
| 5 | openeducat_attendance | 17.0.1.0 | Installed |
| 6 | openeducat_classroom | 17.0.1.0 | Installed |
| 7 | openeducat_erp | 17.0.1.0 | Installed |
| 8 | openeducat_exam | 17.0.1.0 | Installed |
| 9 | openeducat_facility | 17.0.1.0 | Installed |
| 10 | openeducat_fees | 17.0.1.0 | Installed |
| 11 | openeducat_library | 17.0.1.0 | Installed |
| 12 | openeducat_parent | 17.0.1.0 | Installed |
| 13 | openeducat_timetable | 17.0.1.0 | Installed |
| 14 | web_openeducat | 17.0.1.0 | Installed |

### Sample Data Created

Since the testing database was created without demo mode, sample data was manually created:

| Record Type | Count | Details |
|-------------|-------|---------|
| Academic Years | 1 | 2024-2025 |
| Academic Terms | 1 | Primer Trimestre 2024-2025 |
| Courses | 1 | Educación Primaria (EP) |
| Batches | 1 | 1er Grado A |
| Subjects | 4 | Matemáticas, Lengua, Ciencias Naturales, Ciencias Sociales |
| Faculty | 1 | María González |
| Students | 1 | Luis Pérez |
| Parents | 1 | José Pérez |
| Relationships | 1 | Padre/Madre |

### Portal Test Users

| Role | Login | Password |
|------|-------|----------|
| Faculty | `docente.demo` | `Demo2024!` |
| Parent | `representante.demo` | `Demo2024!` |
| Student | `estudiante.demo` | `Demo2024!` |

### Website Status

- **Website ID=1:** Instituto Privado Andrés Bello - **PRESERVED**
- **Homepage:** Original homepage intact
- **OpenEducat Snippets:** Available in website editor (8 snippets)

### Backup

- **Pre-installation backup:** `/opt/odoo-dev/backups/testing_pre_openeducat_20251124.sql` (67MB)

---

## Post-Installation Notes

### Demo Data Limitation

The testing database was created **without** the `--demo-data` flag, which means:
- Odoo demo data XML files are NOT automatically loaded
- Sample data was created manually (see above)
- For full demo experience, consider creating a new database with demo enabled

### Website Frontend - Snippets Based

The `web_openeducat` module provides **website snippets** (building blocks), NOT a complete ready-made website:

**Available Snippets (8):**
1. Slider - Hero carousel
2. About Us - About section
3. Our Course - Course showcase
4. Achievement - Stats/counters
5. Teacher - Faculty display
6. Event - Events listing
7. News Feed - News/blog section
8. Footer - Educational footer

**How to Use Snippets:**
1. Go to: http://dev.ueipab.edu.ve:8019/
2. Login as admin
3. Click **Edit** button (top right)
4. Look at **Blocks** panel (left side) - OpenEducat snippets at TOP
5. **Drag & Drop** snippets onto your page
6. Click **Save** when done

**Important:** Hard refresh browser (`Ctrl+Shift+R`) to load new assets.

---

## Access Points

### Backend (Admin)
- **URL:** http://dev.ueipab.edu.ve:8019/web
- **Menu:** Education (in top navigation after login)

### Frontend (Website)
- **URL:** http://dev.ueipab.edu.ve:8019/
- **Edit Mode:** http://dev.ueipab.edu.ve:8019/website/edit

### Portal (Test Users)
- **URL:** http://dev.ueipab.edu.ve:8019/my
- **Logins:** See Portal Test Users table above

---

## Quick Commands Reference

### Check Installation Status
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http 2>/dev/null << 'EOF'
from odoo import api, SUPERUSER_ID
env = api.Environment(self.env.cr, SUPERUSER_ID, {})
mods = env['ir.module.module'].search([
    ('name', 'like', 'openeducat%'),
    ('state', '=', 'installed')
], order='name')
for m in mods:
    print(f"{m.name}: {m.state}")
print(f"\nTotal: {len(mods)} modules")
EOF
```

### List Sample Data
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http 2>/dev/null << 'EOF'
from odoo import api, SUPERUSER_ID
env = api.Environment(self.env.cr, SUPERUSER_ID, {})
print(f"Students: {env['op.student'].search_count([])}")
print(f"Faculty: {env['op.faculty'].search_count([])}")
print(f"Parents: {env['op.parent'].search_count([])}")
print(f"Courses: {env['op.course'].search_count([])}")
print(f"Subjects: {env['op.subject'].search_count([])}")
EOF
```

### Reset Portal User Password
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http 2>/dev/null << 'EOF'
from odoo import api, SUPERUSER_ID
env = api.Environment(self.env.cr, SUPERUSER_ID, {})
user = env['res.users'].search([('login', '=', 'estudiante.demo')])
if user:
    user.write({'password': 'NewPassword123!'})
    env.cr.commit()
    print(f"Password reset for {user.login}")
EOF
```

### Clear Assets Cache
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http 2>/dev/null << 'EOF'
from odoo import api, SUPERUSER_ID
env = api.Environment(self.env.cr, SUPERUSER_ID, {})
attachments = env['ir.attachment'].search([('name', 'like', 'web.assets%')])
print(f"Clearing {len(attachments)} assets...")
attachments.unlink()
env.cr.commit()
EOF
docker restart odoo-dev-web
```

---

## Rollback Procedures

### Uninstall All OpenEducat Modules
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http << 'EOF'
from odoo import api, SUPERUSER_ID
env = api.Environment(self.env.cr, SUPERUSER_ID, {})
modules = env['ir.module.module'].search([
    '|', ('name', 'like', 'openeducat_%'),
    ('name', '=', 'web_openeducat'),
    ('state', '=', 'installed')
])
for m in modules:
    print(f"Uninstalling {m.name}...")
    m.button_immediate_uninstall()
env.cr.commit()
EOF
```

### Full Database Restore
```bash
# Stop Odoo
docker stop odoo-dev-web

# Restore backup
docker exec -i odoo-dev-postgres psql -U odoo -c "DROP DATABASE testing;"
docker exec -i odoo-dev-postgres psql -U odoo -c "CREATE DATABASE testing OWNER odoo;"
cat /opt/odoo-dev/backups/testing_pre_openeducat_20251124.sql | \
  docker exec -i odoo-dev-postgres psql -U odoo testing

# Restart Odoo
docker start odoo-dev-web
```

---

## Next Steps (Evaluation TODO)

### Backend Evaluation
- [ ] Explore **Education** menu in backend
- [ ] Review Students, Faculty, Courses management
- [ ] Test Attendance marking workflow
- [ ] Test Exam/Grading workflow
- [ ] Test Fee management
- [ ] Review Library functionality
- [ ] Test Timetable creation

### Portal Evaluation
- [ ] Login as `estudiante.demo` - test student portal
- [ ] Login as `representante.demo` - test parent portal
- [ ] Login as `docente.demo` - test faculty portal
- [ ] Verify portal permissions and views

### Website Evaluation
- [ ] Add OpenEducat snippets to a test page
- [ ] Evaluate snippet customization options
- [ ] Test responsive design on mobile

### Integration Evaluation
- [ ] Check if OpenEducat integrates with existing HR module
- [ ] Review reporting capabilities
- [ ] Assess customization requirements for UEIPAB

---

## Documentation References

- [OpenEducat Official Docs](https://www.openeducat.org/documentation)
- [Installation Plan](OPENEDUCAT_INSTALLATION_PLAN.md)
- [Website Safety Analysis](OPENEDUCAT_WEBSITE_SAFETY_ANALYSIS.md)
- [Demo Data Options](OPENEDUCAT_DEMO_DATA_OPTIONS.md)

---

**Installation Completed:** 2025-11-24 ~02:50 UTC
**Installed By:** Claude Code Assistant
**Environment:** Testing (http://dev.ueipab.edu.ve:8019/)
