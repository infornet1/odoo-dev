# Bank Reconciliation Integration Plan

**Status:** Draft for Review
**Created:** 2025-12-25
**Author:** Claude Code Assessment

---

## Executive Summary

Integrate the existing `odoo_api_bridge` bank statement automation system with Odoo 17 Community Edition's reconciliation module to provide a unified bank reconciliation workflow.

---

## Current Infrastructure Assessment

### Odoo 17 Environment

| Module | Version | Status |
|--------|---------|--------|
| `account_reconcile_oca` | 17.0.1.5.24 | Installed |
| `account_reconcile_model_oca` | - | Installed |
| `account_statement_base` | 17.0.1.6.0 | Installed |
| `base_accounting_kit` | - | Installed |

**Bank Journals Configured:** 13 (6 bank, 7 cash)

| Journal | Type | Currency | Account |
|---------|------|----------|---------|
| Banco de Venezuela | Bank | USD | 01020445340007673100 |
| Banco Venezuela | Bank | VEB | - |
| Banco Mercantil | Bank | VEB | - |
| Banco Mercantil USD | Bank | USD | - |
| Banco Plaza | Bank | VEB | - |
| Banplus | Bank | VEB | - |
| Bancamiga | Bank | VEB | - |
| Zelle | Bank | USD | - |

**Existing Reconciliation Models:**
1. Perfect invoice matching (`invoice_matching`)
2. Partial payment matching (`invoice_matching`)

---

### odoo_api_bridge Infrastructure

**Location:** `/var/www/dev/odoo_api_bridge/`

#### Bank Statement Parser
- **File:** `bank_statement_parser.py`
- **Supported Banks:**
  - `BDV` - Banco de Venezuela (TXT format)
  - `BM` - Banco Mercantil (CSV format)
  - `BP` - Banplus (CSV format)
  - `BCP` - Banco Plaza (CSV semicolon-delimited)

#### BDV Automation
- **File:** `bdv_scraper.py`
- **Features:**
  - Automated SMS 2FA via Huawei router
  - Daily CRON at 6:00 AM VET
  - Auto-download to `/var/www/dev/odoo_api_bridge/bdv_downloads/`
  - Email notifications to finanzas@ueipab.edu.ve

#### Database Storage (MariaDB)
- **Database:** `payroll_db`
- **Table:** `bank_transactions`

```sql
CREATE TABLE bank_transactions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    transaction_date DATE NOT NULL,
    concept VARCHAR(255) NOT NULL,
    reference VARCHAR(255) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    balance DECIMAL(15,2) NOT NULL,
    bank_code VARCHAR(10) DEFAULT 'BDV',
    bank_name VARCHAR(100) DEFAULT 'Banco de Venezuela',
    account_code VARCHAR(50) DEFAULT '1.1.01.02.001',
    odoo_move_line_id INT NULL,
    status VARCHAR(50) DEFAULT 'unmatched',
    reconciliation_date DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Current Transaction Statistics (as of 2025-12-25)

| Bank | Count | Date Range |
|------|-------|------------|
| BDV | 3,653 | 2025-06-01 → 2025-12-24 |
| BM | 411 | 2025-06-03 → 2025-11-06 |
| BP | 75 | 2025-07-02 → 2025-11-05 |
| BCP | 6 | 2025-07-31 → 2025-10-31 |
| **Total** | **4,145** | |

| Status | Count | Percentage |
|--------|-------|------------|
| matched | 3,464 | 83.6% |
| unmatched | 583 | 14.1% |
| pdv_matched | 69 | 1.7% |
| bio_matched | 25 | 0.6% |
| ignored | 4 | 0.1% |

---

## Integration Options

### Option A: Sync Script (Recommended)

**Approach:** Create a synchronization layer between MariaDB and Odoo

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   BDV Scraper       │     │   MariaDB           │     │   Odoo 17           │
│   (Daily CRON)      │────▶│   bank_transactions │────▶│   statement.line    │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                      ▲                           │
                                      │                           │
                                      └───────────────────────────┘
                                         Status Sync Back
```

**Pros:**
- Preserves existing working automation
- Minimal risk to production systems
- Incremental implementation
- Can run in parallel with existing reconciliation UI

**Cons:**
- Dual data storage (MariaDB + PostgreSQL)
- Requires sync maintenance

**Implementation Steps:**

