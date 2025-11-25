# OpenEducat Option C Installation - Complete Procedure (WITH Full Demo Data)
**Date:** 2025-11-24 (Updated)
**Option:** C - Complete Installation (All 15 Modules WITH Full Demo Data)
**Target:** Testing Database
**Estimated Time:** 45-60 minutes
**Status:** APPROVED

---

## Approval Confirmation

**Plan Approved:** 2025-11-24
**Approved By:** User

**Pre-Installation Verification Completed:**
- Website ID=1 ("Instituto Privado Andrés Bello") will remain intact
- Existing pages (8 total) will be preserved
- Only new demo page `/home-option-1` will be added
- Demo page will be set as default homepage (easily reversible)

---

## Overview

This procedure installs **all 15 OpenEducat modules WITH demo data** for complete evaluation, including portal testing for parents, students, and teachers.

**What You Get:**
- All 15 modules fully functional
- Demo students, parents, teachers pre-configured
- Portal access ready to test immediately
- Sample courses, exams, attendance, fees
- Educational website homepage (replaces current - easily reversible)
- Complete user experience evaluation

**Website Note:** Your homepage WILL be replaced with OpenEducat demo homepage. This is **easily reversible** (30-second command) and recommended for full evaluation.

---

## Pre-Installation Checklist

### Prerequisites Verification

Run these commands to verify readiness:

```bash
# 1. Check disk space (need ~60MB free)
df -h /mnt/extra-addons

# 2. Verify archive exists
ls -lh /home/ftpuser/odoo-dev/openeducat_erp-17.0.1.0.zip

# 3. Check Odoo container is running
docker ps | grep odoo-dev-web

# 4. Verify testing database exists
docker exec odoo-dev-postgres psql -U odoo -l | grep testing

# 5. Check current homepage (baseline - will be replaced)
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT url, is_published FROM website_page WHERE url = '/';"
```

**Expected Results:**
- Disk space: Several GB available
- Archive: 15M file exists
- Container: Status "Up"
- Database: "testing" exists
- Homepage: Your current homepage entries

---

## Installation Procedure

### PHASE 1: Backup (5 minutes)

**Step 1.1: Create Database Backup**

```bash
# Create backup directory if needed
mkdir -p /opt/odoo-dev/backups

# Backup testing database
docker exec odoo-dev-postgres pg_dump -U odoo testing > \
  /opt/odoo-dev/backups/testing_pre_openeducat_$(date +%Y%m%d_%H%M%S).sql

# Verify backup was created
ls -lh /opt/odoo-dev/backups/testing_pre_openeducat_*.sql | tail -1
```

**Expected:** Backup file created (~50-100 MB depending on your data)

**Step 1.2: Document Current State**

```bash
# Save list of currently installed modules
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT name FROM ir_module_module WHERE state = 'installed' ORDER BY name;" \
  > /opt/odoo-dev/backups/modules_before_openeducat_$(date +%Y%m%d).txt

# Save current website pages
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT url, is_published FROM website_page ORDER BY url;" \
  > /opt/odoo-dev/backups/website_pages_before_openeducat_$(date +%Y%m%d).txt

# Count current modules
echo "Currently installed modules:"
wc -l /opt/odoo-dev/backups/modules_before_openeducat_$(date +%Y%m%d).txt
```

---

### PHASE 2: Extract and Prepare (5 minutes)

**Step 2.1: Extract Modules to Addons Directory**

```bash
# Navigate to addons directory
cd /mnt/extra-addons/

# Extract archive
unzip -q /home/ftpuser/odoo-dev/openeducat_erp-17.0.1.0.zip

# Verify extraction (should see 15 directories)
ls -d openeducat_* web_openeducat 2>/dev/null | wc -l
echo "Expected: 15 directories"

# List all extracted modules
ls -1d openeducat_* web_openeducat 2>/dev/null
```

**Expected Output:**
```
openeducat_activity
openeducat_admission
openeducat_assignment
openeducat_attendance
openeducat_classroom
openeducat_core
openeducat_erp
openeducat_exam
openeducat_facility
openeducat_fees
openeducat_library
openeducat_parent
openeducat_timetable
web_openeducat
```

**Step 2.2: Set Permissions**

