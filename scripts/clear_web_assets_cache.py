#!/usr/bin/env python3
"""
Clear Web Assets Cache
=======================

Clear cached web assets that might be preventing menu from appearing.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("CLEARING WEB ASSETS CACHE")
print("="*80)
print()

# Clear web assets cache
Attachment = env['ir.attachment']

# Find all web assets
web_assets = Attachment.search([
    ('name', 'like', 'web_assets_%'),
    ('res_model', '=', 'ir.ui.view')
])

print(f"Found {len(web_assets)} cached web assets")
print()

if web_assets:
    print("Deleting cached assets:")
    for asset in web_assets:
        print(f"  - {asset.name}")

    web_assets.unlink()
    env.cr.commit()
    print()
    print("✅ Web assets cache cleared!")
else:
    print("No cached web assets found")

print()

# Also clear any menu-related cache
print("Updating menu modification timestamps...")
from datetime import datetime
Menu = env['ir.ui.menu']
all_menus = Menu.search([])
all_menus.write({'write_date': datetime.now()})
env.cr.commit()

print(f"✅ Updated {len(all_menus)} menu timestamps")
print()

print("="*80)
print("CACHE CLEARED - Next steps:")
print("="*80)
print("1. Restart Odoo server: docker restart odoo-dev-web")
print("2. Hard reload browser: Ctrl+Shift+R")
print("3. Check menu again")
print()