1. **Create Odoo Module:** `ueipab_bank_sync`
   - Scheduled action to pull from MariaDB
   - Create `account.bank.statement` per period/bank
   - Create `account.bank.statement.line` records
   - Map bank_code to journal_id

2. **Field Mapping:**
   | MariaDB | Odoo | Notes |
   |---------|------|-------|
   | `transaction_date` | `date` | Direct |
   | `amount` | `amount` | Direct |
   | `concept` | `payment_ref` | Label |
   | `reference` | `ref` | Bank ref |
   | `bank_code` | `journal_id` | Lookup |
   | `id` | `internal_index` | For sync |

3. **Status Sync Back:**
   - After Odoo reconciliation, update MariaDB status
   - Store `odoo_move_line_id` for cross-reference

4. **Journal Mapping Configuration:**
   ```python
   BANK_JOURNAL_MAP = {
       'BDV': 157,   # Banco de Venezuela (USD)
       'BM': 161,    # Banco Mercantil (VEB)
       'BP': 164,    # Banplus (VEB)
       'BCP': 163,   # Banco Plaza (VEB)
   }
   ```

---

### Option B: Full OCA Module Stack (DETAILED)

**Selected Approach:** Custom Odoo module using odoo_api_bridge as data source

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPTION B ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────────────┐   │
│  │ BDV Scraper  │───▶│   MariaDB    │◀──▶│  ueipab_bank_reconcile      │   │
│  │ (6AM Daily)  │    │ payroll_db   │    │  (Custom Odoo 17 Module)    │   │
│  └──────────────┘    │              │    │                             │   │
│                      │ bank_        │    │  ┌─────────────────────┐    │   │
│  ┌──────────────┐    │ transactions │    │  │ MariaDB Connector   │    │   │
│  │ Bank Files   │───▶│              │    │  │ (mysql-connector)   │    │   │
│  │ BM/BP/BCP    │    └──────────────┘    │  └─────────────────────┘    │   │
│  └──────────────┘           │            │            │                │   │
│                             │            │            ▼                │   │
│                             │            │  ┌─────────────────────┐    │   │
│                             │            │  │ Import Wizard       │    │   │
│                             └───────────▶│  │ (Pull from MariaDB) │    │   │
│                                          │  └─────────────────────┘    │   │
│                                          │            │                │   │
│                                          │            ▼                │   │
│                                          │  ┌─────────────────────┐    │   │
│                                          │  │ account.bank.       │    │   │
│                                          │  │ statement.line      │    │   │
│                                          │  └─────────────────────┘    │   │
│                                          │            │                │   │
│                                          │            ▼                │   │
│                                          │  ┌─────────────────────┐    │   │
│                                          │  │ OCA Reconcile       │    │   │
│                                          │  │ Widget (installed)  │    │   │
│                                          │  └─────────────────────┘    │   │
│                                          │            │                │   │
│                                          │            ▼                │   │
│                                          │  ┌─────────────────────┐    │   │
│                                          │  │ Status Sync Back    │    │   │
│                                          │  │ to MariaDB          │    │   │
│                                          │  └─────────────────────┘    │   │
│                                          └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Module Structure: `ueipab_bank_reconcile`

```
ueipab_bank_reconcile/
├── __init__.py
├── __manifest__.py
├── data/
│   └── ir_cron.xml                    # Scheduled sync actions
├── models/
│   ├── __init__.py
│   ├── mariadb_connector.py           # MariaDB connection handler
│   ├── bank_statement_sync.py         # Sync logic model
│   ├── account_bank_statement.py      # Statement extensions
│   └── account_bank_statement_line.py # Line extensions
├── wizards/
│   ├── __init__.py
│   ├── import_from_mariadb.py         # Manual import wizard
│   └── import_from_mariadb_views.xml
├── views/
│   ├── bank_statement_views.xml
│   ├── res_config_settings_views.xml
│   └── menuitem.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
└── static/
    └── description/
        └── icon.png
```

#### Key Components

##### 1. MariaDB Connector (`models/mariadb_connector.py`)