```bash
# Ensure Odoo can read all modules
chown -R root:root /mnt/extra-addons/openeducat_*
chown -R root:root /mnt/extra-addons/web_openeducat

chmod -R 755 /mnt/extra-addons/openeducat_*
chmod -R 755 /mnt/extra-addons/web_openeducat

# Verify permissions
ls -la /mnt/extra-addons/ | grep -E "openeducat|web_openeducat"
```

**Step 2.3: Restart Odoo to Detect Modules**

```bash
# Restart container
docker restart odoo-dev-web

# Wait for Odoo to start
echo "Waiting for Odoo to start..."
sleep 15

# Check if Odoo is ready
docker logs odoo-dev-web 2>&1 | tail -5
```

**Expected:** Log shows Odoo is running

---

### PHASE 3: Update Module List (2 minutes)

**Step 3.1: Refresh Apps List in Odoo**

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys

print("Updating module list...")
env = self.env
env['ir.module.module'].update_list()
env.cr.commit()

print("Module list updated")

# Count OpenEducat modules found
openeducat_count = env['ir.module.module'].search_count([
    '|', ('name', 'like', 'openeducat_%'),
    ('name', '=', 'web_openeducat')
])
print(f"Found {openeducat_count} OpenEducat modules")

sys.exit(0)
EOF
```

**Expected Output:**
```
Updating module list...
Module list updated
Found 15 OpenEducat modules
```

**Step 3.2: Verify Modules Are Detected**

```bash
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT name, state FROM ir_module_module
   WHERE name LIKE '%openeducat%' OR name = 'web_openeducat'
   ORDER BY name;"
```

**Expected:** 15 modules with `state = 'uninstalled'`

---

### PHASE 4: Install Base Dependencies (5 minutes)

**Step 4.1: Install 'board' Module (Required)**

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

board_module = env['ir.module.module'].search([('name', '=', 'board')])
if board_module:
    if board_module.state != 'installed':
        print("Installing 'board' module...")
        board_module.button_immediate_install()
        print("Board module installed")
    else:
        print("Board module already installed")
else:
    print("ERROR: Board module not found!")
    sys.exit(1)

sys.exit(0)
EOF
```

---

### PHASE 5: Install OpenEducat Core (8 minutes)

**Step 5.1: Install openeducat_core WITH Demo Data**

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

print("=" * 60)
print("Installing openeducat_core WITH Demo Data")
print("=" * 60)

core_module = env['ir.module.module'].search([('name', '=', 'openeducat_core')])

if not core_module:
    print("ERROR: openeducat_core module not found!")
    sys.exit(1)

if core_module.state == 'installed':
    print("openeducat_core already installed")
else:
    print("Installing openeducat_core...")
    print("This will take 2-3 minutes...")
    core_module.button_immediate_install()
    print("openeducat_core installed successfully")
    print("")
    print("Demo Data Included:")
    print("  - Sample departments")
    print("  - Sample courses and batches")
    print("  - Sample subjects")
    print("  - Demo students with portal users")
    print("  - Demo faculty members")
    print("  - Academic year and terms")

sys.exit(0)
EOF
```

**Step 5.2: Verify Core Installation**

```bash
# Check core module status
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT state FROM ir_module_module WHERE name = 'openeducat_core';"

# Check demo students were created
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT COUNT(*) as student_count FROM op_student;" 2>/dev/null || echo "Table will be created"
```

---

### PHASE 6: Install Functional Modules WITH Demo (20 minutes)

**Step 6.1: Install All Functional Modules (Batch)**

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

# All modules to install in dependency order
modules_to_install = [
    ('openeducat_fees', 'Fee Management - Demo fee terms and elements'),
    ('openeducat_admission', 'Admissions - Demo admission registers'),
    ('openeducat_assignment', 'Assignments - Demo homework/assignments'),
    ('openeducat_attendance', 'Attendance - Demo attendance sheets'),
    ('openeducat_exam', 'Exams - Demo exam sessions and results'),
    ('openeducat_library', 'Library - Demo books and categories'),
    ('openeducat_parent', 'Parent Portal - Demo parent users linked to students'),
    ('openeducat_timetable', 'Timetable - Demo class schedules'),
    ('openeducat_classroom', 'Classroom - Demo classroom records'),
    ('openeducat_facility', 'Facility - Demo facility bookings'),
    ('openeducat_activity', 'Activities - Demo student activities'),
]

print("=" * 60)
print("Installing Functional Modules WITH Demo Data")
print("=" * 60)
print("")

installed_count = 0
for module_name, description in modules_to_install:
    print(f"Installing {module_name}")
    print(f"   {description}")

    module = env['ir.module.module'].search([('name', '=', module_name)])

    if not module:
        print(f"   Module not found, skipping\n")
        continue

    if module.state == 'installed':
        print(f"   Already installed\n")
        installed_count += 1
        continue

    try:
        module.button_immediate_install()
        print(f"   Installed successfully\n")
        installed_count += 1
    except Exception as e:
        print(f"   Error: {str(e)}\n")

print("=" * 60)
print(f"Functional modules: {installed_count}/{len(modules_to_install)} installed")
print("=" * 60)

sys.exit(0)
EOF
```

