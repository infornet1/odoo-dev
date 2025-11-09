-- CRITICAL LAYOUT COMPARISON QUERIES
-- Run these queries in BOTH production (DB_UEIPAB) and testing databases
-- Compare results field by field to identify layout differences

-- =============================================================================
-- CRITICAL CHECK 1: PAPER FORMAT EXACT COMPARISON
-- =============================================================================
-- Run this in BOTH databases and compare every single field
SELECT
    'PAPER_FORMAT_CRITICAL' as check_type,
    name as format_name,
    COALESCE(format, 'NULL') as format_value,
    COALESCE(page_height::text, 'NULL') as page_height,
    COALESCE(page_width::text, 'NULL') as page_width,
    COALESCE(margin_top::text, 'NULL') as margin_top,
    COALESCE(margin_bottom::text, 'NULL') as margin_bottom,
    COALESCE(margin_left::text, 'NULL') as margin_left,
    COALESCE(margin_right::text, 'NULL') as margin_right,
    COALESCE(orientation, 'NULL') as orientation,
    COALESCE(header_line::text, 'NULL') as header_line,
    COALESCE(header_spacing::text, 'NULL') as header_spacing,
    COALESCE(disable_shrinking::text, 'NULL') as disable_shrinking,
    COALESCE(print_page_width::text, 'NULL') as print_page_width,
    COALESCE(print_page_height::text, 'NULL') as print_page_height,
    COALESCE(dpi::text, 'NULL') as dpi,
    COALESCE(default::text, 'NULL') as is_default
FROM report_paperformat
WHERE name IN ('US Letter', 'US Half Letter')
ORDER BY name;

-- =============================================================================
-- CRITICAL CHECK 2: FREEFORM REPORT ACTION DETAILS
-- =============================================================================
-- Run this in BOTH databases - these settings directly affect rendering
SELECT
    'REPORT_ACTION_CRITICAL' as check_type,
    r.name as report_name,
    COALESCE(r.report_name, 'NULL') as report_key,
    COALESCE(r.paperformat_id::text, 'NULL') as paperformat_id,
    COALESCE(pf.name, 'NULL') as paperformat_name,
    COALESCE(r.print_report_name, 'NULL') as print_report_name,
    COALESCE(r.attachment_use::text, 'NULL') as attachment_use,
    COALESCE(r.attachment, 'NULL') as attachment_expr
FROM ir_actions_report r
LEFT JOIN report_paperformat pf ON r.paperformat_id = pf.id
WHERE r.report_name LIKE '%freeform%'
   OR r.name LIKE '%freeform%'
ORDER BY r.name;

-- =============================================================================
-- CRITICAL CHECK 3: COMPANY LAYOUT SETTINGS
-- =============================================================================
-- These company settings can override report defaults
SELECT
    'COMPANY_CRITICAL' as check_type,
    c.name as company_name,
    COALESCE(c.paperformat_id::text, 'NULL') as company_paperformat_id,
    COALESCE(pf.name, 'NULL') as company_paperformat_name,
    COALESCE(c.font, 'NULL') as company_font,
    COALESCE(c.primary_color, 'NULL') as primary_color,
    COALESCE(c.secondary_color, 'NULL') as secondary_color,
    COALESCE(c.external_report_layout_id::text, 'NULL') as external_layout_id,
    COALESCE(erl.name, 'NULL') as external_layout_name
FROM res_company c
LEFT JOIN report_paperformat pf ON c.paperformat_id = pf.id
LEFT JOIN ir_ui_view erl ON c.external_report_layout_id = erl.id
ORDER BY c.name;

-- =============================================================================
-- CRITICAL CHECK 4: WKHTMLTOPDF AND PDF PARAMETERS
-- =============================================================================
-- These system parameters directly control PDF generation
SELECT
    'PDF_PARAMETERS_CRITICAL' as check_type,
    key as parameter_key,
    COALESCE(value, 'NULL') as parameter_value
FROM ir_config_parameter
WHERE key IN (
    'report.url',
    'web.base.url',
    'web.base.url.freeze',
    'report.webkit.url',
    'report.webkit.debug',
    'report.webkit.resolution',
    'report.webkit.margin-top',
    'report.webkit.margin-bottom',
    'report.webkit.margin-left',
    'report.webkit.margin-right',
    'report.webkit.orientation',
    'report.webkit.format',
    'report.webkit.dpi',
    'report.webkit.disable-shrinking',
    'report.webkit.print-media-type',
    'report.webkit.header-spacing',
    'report.webkit.footer-spacing'
)
ORDER BY key;

-- =============================================================================
-- CRITICAL CHECK 5: CUSTOM CSS AND STYLING
-- =============================================================================
-- Check for any custom CSS that might affect report layout
SELECT
    'CSS_CRITICAL' as check_type,
    name as asset_name,
    bundle as asset_bundle,
    COALESCE(directive, 'NULL') as directive,
    COALESCE(target, 'NULL') as target,
    active::text as is_active,
    sequence::text as load_sequence
FROM ir_asset
WHERE bundle LIKE '%report%'
   OR name LIKE '%report%'
   OR name LIKE '%invoice%'
   OR directive LIKE '%css%'
ORDER BY bundle, sequence;

