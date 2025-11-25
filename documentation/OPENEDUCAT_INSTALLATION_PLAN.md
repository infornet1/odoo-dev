# OpenEducat ERP - Installation Plan
**Date:** 2025-11-24
**Target Environment:** Testing Database
**Version:** 17.0.1.0
**Archive Location:** `/home/ftpuser/odoo-dev/openeducat_erp-17.0.1.0.zip`

---

## Executive Summary

OpenEducat ERP is a comprehensive educational management system for Odoo 17. The suite contains **15 modules** covering student management, admissions, fees, attendance, exams, library, timetables, and more.

**Installation Complexity:** Medium
**Estimated Time:** 30-45 minutes
**Risk Level:** Low (Testing environment only)

---

## Module Overview

### Package Contents (15 Modules)

| Module | Purpose | Dependencies | Priority |
|--------|---------|--------------|----------|
| **openeducat_core** | Base module - Students, Faculties, Courses | board, hr, web, website | **CRITICAL** |
| **openeducat_fees** | Fee management & accounting | openeducat_core, account | High |
| **openeducat_admission** | Student admissions | openeducat_core, openeducat_fees | High |
| **openeducat_assignment** | Assignments & homework | openeducat_core | Medium |
| **openeducat_attendance** | Student attendance tracking | openeducat_core | High |
| **openeducat_exam** | Examination & grading | openeducat_core | High |
| **openeducat_library** | Library management | openeducat_core | Medium |
| **openeducat_parent** | Parent portal & communication | openeducat_core | Medium |
| **openeducat_timetable** | Class scheduling | openeducat_core | Medium |
| **openeducat_classroom** | Classroom management | openeducat_core | Low |
| **openeducat_facility** | Facility booking | openeducat_core | Low |
| **openeducat_activity** | Student activities | openeducat_core | Low |
| **web_openeducat** | Website snippets & theme | website | Medium |
| **openeducat_erp** | Meta-package (installs 7 core modules) | Multiple | **MAIN** |

### Dependency Tree

```
openeducat_core (foundation)
├── board (Odoo) ✅ Available (needs installation)
├── hr (Odoo) ✅ Installed
├── web (Odoo) ✅ Installed
└── website (Odoo) ✅ Installed

openeducat_fees
├── openeducat_core
└── account (Odoo) ✅ Installed

openeducat_admission
├── openeducat_core
└── openeducat_fees

openeducat_erp (Meta Package)
├── openeducat_admission
├── openeducat_assignment
├── openeducat_attendance
├── openeducat_library
├── openeducat_parent
├── openeducat_exam
└── web_openeducat
```

---

## Pre-Installation Checklist

### ✅ Environment Validation

**Testing Database:**
- Database: `testing`
- Odoo Version: 17.0
- Container: `odoo-dev-web`
- Addons Path: `/mnt/extra-addons/`

**Required Odoo Modules Status:**
- ✅ `account` - Installed
- ✅ `hr` - Installed
- ✅ `web` - Installed
- ✅ `website` - Installed
- ⚠️ `board` - Available but not installed (will auto-install)

**System Resources:**
- Archive Size: 15 MB
- Extracted Size: ~40 MB
- Disk Space Required: ~60 MB (with overhead)
- Current `/mnt/extra-addons` Usage: Minimal

### ⚠️ Important Notes

1. **CRITICAL:** This installation is for **TESTING environment ONLY**
2. **board module** needs to be installed first (dependency for openeducat_core)
3. All modules have LGPL-3 license (compatible with Odoo)
4. Demo data is included (can be skipped if needed)
5. No custom Python dependencies required

---

## Installation Plan

### Phase 1: Preparation (5 minutes)

**Step 1.1: Create Backup**
```bash
# Backup testing database
docker exec odoo-dev-postgres pg_dump -U odoo testing > /opt/odoo-dev/backups/testing_pre_openeducat_$(date +%Y%m%d_%H%M%S).sql
```

**Step 1.2: Extract Modules to Addons Path**
```bash
# Extract archive to /mnt/extra-addons/
cd /mnt/extra-addons/
unzip -q /home/ftpuser/odoo-dev/openeducat_erp-17.0.1.0.zip

# Verify extraction
ls -la /mnt/extra-addons/ | grep openeducat
```

**Step 1.3: Set Permissions**
```bash
# Ensure Odoo can read the modules
chown -R root:root /mnt/extra-addons/openeducat_*
chown -R root:root /mnt/extra-addons/web_openeducat
chmod -R 755 /mnt/extra-addons/openeducat_*
chmod -R 755 /mnt/extra-addons/web_openeducat
```

### Phase 2: Install Base Dependency (5 minutes)

**Step 2.1: Restart Odoo to Detect New Modules**
```bash
docker restart odoo-dev-web

# Wait for container to be ready (check logs)
docker logs -f odoo-dev-web
# Press Ctrl+C when you see "HTTP service (werkzeug) running"
```

**Step 2.2: Update Apps List**
```bash
# Via Odoo shell
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env
env['ir.module.module'].update_list()
env.cr.commit()
print("✅ Module list updated")
sys.exit(0)
EOF
```

