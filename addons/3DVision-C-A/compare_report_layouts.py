#!/usr/bin/env python3
"""
Comprehensive Report Layout Comparison Tool
Compare all layout-affecting parameters between Production and Testing databases
"""

import psycopg2
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

class ReportLayoutComparator:
    def __init__(self):
        self.production_config = {
            'host': 'localhost',  # Update with your production DB host
            'database': 'DB_UEIPAB',
            'user': 'odoo',  # Update with your DB user
            'password': 'your_password',  # Update with your DB password
            'port': 5432
        }

        self.testing_config = {
            'host': 'localhost',  # Update with your testing DB host
            'database': 'your_testing_db',  # Update with your testing DB name
            'user': 'odoo',  # Update with your DB user
            'password': 'your_password',  # Update with your DB password
            'port': 5432
        }

    def connect_to_db(self, config: Dict[str, str]):
        """Establish database connection"""
        try:
            conn = psycopg2.connect(**config)
            return conn
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None

    def execute_analysis_queries(self, conn) -> Dict[str, List[Dict]]:
        """Execute all analysis queries and return results"""

        queries = {
            'paper_formats': """
                SELECT 'PAPER_FORMAT_ANALYSIS' as analysis_type,
                       name, format, page_height, page_width,
                       margin_top, margin_bottom, margin_left, margin_right,
                       orientation, header_line, header_spacing,
                       disable_shrinking, print_page_width, print_page_height,
                       dpi, default
                FROM report_paperformat
                WHERE name IN ('US Letter', 'US Half Letter', 'Letter', 'A4')
                ORDER BY name;
            """,

            'report_actions': """
                SELECT 'REPORT_ACTION_ANALYSIS' as analysis_type,
                       name, model, report_type, report_name,
                       report_file, paperformat_id, print_report_name,
                       multi, attachment_use, attachment
                FROM ir_actions_report
                WHERE report_name LIKE '%freeform%'
                   OR name LIKE '%freeform%'
                   OR model = 'account.move'
                ORDER BY name;
            """,

            'company_settings': """
                SELECT 'COMPANY_SETTINGS_ANALYSIS' as analysis_type,
                       c.name as company_name, c.paperformat_id,
                       pf.name as paperformat_name, c.font,
                       c.primary_color, c.secondary_color,
                       c.logo_web_size, c.external_report_layout_id,
                       erl.name as external_layout_name
                FROM res_company c
                LEFT JOIN report_paperformat pf ON c.paperformat_id = pf.id
                LEFT JOIN ir_ui_view erl ON c.external_report_layout_id = erl.id
                ORDER BY c.name;
            """,

            'system_config': """
                SELECT 'SYSTEM_CONFIG_ANALYSIS' as analysis_type,
                       key, value
                FROM ir_config_parameter
                WHERE key LIKE '%report%'
                   OR key LIKE '%pdf%'
                   OR key LIKE '%wkhtmltopdf%'
                   OR key LIKE '%font%'
                   OR key LIKE '%dpi%'
                   OR key LIKE '%margin%'
                   OR key LIKE '%paper%'
                   OR key LIKE '%layout%'
                   OR key LIKE '%print%'
                ORDER BY key;
            """,

            'css_assets': """
                SELECT 'CSS_ASSETS_ANALYSIS' as analysis_type,
                       name, bundle, directive, target,
                       active, sequence
                FROM ir_asset
                WHERE name LIKE '%report%'
                   OR name LIKE '%css%'
                   OR name LIKE '%style%'
                   OR bundle LIKE '%report%'
                ORDER BY bundle, sequence;
            """,

            'qweb_templates': """
                SELECT 'QWEB_TEMPLATE_ANALYSIS' as analysis_type,
                       name, key, type, active, priority,
                       mode, inherit_id, model,
                       CASE
                           WHEN LENGTH(arch_db) > 500
                           THEN LEFT(arch_db, 500) || '...[TRUNCATED]'
                           ELSE arch_db
                       END as arch_db_preview
                FROM ir_ui_view
                WHERE name LIKE '%freeform%'
                   OR key LIKE '%freeform%'
                   OR name LIKE '%invoice%'
                   OR key LIKE '%invoice%'
                   OR name LIKE '%report%'
                   OR arch_db LIKE '%freeform%'
                   OR model = 'account.move'
                ORDER BY name;
            """,

            'currency_precision': """
                SELECT 'CURRENCY_PRECISION_ANALYSIS' as analysis_type,
                       c.name as currency_name, c.symbol,
                       c.position, c.rounding, c.decimal_places,
                       c.active
                FROM res_currency c
                WHERE c.active = true
                ORDER BY c.name;
            """,

            'font_settings': """
                SELECT 'FONT_ANALYSIS' as analysis_type,
                       'Company Font Settings' as category,
                       name as company_name, font as font_setting
                FROM res_company
                WHERE font IS NOT NULL
                UNION ALL
                SELECT 'FONT_ANALYSIS' as analysis_type,
                       'System Font Parameters' as category,
                       key as parameter_name, value as font_value
                FROM ir_config_parameter
                WHERE key LIKE '%font%';
            """,

            'modules': """
                SELECT 'MODULE_ANALYSIS' as analysis_type,
                       name, state, latest_version, author
                FROM ir_module_module
                WHERE (name LIKE '%report%'
                   OR name LIKE '%pdf%'
                   OR name LIKE '%account%'
                   OR name LIKE '%invoice%')
                   AND state = 'installed'
                ORDER BY name;
            """
        }

        results = {}
        cursor = conn.cursor()

        for query_name, query in queries.items():
            try:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                results[query_name] = [dict(zip(columns, row)) for row in rows]
                print(f"✓ Executed {query_name}: {len(rows)} records")
            except Exception as e:
                print(f"✗ Error executing {query_name}: {e}")
                results[query_name] = []

        cursor.close()
        return results

    def compare_results(self, prod_results: Dict, test_results: Dict) -> Dict:
        """Compare results between production and testing"""
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'differences': {},
            'summary': {}
        }

        for query_name in prod_results.keys():
            if query_name not in test_results:
                comparison['differences'][query_name] = {
                    'status': 'missing_in_testing',
                    'production_count': len(prod_results[query_name]),
                    'testing_count': 0
                }
                continue

            prod_data = prod_results[query_name]
            test_data = test_results[query_name]

            differences = []

            # Compare counts
            if len(prod_data) != len(test_data):
                differences.append({
                    'type': 'count_mismatch',
                    'production_count': len(prod_data),
                    'testing_count': len(test_data)
                })

            # Compare content
            prod_dict = {self._get_record_key(record): record for record in prod_data}
            test_dict = {self._get_record_key(record): record for record in test_data}

            # Find records only in production
            only_in_prod = set(prod_dict.keys()) - set(test_dict.keys())
            if only_in_prod:
                differences.append({
                    'type': 'only_in_production',
                    'records': [prod_dict[key] for key in only_in_prod]
                })

            # Find records only in testing
            only_in_test = set(test_dict.keys()) - set(prod_dict.keys())
            if only_in_test:
                differences.append({
                    'type': 'only_in_testing',
                    'records': [test_dict[key] for key in only_in_test]
                })

            # Find different values for same records
            common_keys = set(prod_dict.keys()) & set(test_dict.keys())
            for key in common_keys:
                prod_record = prod_dict[key]
                test_record = test_dict[key]

                field_diffs = {}
                for field in prod_record.keys():
                    if field in test_record:
                        if prod_record[field] != test_record[field]:
                            field_diffs[field] = {
                                'production': prod_record[field],
                                'testing': test_record[field]
                            }

                if field_diffs:
                    differences.append({
                        'type': 'field_differences',
                        'record_key': key,
                        'fields': field_diffs
                    })

            if differences:
                comparison['differences'][query_name] = differences

            # Summary statistics
            comparison['summary'][query_name] = {
                'production_records': len(prod_data),
                'testing_records': len(test_data),
                'differences_found': len(differences) > 0
            }

        return comparison

    def _get_record_key(self, record: Dict) -> str:
        """Generate a unique key for a record"""
        if 'name' in record and record['name']:
            return record['name']
        elif 'key' in record and record['key']:
            return record['key']
        elif 'id' in record:
            return str(record['id'])
        else:
            return str(hash(frozenset(record.items())))

    def save_results(self, filename: str, data: Any):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Results saved to {filename}")

    def run_comparison(self):
        """Run the complete comparison analysis"""
        print("Starting comprehensive report layout analysis...")
        print("=" * 60)

        # Connect to production database
        print("Connecting to production database...")
        prod_conn = self.connect_to_db(self.production_config)
        if not prod_conn:
            print("Failed to connect to production database")
            return

        # Connect to testing database
        print("Connecting to testing database...")
        test_conn = self.connect_to_db(self.testing_config)
        if not test_conn:
            print("Failed to connect to testing database")
            prod_conn.close()
            return

        try:
            # Execute analysis on production
            print("\nAnalyzing production database...")
            prod_results = self.execute_analysis_queries(prod_conn)

            # Execute analysis on testing
            print("\nAnalyzing testing database...")
            test_results = self.execute_analysis_queries(test_conn)

            # Compare results
            print("\nComparing results...")
            comparison = self.compare_results(prod_results, test_results)

            # Save individual results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_results(f"production_analysis_{timestamp}.json", prod_results)
            self.save_results(f"testing_analysis_{timestamp}.json", test_results)
            self.save_results(f"comparison_results_{timestamp}.json", comparison)

            # Print summary
            self.print_summary(comparison)

        finally:
            prod_conn.close()
            test_conn.close()

    def print_summary(self, comparison: Dict):
        """Print comparison summary"""
        print("\n" + "=" * 60)
        print("COMPARISON SUMMARY")
        print("=" * 60)

        total_differences = len(comparison['differences'])
        if total_differences == 0:
            print("✓ No differences found between environments!")
            return

        print(f"✗ Found differences in {total_differences} areas:")

        for area, diffs in comparison['differences'].items():
            print(f"\n{area.upper()}:")
            if isinstance(diffs, list):
                for diff in diffs:
                    if diff['type'] == 'count_mismatch':
                        print(f"  - Count mismatch: Prod={diff['production_count']}, Test={diff['testing_count']}")
                    elif diff['type'] == 'field_differences':
                        print(f"  - Field differences in record: {diff['record_key']}")
                        for field, values in diff['fields'].items():
                            print(f"    {field}: Prod='{values['production']}' vs Test='{values['testing']}'")
                    elif diff['type'] == 'only_in_production':
                        print(f"  - {len(diff['records'])} record(s) only in production")
                    elif diff['type'] == 'only_in_testing':
                        print(f"  - {len(diff['records'])} record(s) only in testing")
            else:
                print(f"  - {diffs}")

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
Report Layout Comparison Tool

This script compares all layout-affecting parameters between production and testing databases.

Before running:
1. Update database connection settings in the script
2. Ensure you have psycopg2 installed: pip install psycopg2-binary
3. Ensure database connectivity from this machine

The script will:
- Connect to both databases
- Execute comprehensive analysis queries
- Compare results and identify differences
- Save detailed results to JSON files
- Display summary of findings

Critical areas analyzed:
- Paper formats and margins
- Report action configurations
- Company settings
- System configuration parameters
- CSS and styling assets
- QWeb template customizations
- Font and typography settings
- Currency and precision settings
- Module versions and states
        """)
        return

    comparator = ReportLayoutComparator()
    comparator.run_comparison()

if __name__ == "__main__":
    main()