**Expected:** All 11 modules install successfully (takes ~15-20 minutes)

---

### PHASE 7: Install Website Module WITH Demo (5 minutes)

**Step 7.1: Install web_openeducat WITH Demo Data**

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

print("=" * 60)
print("Installing web_openeducat WITH Demo Data")
print("=" * 60)
print("")
print("NOTE: This will replace your homepage with OpenEducat demo")
print("      (Easily reversible - see restore instructions below)")
print("")

module = env['ir.module.module'].search([('name', '=', 'web_openeducat')])

if not module:
    print("ERROR: web_openeducat module not found!")
    sys.exit(1)

if module.state == 'installed':
    print("web_openeducat already installed")
else:
    print("Installing web_openeducat WITH demo...")

    try:
        module.button_immediate_install()
        print("")
        print("web_openeducat installed successfully WITH demo data")
        print("")
        print("Installed:")
        print("  - Educational website snippets (8 components)")
        print("  - Theme styling and CSS")
        print("  - Demo homepage at /home-option-1")
        print("  - Demo footer template")
        print("")
        print("Your original homepage is still available at /")
        print("Demo homepage is now the default")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

print("=" * 60)

sys.exit(0)
EOF
```

**Step 7.2: Verify Website Changes**

```bash
# Check website pages
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT url, is_published FROM website_page
   WHERE url IN ('/', '/home-option-1')
   ORDER BY url;"
```

**Expected:**
```
       url        | is_published
------------------+--------------
 /                | t
 /home-option-1   | t
```

---

### PHASE 8: Install Meta Package (Optional Verification)

**Step 8.1: Verify openeducat_erp Status**

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

# The meta package should be auto-satisfied since we installed all dependencies
erp_module = env['ir.module.module'].search([('name', '=', 'openeducat_erp')])

if erp_module:
    if erp_module.state != 'installed':
        print("Installing openeducat_erp meta-package...")
        erp_module.button_immediate_install()
        print("openeducat_erp installed")
    else:
        print("openeducat_erp already installed")

sys.exit(0)
EOF
```

---

### PHASE 9: Post-Installation (5 minutes)

**Step 9.1: Verify All Modules Installed**

```bash
# List all installed OpenEducat modules
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT name, state FROM ir_module_module
   WHERE (name LIKE '%openeducat%' OR name = 'web_openeducat')
   AND state = 'installed'
   ORDER BY name;"

# Count installed modules (should be 14-15)
echo ""
echo "Total OpenEducat modules installed:"
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT COUNT(*) FROM ir_module_module
   WHERE (name LIKE '%openeducat%' OR name = 'web_openeducat')
   AND state = 'installed';"
```

**Expected:** 14-15 modules showing `state = installed`

**Step 9.2: Clear Assets Cache**

```bash
# Clear Odoo's compiled assets
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys

print("Clearing assets cache...")
env = self.env

assets = env['ir.attachment'].search([('url', 'like', '/web/assets/%')])
assets_count = len(assets)
assets.unlink()
env.cr.commit()

print(f"Cleared {assets_count} compiled assets")

sys.exit(0)
EOF

# Restart Odoo
echo "Restarting Odoo..."
docker restart odoo-dev-web
sleep 15

# Verify Odoo is running
docker logs odoo-dev-web 2>&1 | tail -5
```

**Step 9.3: Check Demo Data Was Loaded**