**Step 2.3: Install 'board' Module (Required Dependency)**
```bash
# Install board module first
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

board_module = env['ir.module.module'].search([('name', '=', 'board')])
if board_module.state != 'installed':
    board_module.button_immediate_install()
    print("✅ Board module installed")
else:
    print("ℹ️  Board module already installed")

sys.exit(0)
EOF
```

### Phase 3: Install OpenEducat Core (10 minutes)

**Step 3.1: Install openeducat_core**
```bash
# Install core module (foundation for all other modules)
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

core_module = env['ir.module.module'].search([('name', '=', 'openeducat_core')])
if core_module:
    if core_module.state != 'installed':
        print("Installing openeducat_core...")
        core_module.button_immediate_install()
        print("✅ OpenEducat Core installed successfully")
    else:
        print("ℹ️  OpenEducat Core already installed")
else:
    print("❌ ERROR: openeducat_core module not found!")
    sys.exit(1)

sys.exit(0)
EOF
```

**Step 3.2: Verify Core Installation**
```bash
# Check if core module is installed
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT name, state FROM ir_module_module WHERE name = 'openeducat_core';"
```

### Phase 4: Install Additional Modules (15 minutes)

**Step 4.1: Install Supporting Modules**
```bash
# Install web_openeducat (website theme)
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

web_module = env['ir.module.module'].search([('name', '=', 'web_openeducat')])
if web_module and web_module.state != 'installed':
    web_module.button_immediate_install()
    print("✅ Web OpenEducat installed")

sys.exit(0)
EOF
```

**Step 4.2: Install Individual Functional Modules**

You can install modules individually as needed:

```bash
# Install fees module
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

modules_to_install = ['openeducat_fees', 'openeducat_admission',
                      'openeducat_attendance', 'openeducat_exam']

for module_name in modules_to_install:
    module = env['ir.module.module'].search([('name', '=', module_name)])
    if module and module.state != 'installed':
        print(f"Installing {module_name}...")
        module.button_immediate_install()
        print(f"✅ {module_name} installed")

sys.exit(0)
EOF
```

**Step 4.3: OR Install Full ERP Suite (Recommended)**

```bash
# Install openeducat_erp (meta-package installs 7 key modules)
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

erp_module = env['ir.module.module'].search([('name', '=', 'openeducat_erp')])
if erp_module and erp_module.state != 'installed':
    print("Installing OpenEducat ERP Suite...")
    erp_module.button_immediate_install()
    print("✅ OpenEducat ERP Suite installed (7 modules)")
else:
    print("ℹ️  OpenEducat ERP already installed")

sys.exit(0)
EOF
```

### Phase 5: Post-Installation (5 minutes)

**Step 5.1: Verify Installation**
```bash
# List all installed OpenEducat modules
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT name, state, shortdesc FROM ir_module_module WHERE name LIKE '%openeducat%' OR name = 'web_openeducat' ORDER BY name;"
```

**Step 5.2: Clear Assets Cache**
```bash
# Restart Odoo to clear compiled assets
docker restart odoo-dev-web
```

**Step 5.3: Browser Cache Clear**
- Open browser to testing instance
- Press `Ctrl+Shift+R` (hard refresh)
- Login and navigate to Apps menu
- Verify OpenEducat appears in installed apps

---

## Installation Options

### Option A: Minimal Installation (Fastest)
**Modules:** openeducat_core only
**Use Case:** Just exploring or need basic student management
**Time:** ~10 minutes

### Option B: Essential Suite (Recommended)
**Modules:** openeducat_erp (includes 7 key modules)
**Use Case:** Full educational management system
**Time:** ~30 minutes
**Includes:**
- Core, Admission, Assignment, Attendance
- Library, Parent portal, Exam, Web theme

### Option C: Complete Installation (Maximum Features)
**Modules:** All 15 modules
**Use Case:** Comprehensive evaluation of all features
**Time:** ~45 minutes

---

## Expected Menu Structure Post-Installation

After installation, you'll see new menu items:

```
📚 Education (Top Menu)
├── Students
│   ├── Students
│   ├── Student Courses
│   └── Subject Registration
├── Faculty
│   ├── Faculty
│   └── Department
├── Admission
│   ├── Admission Register
│   └── Admissions
├── Attendance
│   ├── Attendance Sheets
│   └── Attendance Lines
├── Exams
│   ├── Exam Sessions
│   ├── Exam Results
│   └── Grade Configuration
├── Fees
│   ├── Fee Terms
│   ├── Fee Elements
│   └── Fee Collection
├── Library
│   ├── Books
│   ├── Issue/Return
│   └── Book Requests
├── Configuration
│   ├── Courses
│   ├── Batches
│   ├── Subjects
│   ├── Academic Year
│   └── Academic Terms
```

---

## Rollback Plan

If installation fails or causes issues:

### Quick Rollback
```bash
# Uninstall all OpenEducat modules
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

openeducat_modules = env['ir.module.module'].search([
    '|', ('name', 'like', 'openeducat_%'),
    ('name', '=', 'web_openeducat')
])

for module in openeducat_modules:
    if module.state == 'installed':
        print(f"Uninstalling {module.name}...")
        module.button_immediate_uninstall()

print("✅ All OpenEducat modules uninstalled")
sys.exit(0)
EOF

# Remove module files
rm -rf /mnt/extra-addons/openeducat_*
rm -rf /mnt/extra-addons/web_openeducat

# Restart Odoo
docker restart odoo-dev-web
```

### Full Database Restore
```bash
# If database is corrupted, restore from backup
docker exec -i odoo-dev-postgres psql -U odoo -c "DROP DATABASE testing;"
docker exec -i odoo-dev-postgres psql -U odoo -c "CREATE DATABASE testing;"
docker exec -i odoo-dev-postgres psql -U odoo testing < /opt/odoo-dev/backups/testing_pre_openeducat_YYYYMMDD_HHMMSS.sql
```

---

## Potential Issues & Solutions

### Issue 1: Module Not Found After Extraction
**Symptom:** Module not appearing in Apps list
**Solution:**
```bash
docker restart odoo-dev-web
# Then update module list via Odoo UI: Apps > Update Apps List
```

### Issue 2: Dependency Errors During Installation
**Symptom:** "Module X depends on Y which is not installed"
**Solution:** Install dependencies first (board → openeducat_core → others)

### Issue 3: Permission Errors
**Symptom:** "Cannot read file" errors in logs
**Solution:**
```bash
chmod -R 755 /mnt/extra-addons/openeducat_*
docker restart odoo-dev-web
```

### Issue 4: Asset Loading Issues (CSS/JS)
**Symptom:** Broken layout or missing styles
**Solution:**
```bash
# Clear assets from Odoo
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
self.env['ir.attachment'].search([
    ('url', 'like', '/web/assets/%')
]).unlink()
sys.exit(0)
EOF

docker restart odoo-dev-web
# Browser: Ctrl+Shift+R (hard refresh)
```

---

## Post-Installation Configuration

### Initial Setup Tasks

1. **Configure Academic Year**
   - Navigate to Education > Configuration > Academic Year
   - Create current academic year (e.g., 2024-2025)

2. **Create Academic Terms**
   - Education > Configuration > Academic Terms
   - Define semesters/quarters

3. **Set Up Departments**
   - Education > Faculty > Departments
   - Create academic departments

4. **Define Courses**
   - Education > Configuration > Courses
   - Add degree programs

5. **Create Batches**
   - Education > Configuration > Batches
   - Create class batches (e.g., "2024 Batch")

6. **Configure Subjects**
   - Education > Configuration > Subjects
   - Add courses/subjects offered

7. **Set Company Information**
   - Settings > Companies > Update company details
   - Add logo for student ID cards

---

## Testing Checklist

After installation, verify functionality:

- [ ] Create a test student record
- [ ] Enroll student in a course
- [ ] Create admission record
- [ ] Generate student ID card report
- [ ] Create fee term and assign to student
- [ ] Mark attendance for a class
- [ ] Create exam session
- [ ] Issue library book
- [ ] Access student portal (if using portal)
- [ ] Check website integration

---

## Module Architecture Notes

### Database Impact
- **New Tables:** ~80 tables created
- **New Models:** ~60 models
- **Security Groups:** 15+ groups (Student, Faculty, Admin, etc.)
- **Report Templates:** 20+ QWeb reports

### Integration Points
- **HR Module:** Faculty linked to hr.employee
- **Accounting:** Fee collection integrated with account.move
- **Website:** Student portal and public pages
- **Portal:** Parent/student access
- **Mail:** Automated notifications

---

## Support & Documentation

**Vendor:** OpenEduCat Inc
**Website:** https://www.openeducat.org
**License:** LGPL-3
**Version:** 17.0.1.0
**Release Date:** May 2024

**Official Documentation:**
- https://www.openeducat.org/documentation
- https://apps.odoo.com/apps/modules/browse?search=openeducat

---

## Recommendations

### For UEIPAB Implementation

**Consider:**
1. **Start with Core Module Only** - Test basic student/faculty management
2. **Enable Fees Module** - If you need tuition management
3. **Add Attendance** - For class attendance tracking
4. **Evaluate Exam Module** - For grading and transcripts

**Skip (Initially):**
- Library module (if no library operations)
- Facility booking (if not needed)
- Timetable (can add later if needed)

**Integration Opportunities:**
- Link faculty to existing HR employees
- Integrate fees with current accounting setup
- Use existing company structure

**Caution:**
- This is a comprehensive ERP system
- May have overlapping functionality with existing modules
- Test thoroughly before considering production deployment
- Ensure it fits your specific educational workflow

---

## Summary

**Recommended Installation Approach:**
1. Install **openeducat_core** first (Phase 3)
2. Evaluate core functionality
3. Install **openeducat_erp** if satisfied (Phase 4.3)
4. Gradually enable additional modules as needed

**Total Estimated Time:** 30-45 minutes
**Risk Level:** Low (testing environment)
**Reversibility:** High (easy uninstall/rollback)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-24
**Author:** Claude Code
**Status:** Ready for Implementation