```python
# Pseudo-code for reference
class MariaDBConnector(models.AbstractModel):
    _name = 'ueipab.mariadb.connector'
    _description = 'MariaDB Connection Handler'

    def _get_connection(self):
        """Get MariaDB connection using system parameters"""
        params = self.env['ir.config_parameter'].sudo()
        return mysql.connector.connect(
            host=params.get_param('ueipab_bank.mariadb_host'),
            database=params.get_param('ueipab_bank.mariadb_db'),
            user=params.get_param('ueipab_bank.mariadb_user'),
            password=params.get_param('ueipab_bank.mariadb_password')
        )

    def get_unsynced_transactions(self, bank_code=None, date_from=None):
        """Fetch transactions not yet synced to Odoo"""
        # Query bank_transactions where odoo_statement_line_id IS NULL
        pass

    def mark_as_synced(self, mariadb_id, odoo_line_id):
        """Update MariaDB with Odoo reference"""
        pass

    def sync_reconciliation_status(self, odoo_line_id, status):
        """Sync back reconciliation status to MariaDB"""
        pass
```

##### 2. Import Wizard (`wizards/import_from_mariadb.py`)

```python
# Pseudo-code for reference
class ImportFromMariaDB(models.TransientModel):
    _name = 'ueipab.import.mariadb.wizard'
    _description = 'Import Bank Transactions from MariaDB'

    bank_code = fields.Selection([
        ('BDV', 'Banco de Venezuela'),
        ('BM', 'Banco Mercantil'),
        ('BP', 'Banplus'),
        ('BCP', 'Banco Plaza'),
        ('ALL', 'All Banks')
    ], default='ALL')
    date_from = fields.Date()
    date_to = fields.Date()
    status_filter = fields.Selection([
        ('unmatched', 'Unmatched Only'),
        ('all', 'All Transactions')
    ], default='unmatched')

    def action_import(self):
        """Import transactions from MariaDB to Odoo statements"""
        # 1. Fetch from MariaDB
        # 2. Group by bank/month
        # 3. Create/get statement per group
        # 4. Create statement lines
        # 5. Update MariaDB with Odoo IDs
        pass
```

##### 3. Journal Mapping Configuration

| MariaDB bank_code | Odoo Journal ID | Journal Name | Currency |
|-------------------|-----------------|--------------|----------|
| `BDV` | 157 | Banco de Venezuela | USD |
| `BDV` | 162 | Banco Venezuela | VEB |
| `BM` | 161 | Banco Mercantil | VEB |
| `BM` | 160 | Banco Mercantil USD | USD |
| `BP` | 164 | Banplus | VEB |
| `BCP` | 163 | Banco Plaza | VEB |

##### 4. Reconciliation Model Extensions

Create Venezuelan-specific reconciliation models:

| Model Name | Rule Type | Match Pattern |
|------------|-----------|---------------|
| Payroll Match | `invoice_matching` | `NOMINA` in concept |
| Commission Match | `writeoff_suggestion` | `COMISION PDV` pattern |
| Transfer Match | `invoice_matching` | `TRANSF` reference |
| Tax Payment | `writeoff_suggestion` | `SENIAT`, `IVSS`, `FAOV` |

##### 5. Scheduled Actions (CRON)

```xml
<record id="ir_cron_sync_bank_transactions" model="ir.cron">
    <field name="name">Sync Bank Transactions from MariaDB</field>
    <field name="model_id" ref="model_ueipab_bank_sync"/>
    <field name="state">code</field>
    <field name="code">model.cron_sync_transactions()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">hours</field>
    <field name="numbercall">-1</field>
    <field name="active">True</field>
</record>
```

#### Dependencies

**OCA Modules (Already Installed):**
- `account_reconcile_oca` (v17.0.1.5.24)
- `account_statement_base` (v17.0.1.6.0)
- `account_reconcile_model_oca`

**Python Packages (to add):**
- `mysql-connector-python` (for MariaDB access)

**No Additional OCA Modules Required** - We leverage the existing reconcile infrastructure.

#### Pros (Revised)

- Uses existing, proven odoo_api_bridge infrastructure
- Native Odoo OCA reconciliation widget
- Single reconciliation source of truth (Odoo)
- Bidirectional sync keeps MariaDB updated
- No changes to BDV scraper automation
- Incremental migration possible

#### Cons (Revised)

- Custom module development required
- MariaDB dependency from Odoo server
- Two databases to maintain
- Need to handle sync failures gracefully

#### Implementation Phases

##### Phase 1: Module Foundation (Week 1)
1. Create module skeleton
2. Implement MariaDB connector
3. Add system parameter configuration
4. Test connection from Odoo to MariaDB

##### Phase 2: Import Wizard (Week 2)
1. Build import wizard UI
2. Implement transaction fetch logic
3. Create statement grouping logic
4. Implement statement line creation
5. Test with small batch (10-20 transactions)

