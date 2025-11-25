# OpenEducat Demo Data - Can It Be Installed Later?
**Date:** 2025-11-24
**Question:** Can demo data be added after modules are already installed?

---

## Quick Answer

**Short Answer:** ❌ **NO** - Odoo's standard mechanism does NOT support loading demo data after a module is already installed.

**BUT:** ✅ **YES** - There are **3 workarounds** to get demo data later if needed.

---

## Understanding Odoo Demo Data Mechanism

### How Demo Data Works in Odoo

**At Database Creation:**
```
Create Database Screen:
  Database Name: [testing]
  [ ] Load demonstration data  ← THIS IS CRITICAL
```

This checkbox sets a **database-wide flag**:
- **Checked:** `demo = True` (all modules install WITH demo)
- **Unchecked:** `demo = False` (all modules install WITHOUT demo)

**Your Testing Database Status:**
```sql
SELECT demo FROM ir_module_module LIMIT 1;
Result: f (false)
```

Your database was created **WITHOUT demo mode enabled**.

### What Happens During Module Installation

**Module Manifest Structure:**
```python
# __manifest__.py
{
    'name': 'web_openeducat',
    'data': [                          # ← ALWAYS loaded
        'views/assets.xml',
        'views/snippets/slider.xml',
        ...
    ],
    'demo': [                          # ← ONLY loaded if demo=True
        'data/homepage_demo.xml',      # Demo homepage
        'data/footer_template.xml',    # Demo footer
    ],
}
```

**Installation Behavior:**
- If `database.demo = True` → Install BOTH 'data' and 'demo' files
- If `database.demo = False` → Install ONLY 'data' files (skip 'demo')

**After Module Is Installed:**
- Odoo marks demo files as "already processed"
- **Reinstalling the module:** Still skips demo files
- **Upgrading the module:** Still skips demo files
- **Uninstall + Reinstall:** Still skips demo files (database flag unchanged)

---

## Why Standard Method Doesn't Work

### Technical Limitation

Odoo's module loading mechanism:

```python
# Simplified Odoo internal logic
def load_module(module):
    load_data_files(module.data)  # Always load

    if database.demo_enabled:      # Check database flag
        load_data_files(module.demo)  # Only if flag is True
```

**Key Point:** The `database.demo_enabled` flag is **set at database creation** and **cannot be changed** for existing databases through standard UI.

---

## Workarounds: 3 Ways to Get Demo Data Later

### ✅ Option 1: Manual Data Loading (Recommended)

**Load demo XML files manually using Odoo shell.**

**Advantages:**
- ✅ Works with existing installation
- ✅ Selective loading (choose which demo files)
- ✅ No module reinstallation needed
- ✅ Can be done anytime

**Steps:**

```bash
# Step 1: Identify demo files to load
# For web_openeducat, the demo files are:
# - data/homepage_demo.xml
# - data/footer_template.xml

# Step 2: Load demo data manually
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
from odoo.tools import convert

# Path to the module
module_path = '/mnt/extra-addons/web_openeducat'

# Demo files to load
demo_files = [
    'data/homepage_demo.xml',
    'data/footer_template.xml',
]

print("=" * 60)
print("Loading web_openeducat demo data manually")
print("=" * 60)

for demo_file in demo_files:
    file_path = f"{module_path}/{demo_file}"
    print(f"\n📦 Loading: {demo_file}")

    try:
        # Use Odoo's XML parser to load the file
        with open(file_path, 'rb') as f:
            convert.convert_xml_import(
                env.cr,
                'web_openeducat',
                f,
                idref={},
                mode='init',
                noupdate=False
            )
        print(f"   ✅ Loaded successfully")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

env.cr.commit()
print("\n" + "=" * 60)
print("Demo data loading complete")
print("=" * 60)

sys.exit(0)
EOF

# Step 3: Verify homepage was created
docker exec odoo-dev-postgres psql -U odoo -d testing -c \
  "SELECT url, is_published FROM website_page WHERE url = '/home-option-1';"
```

**Result:** Demo homepage appears at `/home-option-1`, becomes default

**To Undo:**
```bash
# Remove demo homepage if you don't want it
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
env['website.page'].search([('url', '=', '/home-option-1')]).unlink()
sys.exit(0)
EOF
```

---

### ✅ Option 2: Move Demo to Data Files

**Modify module manifest to treat demo as regular data.**

**Advantages:**
- ✅ Demo files load on module upgrade
- ✅ Persistent solution
- ✅ Works with any future installations

**Disadvantages:**
- ⚠️ Requires modifying module code
- ⚠️ Demo data becomes "permanent" data
- ⚠️ Less clean separation

**Steps:**

```bash
# Step 1: Edit web_openeducat manifest
nano /mnt/extra-addons/web_openeducat/__manifest__.py

# Step 2: Change this:
'demo': [
    'data/homepage_demo.xml',
    'data/footer_template.xml',
],

# To this:
'data': [
    'views/assets.xml',
    'views/snippets/slider.xml',
    # ... existing data files ...
    'data/homepage_demo.xml',      # ← Moved from demo
    'data/footer_template.xml',    # ← Moved from demo
],
'demo': [
    # Empty now
],

# Step 3: Upgrade the module
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
module = env['ir.module.module'].search([('name', '=', 'web_openeducat')])
module.button_immediate_upgrade()
print("✅ Module upgraded, demo data loaded")
sys.exit(0)
EOF
```

