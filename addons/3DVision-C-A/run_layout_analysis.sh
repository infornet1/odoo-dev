#!/bin/bash

# Report Layout Analysis Runner
# This script helps execute the comprehensive layout analysis

echo "=========================================="
echo "Report Layout Analysis Tool"
echo "=========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROD_DB="DB_UEIPAB"
TEST_DB="your_testing_db_name"  # Update this
DB_USER="odoo"                  # Update this
DB_HOST="localhost"             # Update this
DB_PORT="5432"                  # Update this

# Files
SQL_FILE="critical_layout_checks.sql"
ANALYSIS_FILE="report_layout_analysis.sql"
PYTHON_SCRIPT="compare_report_layouts.py"

echo -e "${BLUE}Available analysis options:${NC}"
echo "1. Run critical layout checks manually (SQL queries)"
echo "2. Run comprehensive Python analysis (requires psycopg2)"
echo "3. Export results for manual comparison"
echo "4. Show environment fingerprint only"
echo "5. Check prerequisites"
echo

read -p "Select option (1-5): " option

case $option in
    1)
        echo -e "\n${YELLOW}Running critical layout checks...${NC}"
        echo "You'll need to execute these queries manually in your database tool."
        echo
        echo -e "${GREEN}Critical checks to run in BOTH databases:${NC}"
        echo "1. Paper format comparison"
        echo "2. Report action settings"
        echo "3. Company layout settings"
        echo "4. PDF generation parameters"
        echo "5. CSS and styling"
        echo "6. Template modifications"
        echo "7. Currency formatting"
        echo "8. Font and language settings"
        echo "9. Sequence formats"
        echo "10. Module versions"
        echo
        echo -e "${BLUE}SQL file ready:${NC} $SQL_FILE"
        echo
        echo "Instructions:"
        echo "1. Open your database management tool (pgAdmin, DBeaver, etc.)"
        echo "2. Connect to production database: $PROD_DB"
        echo "3. Run the queries from $SQL_FILE"
        echo "4. Save/export the results"
        echo "5. Connect to testing database: $TEST_DB"
        echo "6. Run the same queries"
        echo "7. Compare results field by field"
        echo
        echo "Pay special attention to the ENVIRONMENT_FINGERPRINT query - if the"
        echo "fingerprints don't match, drill down into the specific differences."
        ;;

    2)
        echo -e "\n${YELLOW}Checking Python script...${NC}"
        if [[ ! -f "$PYTHON_SCRIPT" ]]; then
            echo -e "${RED}Error: $PYTHON_SCRIPT not found${NC}"
            exit 1
        fi

        echo "Before running the Python script, you need to:"
        echo "1. Install psycopg2: pip install psycopg2-binary"
        echo "2. Update database connection settings in $PYTHON_SCRIPT"
        echo "3. Ensure database connectivity"
        echo
        read -p "Have you completed these steps? (y/n): " ready

        if [[ $ready == "y" || $ready == "Y" ]]; then
            echo -e "\n${GREEN}Running comprehensive analysis...${NC}"
            python3 "$PYTHON_SCRIPT"
        else
            echo "Please complete the prerequisites first."
        fi
        ;;

    3)
        echo -e "\n${YELLOW}Preparing manual export queries...${NC}"

        # Create individual query files for easy copying
        mkdir -p analysis_queries

        # Extract each critical check into separate files
        echo "-- Environment Fingerprint Query" > analysis_queries/01_fingerprint.sql
        sed -n '/ENVIRONMENT_FINGERPRINT/,/-- =============/p' "$SQL_FILE" >> analysis_queries/01_fingerprint.sql

        echo "-- Paper Format Check" > analysis_queries/02_paper_formats.sql
        sed -n '/PAPER_FORMAT_CRITICAL/,/ORDER BY name;/p' "$SQL_FILE" >> analysis_queries/02_paper_formats.sql

        echo "-- Report Actions Check" > analysis_queries/03_report_actions.sql
        sed -n '/REPORT_ACTION_CRITICAL/,/ORDER BY r.name;/p' "$SQL_FILE" >> analysis_queries/03_report_actions.sql

        echo "-- Company Settings Check" > analysis_queries/04_company_settings.sql
        sed -n '/COMPANY_CRITICAL/,/ORDER BY c.name;/p' "$SQL_FILE" >> analysis_queries/04_company_settings.sql

        echo -e "${GREEN}Query files created in analysis_queries/ directory:${NC}"
        ls -la analysis_queries/
        echo
        echo "Instructions for manual comparison:"
        echo "1. Run each query file in PRODUCTION database"
        echo "2. Export results to CSV"
        echo "3. Run same queries in TESTING database"
        echo "4. Export results to CSV with different filename"
        echo "5. Use diff tools or spreadsheet to compare"
        echo
        echo "Start with 01_fingerprint.sql - if fingerprints match, environments are identical"
        ;;

    4)
        echo -e "\n${YELLOW}Environment Fingerprint Query Only:${NC}"
        echo
        echo "Run this query in BOTH databases and compare the fingerprints:"
        echo
        cat << 'EOF'