```bash
echo "=========================================="
echo "Demo Data Verification"
echo "=========================================="

echo -n "Demo Students: "
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT COUNT(*) FROM op_student;" 2>/dev/null || echo "0"

echo -n "Demo Faculty: "
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT COUNT(*) FROM op_faculty;" 2>/dev/null || echo "0"

echo -n "Demo Courses: "
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT COUNT(*) FROM op_course;" 2>/dev/null || echo "0"

echo -n "Demo Subjects: "
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT COUNT(*) FROM op_subject;" 2>/dev/null || echo "0"

echo -n "Demo Parents: "
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c \
  "SELECT COUNT(*) FROM op_parent;" 2>/dev/null || echo "0"

echo ""
echo "=========================================="
```

---

## PHASE 10: Portal Testing Setup

### Step 10.1: Identify Demo Portal Users

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

print("=" * 60)
print("Demo Portal Users for Testing")
print("=" * 60)

# Find student portal users
print("\nSTUDENT PORTAL USERS:")
print("-" * 40)
students = env['op.student'].search([])
for student in students[:5]:  # First 5 students
    if student.user_id:
        print(f"  Name: {student.name}")
        print(f"  Login: {student.user_id.login}")
        print(f"  Email: {student.user_id.email or 'N/A'}")
        print("")

# Find parent portal users
print("\nPARENT PORTAL USERS:")
print("-" * 40)
parents = env['op.parent'].search([])
for parent in parents[:5]:  # First 5 parents
    if parent.user_id:
        print(f"  Name: {parent.name}")
        print(f"  Login: {parent.user_id.login}")
        print(f"  Email: {parent.user_id.email or 'N/A'}")
        children = parent.student_ids.mapped('name')
        print(f"  Children: {', '.join(children) if children else 'N/A'}")
        print("")

# Find faculty portal users
print("\nFACULTY PORTAL USERS:")
print("-" * 40)
faculty = env['op.faculty'].search([])
for fac in faculty[:5]:  # First 5 faculty
    if fac.user_id:
        print(f"  Name: {fac.name}")
        print(f"  Login: {fac.user_id.login}")
        print(f"  Email: {fac.user_id.email or 'N/A'}")
        print("")

print("=" * 60)
print("Note: Default password for demo users is usually 'demo' or '1'")
print("You can reset passwords in Settings > Users")
print("=" * 60)

sys.exit(0)
EOF
```

### Step 10.2: Reset Demo User Passwords (If Needed)

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

# Find all portal users from OpenEducat
portal_group = env.ref('base.group_portal')
demo_users = env['res.users'].search([
    ('groups_id', 'in', portal_group.id),
    ('login', '!=', 'portal')
])

print("Resetting demo portal user passwords to 'demo123'...")
print("")

for user in demo_users[:10]:  # First 10 users
    try:
        user.write({'password': 'demo123'})
        print(f"  {user.login} - Password set to 'demo123'")
    except Exception as e:
        print(f"  {user.login} - Error: {str(e)}")

env.cr.commit()
print("")
print("Demo passwords reset. Use 'demo123' to login as portal users.")

sys.exit(0)
EOF
```

---

## Portal Testing Checklist

### Student Portal Testing

Access: Login as demo student user

- [ ] **Dashboard:** Student can see their dashboard
- [ ] **Profile:** Student can view/edit their profile
- [ ] **Courses:** Student can see enrolled courses
- [ ] **Attendance:** Student can view attendance records
- [ ] **Exams:** Student can see exam schedule and results
- [ ] **Assignments:** Student can view and submit assignments
- [ ] **Fees:** Student can see fee details and payment status
- [ ] **Library:** Student can see borrowed books
- [ ] **Timetable:** Student can view class schedule

### Parent Portal Testing

Access: Login as demo parent user

- [ ] **Dashboard:** Parent can see children's overview
- [ ] **Children:** Parent can see list of their children
- [ ] **Attendance:** Parent can view children's attendance
- [ ] **Grades:** Parent can see children's exam results
- [ ] **Fees:** Parent can view fee status for children
- [ ] **Communication:** Parent can contact teachers (if enabled)

### Faculty Portal Testing

Access: Login as demo faculty user

- [ ] **Dashboard:** Faculty can see their dashboard
- [ ] **Courses:** Faculty can see assigned courses
- [ ] **Students:** Faculty can view student lists
- [ ] **Attendance:** Faculty can mark attendance
- [ ] **Assignments:** Faculty can create/grade assignments
- [ ] **Exams:** Faculty can enter exam results

### Public Website Testing