##### Phase 3: Reconciliation Configuration (Week 3)
1. Create Venezuelan reconciliation models
2. Configure matching rules for common patterns
3. Test OCA widget with imported data
4. Validate matching accuracy

##### Phase 4: Sync Back Implementation (Week 4)
1. Add post-reconciliation hook
2. Implement MariaDB status update
3. Add sync error handling
4. Test full round-trip workflow

##### Phase 5: Automation & Testing (Week 5)
1. Implement scheduled sync CRON
2. Add email notifications
3. Full integration testing
4. User acceptance testing

##### Phase 6: Production Deployment
1. Deploy to production
2. Import historical data (optional)
3. Parallel run with existing system
4. User training
5. Deprecate old reconciliation UI

---

### Option C: Hybrid Approach

**Approach:** Keep MariaDB for raw import, use Odoo for reconciliation only

1. BDV Scraper continues to MariaDB (unchanged)
2. Daily sync job pushes to Odoo statements
3. Users reconcile in Odoo OCA widget
4. No sync back needed - Odoo is source of truth for reconciliation

---

## Recommended Implementation: Option B (Under Review)

> **Note:** Option B is currently being explored as it provides the best balance between
> leveraging existing infrastructure and native Odoo integration.

### Why Option B?

1. **Preserves BDV Automation** - The proven daily scraper continues unchanged
2. **Uses OCA Widget** - Already installed and battle-tested reconciliation UI
3. **Bidirectional Sync** - MariaDB remains the import source, Odoo becomes reconciliation source
4. **Single Module** - All custom logic in one Odoo module (`ueipab_bank_reconcile`)
5. **Gradual Migration** - Can run parallel with existing `odoo_api_bridge` reconciliation UI

### Implementation Summary (Option B)

See [Option B: Full OCA Module Stack (DETAILED)](#option-b-full-oca-module-stack-detailed) above for complete architecture.

| Phase | Focus | Duration |
|-------|-------|----------|
| 1 | Module Foundation + MariaDB Connector | Week 1 |
| 2 | Import Wizard + Statement Creation | Week 2 |
| 3 | Reconciliation Models + Testing | Week 3 |
| 4 | Sync Back to MariaDB | Week 4 |
| 5 | CRON Automation + UAT | Week 5 |
| 6 | Production Deployment | Week 6 |

---

## Technical Considerations

### Currency Handling
- BDV transactions are in VEB
- Odoo journals have mixed currencies (USD/VEB)
- Need proper currency conversion at import

### Duplicate Prevention
- Use `reference` + `date` + `amount` as unique key
- Check existing statement lines before import
- Handle re-imports gracefully

### Performance
- 4,000+ transactions to import initially
- Batch processing recommended
- Consider date range filters for incremental sync

### Security
- MariaDB credentials in Odoo system parameters
- Restrict sync to backend users only
- Audit logging for all imports

---

## Open Questions

1. **Currency Strategy:** Should all transactions be imported in original currency or converted to USD?

2. **Historical Data:** Import all 4,145 transactions or start fresh from a specific date?

3. **Existing Matches:** Should already-matched transactions in MariaDB be imported as reconciled in Odoo?

4. **Dual System:** Keep MariaDB reconciliation UI or deprecate in favor of Odoo?

5. **Statement Grouping:** One statement per day? Per month? Per import batch?

---

## Next Steps

### Immediate (Pending Review)
- [ ] Review and approve Option B approach
- [ ] Answer open questions below
- [ ] Verify MariaDB connectivity from Odoo Docker container

### Phase 1 Preparation
- [ ] Create `ueipab_bank_reconcile` module skeleton
- [ ] Install `mysql-connector-python` in Odoo container
- [ ] Configure MariaDB system parameters
- [ ] Test basic connectivity

### Validation
- [ ] Import 10-20 test transactions
- [ ] Verify OCA reconcile widget displays them
- [ ] Test manual reconciliation workflow
- [ ] Validate statement line creation

---

## References

- [OCA/bank-statement-import](https://github.com/OCA/bank-statement-import) - 17.0 branch
- [OCA/account-reconcile](https://github.com/OCA/account-reconcile) - Reconciliation modules
- `/var/www/dev/odoo_api_bridge/docs/apps/CLAUDE_BDV_AUTOMATION.md` - BDV scraper documentation
- `/var/www/dev/odoo_api_bridge/bank_statement_parser.py` - Parser implementation