SELECT
    'ENVIRONMENT_FINGERPRINT' as check_type,
    (SELECT STRING_AGG(
        name || ':' ||
        COALESCE(margin_top::text,'0') || ',' ||
        COALESCE(margin_bottom::text,'0') || ',' ||
        COALESCE(margin_left::text,'0') || ',' ||
        COALESCE(margin_right::text,'0') || ',' ||
        COALESCE(orientation,'Portrait') || ',' ||
        COALESCE(dpi::text,'90'),
        '|'
     ) FROM report_paperformat
     WHERE name IN ('US Letter', 'US Half Letter')
    ) as paper_format_fingerprint,
    (SELECT STRING_AGG(
        c.name || ':pf' || COALESCE(c.paperformat_id::text,'none') ||
        ':font' || COALESCE(c.font,'none'),
        '|'
     ) FROM res_company c
    ) as company_fingerprint,
    (SELECT STRING_AGG(
        name || ':pf' || COALESCE(paperformat_id::text,'none'),
        '|'
     ) FROM ir_actions_report
     WHERE report_name LIKE '%freeform%'
    ) as report_action_fingerprint;
EOF
        echo
        echo -e "${BLUE}If fingerprints are identical, your environments are synchronized.${NC}"
        echo -e "${BLUE}If different, run the full analysis to find specific differences.${NC}"
        ;;

    5)
        echo -e "\n${YELLOW}Checking prerequisites...${NC}"
        echo

        # Check if files exist
        echo -e "${BLUE}File availability:${NC}"
        for file in "$SQL_FILE" "$ANALYSIS_FILE" "$PYTHON_SCRIPT"; do
            if [[ -f "$file" ]]; then
                echo -e "${GREEN}✓${NC} $file"
            else
                echo -e "${RED}✗${NC} $file (missing)"
            fi
        done
        echo

        # Check Python and psycopg2
        echo -e "${BLUE}Python environment:${NC}"
        if command -v python3 &> /dev/null; then
            echo -e "${GREEN}✓${NC} Python 3 available"
            if python3 -c "import psycopg2" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} psycopg2 available"
            else
                echo -e "${YELLOW}⚠${NC} psycopg2 not available (run: pip install psycopg2-binary)"
            fi
        else
            echo -e "${RED}✗${NC} Python 3 not found"
        fi
        echo

        # Check database connectivity (if psql is available)
        echo -e "${BLUE}Database connectivity:${NC}"
        if command -v psql &> /dev/null; then
            echo -e "${GREEN}✓${NC} PostgreSQL client (psql) available"
            echo "You can test connectivity with:"
            echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $PROD_DB -c '\\dt'"
        else
            echo -e "${YELLOW}⚠${NC} psql not found - install PostgreSQL client for direct testing"
        fi
        echo

        echo -e "${BLUE}Manual analysis options:${NC}"
        echo "• Use pgAdmin, DBeaver, or any PostgreSQL client"
        echo "• Connect to both databases"
        echo "• Run the SQL queries from $SQL_FILE"
        echo "• Compare results manually"
        ;;

    *)
        echo "Invalid option selected"
        exit 1
        ;;
esac

echo
echo -e "${GREEN}Analysis complete!${NC}"
echo
echo -e "${BLUE}Key areas to focus on for layout differences:${NC}"
echo "• Margin values (top, bottom, left, right)"
echo "• DPI settings"
echo "• Paper format orientations"
echo "• Company paperformat assignments"
echo "• Font settings and CSS customizations"
echo "• Currency symbol positioning"
echo "• Template modifications"
echo
echo -e "${YELLOW}Remember:${NC} Even small differences in margins or DPI can cause"
echo "significant layout variations in PDF reports."