Access: Visit website without login

- [ ] **Homepage:** OpenEducat demo homepage displays correctly
- [ ] **Navigation:** Menu items work properly
- [ ] **Courses:** Public course catalog visible (if enabled)
- [ ] **Contact:** Contact forms work
- [ ] **Responsive:** Mobile view works correctly

---

## Homepage Management

### View Demo Homepage

After installation, your website will show the OpenEducat demo homepage.

**Access URLs:**
- **Demo Homepage (new default):** `http://[your-url]/` or `http://[your-url]/home-option-1`
- **Original Homepage:** Your original content is still accessible

### Restore Original Homepage (When Needed)

If you want to restore your original homepage after evaluation:

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
env = self.env

print("Restoring original homepage...")

# Find and remove demo homepage
demo_page = env['website.page'].search([('url', '=', '/home-option-1')])
if demo_page:
    demo_page.unlink()
    print("Demo homepage removed")
else:
    print("Demo homepage not found")

# Ensure original pages are published
original_pages = env['website.page'].search([('url', '=', '/')])
for page in original_pages:
    if not page.is_published:
        page.write({'is_published': True})
        print(f"Restored: {page.name}")

env.cr.commit()
print("")
print("Original homepage restored!")

sys.exit(0)
EOF
```

### Switch Between Homepages

To temporarily switch which page is the default:

```bash
# Make demo homepage default (show demo)
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "UPDATE website_page SET is_published = true WHERE url = '/home-option-1';"

# OR hide demo homepage (show original)
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "UPDATE website_page SET is_published = false WHERE url = '/home-option-1';"
```

---

## Verification Checklist

### Backend Verification

- [ ] **Education Menu:** Visible in top navigation
- [ ] **Students:** Demo students appear in list
- [ ] **Faculty:** Demo faculty appear in list
- [ ] **Courses:** Demo courses configured
- [ ] **Academic Year:** Current year set up
- [ ] **Fees:** Fee terms defined
- [ ] **Library:** Demo books available

### Portal Verification

- [ ] **Student Login:** Can login as demo student
- [ ] **Parent Login:** Can login as demo parent
- [ ] **Faculty Login:** Can login as demo faculty
- [ ] **Portal Navigation:** Menu items work
- [ ] **Data Display:** Student sees their records

### Website Verification

- [ ] **Demo Homepage:** Displays correctly
- [ ] **Snippets:** Available in website editor
- [ ] **Styling:** Educational theme applied
- [ ] **Original Page:** Still accessible (if needed)

---

## Troubleshooting

### Issue: Demo Data Not Loaded

**Symptom:** No demo students/faculty after installation

**Solution - Manual Demo Load:**
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
from odoo.tools import convert
import os

module_path = '/mnt/extra-addons/openeducat_core'
demo_files = [
    'demo/department_demo.xml',
    'demo/base_demo.xml',
    'demo/res_partner_demo.xml',
    'demo/student_demo.xml',
    'demo/faculty_demo.xml',
]

for demo_file in demo_files:
    file_path = os.path.join(module_path, demo_file)
    if os.path.exists(file_path):
        print(f"Loading {demo_file}...")
        with open(file_path, 'rb') as f:
            convert.convert_xml_import(env.cr, 'openeducat_core', f, {}, 'init', False)

env.cr.commit()
print("Demo data loaded manually")
sys.exit(0)
EOF
```

### Issue: Portal Users Can't Login

**Symptom:** Demo users get "wrong login/password"

**Solution - Reset Passwords:**
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
# Reset all portal user passwords
portal_group = env.ref('base.group_portal')
portal_users = env['res.users'].search([('groups_id', 'in', portal_group.id)])
for user in portal_users:
    user.write({'password': 'demo123'})
    print(f"Reset: {user.login}")
env.cr.commit()
sys.exit(0)
EOF
```

### Issue: Education Menu Not Appearing

**Solution:**
1. Clear browser cache: `Ctrl+Shift+R`
2. Logout and login again
3. Check user has Education group:

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
admin = env['res.users'].search([('login', '=', 'admin')])
edu_groups = env['res.groups'].search([('category_id.name', '=', 'Education')])
for group in edu_groups:
    admin.write({'groups_id': [(4, group.id)]})
print("Admin granted all Education groups")
sys.exit(0)
EOF
```

---

## Rollback Procedures