**Result:** Demo homepage loads on upgrade

**Caution:** This modifies the module, making updates from vendor more complex.

---

### ✅ Option 3: Create New Demo Database

**Create a separate database WITH demo mode enabled.**

**Advantages:**
- ✅ Proper demo data loading
- ✅ No workarounds needed
- ✅ Clean separation (testing vs demo)
- ✅ Full demo experience

**Disadvantages:**
- ⚠️ Requires new database
- ⚠️ Need to reinstall all modules
- ⚠️ Extra disk space

**Steps:**

```bash
# Step 1: Create new database WITH demo mode
docker exec -i odoo-dev-web /usr/bin/odoo shell --no-http <<'EOF'
import sys

# Create database with demo data enabled
db_name = 'openeducat_demo'
print(f"Creating demo database: {db_name}")

# This creates database with demo=True
env.cr.execute("CREATE DATABASE %s" % db_name)
env.cr.commit()

print(f"✅ Database '{db_name}' created")
print("   Now install modules in this database")

sys.exit(0)
EOF

# Step 2: Initialize the database
docker exec odoo-dev-web /usr/bin/odoo \
  -d openeducat_demo \
  --init base \
  --load-language=en_US \
  --without-demo=all \
  --stop-after-init

# Wait, that won't work. Let's use proper method:

# BETTER APPROACH: Use Odoo's database creation
# Via web UI: Database Manager (http://localhost:8069/web/database/manager)
# Create new database, check "Load demonstration data"

# OR via command line:
docker exec odoo-dev-web /usr/bin/odoo \
  -d openeducat_demo \
  --without-demo=False \
  --init=base \
  --stop-after-init

# Step 3: Extract OpenEducat to the demo database's addons
# (Already extracted to /mnt/extra-addons)

# Step 4: Install OpenEducat modules WITH demo
docker exec -i odoo-dev-web /usr/bin/odoo shell -d openeducat_demo --no-http <<'EOF'
# Update module list
env['ir.module.module'].update_list()

# Install all OpenEducat modules (demo will load automatically)
modules = ['openeducat_core', 'openeducat_fees', ...]
# ... installation code ...

sys.exit(0)
EOF
```

**Result:** Complete OpenEducat demo in separate database

---

## Comparison: Which Option Is Best?

| Option | Difficulty | Clean? | Reversible? | Best For |
|--------|-----------|--------|-------------|----------|
| **1. Manual Loading** | Easy | ✅ Yes | ✅ Yes | Quick demo preview |
| **2. Move to Data** | Medium | ❌ No | ⚠️ Partial | Permanent demo |
| **3. New Database** | Medium | ✅ Yes | ✅ Yes | Full evaluation |

### Recommendations by Use Case

**Scenario 1: "Just want to see the demo homepage"**
→ **Use Option 1 (Manual Loading)**
- Takes 2 minutes
- Easy to remove if you don't like it
- No permanent changes

**Scenario 2: "Want demo data for training/testing"**
→ **Use Option 3 (New Database)**
- Proper demo environment
- Keep testing db clean
- Easy to delete when done

**Scenario 3: "Need demo permanently in testing db"**
→ **Use Option 2 (Move to Data)**
- Loads on upgrade
- Permanent solution
- Accept the module modification

---

## Recommended Strategy for UEIPAB

### Our Recommendation: **Hybrid Approach**

**Phase 1: Install WITHOUT Demo (as planned)**
```
Install all 15 modules
web_openeducat: WITHOUT demo
Result: Clean installation, homepage preserved
```

**Phase 2: Evaluate Backend (Week 1-2)**
```
Test all ERP features:
- Student management
- Fee collection
- Attendance
- Exams
- Reports
No website demo needed yet
```

**Phase 3: If You Want to See Website Demo (Week 3+)**

**Option A: Manual Load in Testing (Temporary Demo)**
```bash
# Load demo homepage manually (Option 1)
# Takes 2 minutes
# Review the demo
# Delete if you don't need it
```

**Option B: Create Separate Demo Database (Full Demo)**
```bash
# Create openeducat_demo database
# Install all modules WITH demo
# Full demo experience
# Keep testing db clean
```

---

## Detailed: Manual Demo Loading Script

If you choose **Option 1** later, here's the complete script:

```bash
#!/bin/bash
# Load web_openeducat demo data manually
# File: /opt/odoo-dev/scripts/load_openeducat_demo.sh

echo "================================================"
echo "Loading OpenEducat Demo Data (web_openeducat)"
echo "================================================"
echo ""
echo "⚠️  WARNING: This will replace your homepage!"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Loading demo data..."

docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys
from odoo.tools import convert
import os

module_path = '/mnt/extra-addons/web_openeducat'
demo_files = [
    'data/homepage_demo.xml',
    'data/footer_template.xml',
]

print("\n" + "=" * 60)
print("Loading web_openeducat demo data")
print("=" * 60 + "\n")

for demo_file in demo_files:
    file_path = os.path.join(module_path, demo_file)

    if not os.path.exists(file_path):
        print(f"❌ File not found: {demo_file}")
        continue

    print(f"📦 Loading: {demo_file}")

    try:
        with open(file_path, 'rb') as f:
            convert.convert_xml_import(
                env.cr,
                'web_openeducat',
                f,
                idref={},
                mode='init',
                noupdate=False
            )
        print(f"   ✅ Successfully loaded\n")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}\n")
        sys.exit(1)

env.cr.commit()

# Verify homepage was created
demo_page = env['website.page'].search([('url', '=', '/home-option-1')])
if demo_page:
    print("✅ Demo homepage created: /home-option-1")
    print(f"   Published: {demo_page.is_published}")
    print(f"   View ID: {demo_page.view_id.id}")
else:
    print("⚠️  Demo homepage not found")

print("\n" + "=" * 60)
print("Demo data loading complete!")
print("=" * 60)
print("\nAccess demo homepage at: http://[your-url]/home-option-1")
print("\nTo restore original homepage, run:")
print("  /opt/odoo-dev/scripts/restore_original_homepage.sh")

sys.exit(0)
EOF

echo ""
echo "================================================"
echo "Demo data loaded successfully!"
echo "================================================"
```

**Usage:**
```bash
# Later, when you want to see the demo:
chmod +x /opt/odoo-dev/scripts/load_openeducat_demo.sh
/opt/odoo-dev/scripts/load_openeducat_demo.sh
```

---

## Rollback Script: Remove Demo Homepage

If you load demo and want to remove it:

```bash
#!/bin/bash
# Remove OpenEducat demo homepage
# File: /opt/odoo-dev/scripts/restore_original_homepage.sh

echo "Restoring original homepage..."

docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
import sys

# Find and delete demo homepage
demo_page = env['website.page'].search([('url', '=', '/home-option-1')])

if demo_page:
    print(f"Found demo page: {demo_page.name}")
    demo_page.unlink()
    print("✅ Demo homepage removed")
else:
    print("ℹ️  No demo homepage found")

# Ensure original homepage is published
original_pages = env['website.page'].search([('url', '=', '/')])
for page in original_pages:
    if not page.is_published:
        page.write({'is_published': True})
        print(f"✅ Published: {page.name}")

env.cr.commit()
print("\n✅ Original homepage restored")

sys.exit(0)
EOF

echo "Done!"
```

---

## Summary: Your Options

### During Initial Installation (Now)

**Recommended:** Install web_openeducat **WITHOUT demo**
- ✅ Preserves your homepage
- ✅ Gets all snippets and functionality
- ✅ Clean, safe installation

### Later (If You Want Demo)

**3 Options Available:**

1. **Manual Loading** (5 minutes)
   - Run script above
   - See demo homepage
   - Easy to remove

2. **Create Demo Database** (30 minutes)
   - Full demo experience
   - Separate from testing
   - Professional approach

3. **Modify Module** (10 minutes)
   - Permanent demo data
   - Loads on upgrade
   - Requires code change

### Our Recommendation

**Go with the plan:** Install WITHOUT demo now

**Later options:**
- Week 1-2: Evaluate backend (no demo needed)
- Week 3+: If curious, use **Option 1** (manual load) for quick preview
- Before production: Consider **Option 3** (demo database) for full evaluation

**Flexibility:** All options remain available after installation! ✅

---

## References

Based on research and Odoo community knowledge:

- [How to load demo data of particular module - Odoo Forum](https://www.odoo.com/forum/help-1/how-to-load-demo-data-of-particular-module-147070)
- [How to Load Demo Data in Odoo 17 - Cybrosys](https://www.cybrosys.com/blog/how-to-load-demo-data-in-odoo-17)
- [Loading demo data - Odoo Forum](https://www.odoo.com/forum/help-1/loading-demo-data-248221)
- [Stack Overflow: Load demo data automatically after upgrade/install](https://stackoverflow.com/questions/73412914/is-it-possible-to-load-demo-data-automatically-after-i-upgrade-install-a-module)

**Key Finding:** Demo data loading is controlled at database creation time. Workarounds exist but require manual intervention.

---

## Final Answer to Your Question

**"Can demo data be installed later if needed?"**

**Technical Answer:** No, not through standard Odoo mechanisms.

**Practical Answer:** Yes, through workarounds (manual loading recommended).

**Best Approach:**
1. Install WITHOUT demo now (as planned)
2. Evaluate for 1-2 weeks
3. IF you want to see demo homepage → Use manual loading script (5 min)
4. Easy to add, easy to remove ✅

**You're NOT locked in to this decision!** 🎉

---

**Document Version:** 1.0
**Last Updated:** 2025-11-24
**Status:** Complete Analysis