-- =============================================================================
-- CRITICAL CHECK 6: QWEB TEMPLATE MODIFICATIONS
-- =============================================================================
-- Check if freeform templates have been customized
SELECT
    'TEMPLATE_CRITICAL' as check_type,
    name as template_name,
    COALESCE(key, 'NULL') as template_key,
    COALESCE(mode, 'NULL') as inheritance_mode,
    COALESCE(inherit_id::text, 'NULL') as parent_template_id,
    active::text as is_active,
    COALESCE(priority::text, 'NULL') as priority,
    -- Only show first 200 chars of arch_db to identify customizations
    CASE
        WHEN arch_db IS NOT NULL
        THEN LEFT(arch_db, 200) || '...'
        ELSE 'NULL'
    END as arch_preview
FROM ir_ui_view
WHERE (name LIKE '%freeform%' OR key LIKE '%freeform%')
   OR (arch_db LIKE '%freeform%' AND model = 'account.move')
ORDER BY name;

-- =============================================================================
-- CRITICAL CHECK 7: CURRENCY AND DECIMAL FORMATTING
-- =============================================================================
-- Currency formatting can affect layout due to symbol positioning
SELECT
    'CURRENCY_CRITICAL' as check_type,
    c.name as currency_name,
    COALESCE(c.symbol, 'NULL') as currency_symbol,
    COALESCE(c.position, 'NULL') as symbol_position,
    COALESCE(c.rounding::text, 'NULL') as rounding,
    COALESCE(c.decimal_places::text, 'NULL') as decimal_places,
    -- Check if this currency is used by any company
    CASE
        WHEN EXISTS (SELECT 1 FROM res_company WHERE currency_id = c.id)
        THEN 'YES'
        ELSE 'NO'
    END as used_by_company
FROM res_currency c
WHERE c.active = true
ORDER BY c.name;

-- =============================================================================
-- CRITICAL CHECK 8: FONT AND LANGUAGE SETTINGS
-- =============================================================================
-- Font and language settings can affect character spacing and layout
SELECT
    'FONT_LANGUAGE_CRITICAL' as check_type,
    'Company Fonts' as setting_type,
    c.name as setting_name,
    COALESCE(c.font, 'NULL') as font_value
FROM res_company c
WHERE c.font IS NOT NULL

UNION ALL

SELECT
    'FONT_LANGUAGE_CRITICAL' as check_type,
    'Active Languages' as setting_type,
    l.name as setting_name,
    l.code || ' | direction:' || COALESCE(l.direction, 'NULL') ||
    ' | decimal:' || COALESCE(l.decimal_point, 'NULL') ||
    ' | thousands:' || COALESCE(l.thousands_sep, 'NULL') as font_value
FROM res_lang l
WHERE l.active = true

ORDER BY setting_type, setting_name;

-- =============================================================================
-- CRITICAL CHECK 9: SEQUENCE FORMATS (Can affect layout width)
-- =============================================================================
-- Invoice numbering format can affect layout if numbers are very long
SELECT
    'SEQUENCE_CRITICAL' as check_type,
    name as sequence_name,
    COALESCE(code, 'NULL') as sequence_code,
    COALESCE(prefix, 'NULL') as prefix,
    COALESCE(suffix, 'NULL') as suffix,
    COALESCE(padding::text, 'NULL') as padding,
    COALESCE(number_next::text, 'NULL') as next_number
FROM ir_sequence
WHERE code LIKE '%account%' OR code LIKE '%invoice%'
ORDER BY name;

-- =============================================================================
-- CRITICAL CHECK 10: INSTALLED MODULES AFFECTING REPORTS
-- =============================================================================
-- Different module versions can have different report templates
SELECT
    'MODULE_CRITICAL' as check_type,
    name as module_name,
    state as module_state,
    COALESCE(latest_version, 'NULL') as version,
    COALESCE(author, 'NULL') as author
FROM ir_module_module
WHERE state = 'installed'
  AND (name LIKE '%account%'
       OR name LIKE '%invoice%'
       OR name LIKE '%report%'
       OR name LIKE '%pdf%'
       OR name LIKE '%web%')
ORDER BY name;

-- =============================================================================
-- SUMMARY QUERY: ENVIRONMENT FINGERPRINT
-- =============================================================================
-- This creates a "fingerprint" of critical settings for quick comparison
SELECT
    'ENVIRONMENT_FINGERPRINT' as check_type,
    -- Paper format fingerprint
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

    -- Company settings fingerprint
    (SELECT STRING_AGG(
        c.name || ':pf' || COALESCE(c.paperformat_id::text,'none') ||
        ':font' || COALESCE(c.font,'none'),
        '|'
     ) FROM res_company c
    ) as company_fingerprint,

    -- Report action fingerprint
    (SELECT STRING_AGG(
        name || ':pf' || COALESCE(paperformat_id::text,'none'),
        '|'
     ) FROM ir_actions_report
     WHERE report_name LIKE '%freeform%'
    ) as report_action_fingerprint;

-- =============================================================================
-- EXECUTION INSTRUCTIONS
-- =============================================================================
--
-- 1. Run each of these queries in BOTH databases
-- 2. Export results to CSV or copy to spreadsheet
-- 3. Compare field by field, paying special attention to:
--    - All margin values (margin_top, margin_bottom, margin_left, margin_right)
--    - DPI settings
--    - Paper format orientations
--    - Company paperformat_id assignments
--    - Any CSS assets or template customizations
--    - Font settings
--    - Currency symbol positioning
--
-- 4. The ENVIRONMENT_FINGERPRINT query provides a quick way to spot differences
--    If the fingerprints don't match, drill down into the specific checks above
--
-- 5. Look for NULL vs actual values - sometimes one environment has a setting
--    while the other doesn't, causing the default to be used differently
--
-- =============================================================================