### Quick Rollback: Restore Homepage Only

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
demo_page = env['website.page'].search([('url', '=', '/home-option-1')])
if demo_page:
    demo_page.unlink()
    print("Demo homepage removed")
sys.exit(0)
EOF
```

### Complete Rollback: Uninstall All OpenEducat

```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys

modules = env['ir.module.module'].search([
    '|', ('name', 'like', 'openeducat_%'),
    ('name', '=', 'web_openeducat')
])

for module in modules:
    if module.state == 'installed':
        print(f"Uninstalling {module.name}...")
        module.button_immediate_uninstall()

print("All OpenEducat modules uninstalled")
sys.exit(0)
EOF

# Remove module files
rm -rf /mnt/extra-addons/openeducat_*
rm -rf /mnt/extra-addons/web_openeducat

# Restart Odoo
docker restart odoo-dev-web
```

### Database Restore: Full Rollback

```bash
# Find your backup
ls -lh /opt/odoo-dev/backups/testing_pre_openeducat_*.sql

# Restore (replace TIMESTAMP with actual backup filename)
docker exec -i odoo-dev-postgres psql -U odoo -c "DROP DATABASE testing;"
docker exec -i odoo-dev-postgres psql -U odoo -c "CREATE DATABASE testing OWNER odoo;"
docker exec -i odoo-dev-postgres psql -U odoo testing < \
  /opt/odoo-dev/backups/testing_pre_openeducat_YYYYMMDD_HHMMSS.sql

# Restart Odoo
docker restart odoo-dev-web
```

---

## Installation Summary

### What Gets Installed

| Module | Demo Data Included |
|--------|-------------------|
| openeducat_core | Students, Faculty, Courses, Subjects |
| openeducat_fees | Fee terms, Fee elements |
| openeducat_admission | Admission registers |
| openeducat_assignment | Sample assignments |
| openeducat_attendance | Attendance sheets |
| openeducat_exam | Exam sessions, Results |
| openeducat_library | Books, Categories |
| openeducat_parent | Parent records with portal users |
| openeducat_timetable | Timetable schedules |
| openeducat_classroom | Classroom records |
| openeducat_facility | Facility bookings |
| openeducat_activity | Student activities |
| web_openeducat | Demo homepage, Footer, Snippets |
| openeducat_erp | Meta-package (no data) |

### Portal Users Created

- **Students:** Demo students with portal access
- **Parents:** Demo parents linked to students
- **Faculty:** Demo faculty with portal access

### Website Changes

- **Homepage:** Replaced with OpenEducat demo (reversible)
- **Snippets:** 8 educational building blocks added
- **Styling:** Educational theme CSS applied

---

## Quick Reference Commands

### Check Installation Status
```bash
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT name, state FROM ir_module_module
   WHERE name LIKE '%openeducat%' ORDER BY name;"
```

### List Demo Users
```bash
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT login, name FROM res_users
   WHERE login LIKE '%student%' OR login LIKE '%parent%' OR login LIKE '%faculty%';"
```

### Restore Original Homepage
```bash
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "DELETE FROM website_page WHERE url = '/home-option-1';"
```

### Restart Odoo
```bash
docker restart odoo-dev-web && sleep 15 && docker logs odoo-dev-web 2>&1 | tail -5
```

---

## Installation Checklist Summary

Use this quick checklist to track progress:

- [ ] **Phase 1:** Database backup created
- [ ] **Phase 2:** Modules extracted to /mnt/extra-addons
- [ ] **Phase 3:** Module list updated in Odoo
- [ ] **Phase 4:** Board module installed
- [ ] **Phase 5:** openeducat_core installed WITH demo
- [ ] **Phase 6:** 11 functional modules installed WITH demo
- [ ] **Phase 7:** web_openeducat installed WITH demo
- [ ] **Phase 8:** Meta package verified
- [ ] **Phase 9:** Assets cleared, Odoo restarted
- [ ] **Phase 10:** Portal users identified, passwords reset
- [ ] **Verification:** All modules showing as installed
- [ ] **Portal Test:** Can login as student/parent/faculty

---

**Installation Time Estimate:** 45-60 minutes
**Complexity:** Medium
**Risk Level:** Low (testing environment + backup)
**Reversibility:** High (easy uninstall + database restore)

**Ready to proceed?** Let me know when you want to start the installation!
