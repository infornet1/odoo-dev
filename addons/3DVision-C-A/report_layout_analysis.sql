-- COMPREHENSIVE REPORT LAYOUT ANALYSIS
-- Compare all possible layout parameters between Production (DB_UEIPAB) and Testing databases
-- Execute these queries in both environments and compare results

-- =============================================================================
-- 1. COMPLETE PAPER FORMAT ANALYSIS
-- =============================================================================
SELECT 'PAPER_FORMAT_ANALYSIS' as analysis_type,
       name,
       format,
       page_height,
       page_width,
       margin_top,
       margin_bottom,
       margin_left,
       margin_right,
       orientation,
       header_line,
       header_spacing,
       disable_shrinking,
       print_page_width,
       print_page_height,
       dpi,
       default,
       display_name,
       create_date,
       write_date,
       create_uid,
       write_uid
FROM report_paperformat
WHERE name IN ('US Letter', 'US Half Letter', 'Letter', 'A4')
ORDER BY name;

-- =============================================================================
-- 2. DETAILED REPORT ACTION ANALYSIS
-- =============================================================================
SELECT 'REPORT_ACTION_ANALYSIS' as analysis_type,
       name,
       model,
       report_type,
       report_name,
       report_file,
       paperformat_id,
       print_report_name,
       multi,
       attachment_use,
       attachment,
       binding_model_id,
       binding_type,
       groups_id,
       display_name,
       create_date,
       write_date,
       create_uid,
       write_uid
FROM ir_actions_report
WHERE report_name LIKE '%freeform%'
   OR name LIKE '%freeform%'
   OR model = 'account.move'
ORDER BY name;

-- =============================================================================
-- 3. COMPANY SETTINGS ANALYSIS
-- =============================================================================
SELECT 'COMPANY_SETTINGS_ANALYSIS' as analysis_type,
       c.name as company_name,
       c.paperformat_id,
       pf.name as paperformat_name,
       c.font,
       c.primary_color,
       c.secondary_color,
       c.logo_web_size,
       c.report_header,
       c.report_footer,
       c.external_report_layout_id,
       erl.name as external_layout_name,
       c.country_id,
       country.name as country_name,
       c.currency_id,
       curr.name as currency_name
FROM res_company c
LEFT JOIN report_paperformat pf ON c.paperformat_id = pf.id
LEFT JOIN ir_ui_view erl ON c.external_report_layout_id = erl.id
LEFT JOIN res_country country ON c.country_id = country.id
LEFT JOIN res_currency curr ON c.currency_id = curr.id
ORDER BY c.name;

-- =============================================================================
-- 4. SYSTEM CONFIGURATION PARAMETERS
-- =============================================================================
SELECT 'SYSTEM_CONFIG_ANALYSIS' as analysis_type,
       key,
       value,
       create_date,
       write_date
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

-- =============================================================================
-- 5. CSS AND STYLING ANALYSIS (WEB ASSETS)
-- =============================================================================
SELECT 'CSS_ASSETS_ANALYSIS' as analysis_type,
       name,
       bundle,
       directive,
       target,
       active,
       sequence,
       create_date,
       write_date
FROM ir_asset
WHERE name LIKE '%report%'
   OR name LIKE '%css%'
   OR name LIKE '%style%'
   OR bundle LIKE '%report%'
ORDER BY bundle, sequence;

-- =============================================================================
-- 6. QWEB TEMPLATE CUSTOMIZATIONS
-- =============================================================================
SELECT 'QWEB_TEMPLATE_ANALYSIS' as analysis_type,
       name,
       key,
       type,
       arch_db,
       active,
       priority,
       mode,
       inherit_id,
       model,
       create_date,
       write_date,
       create_uid,
       write_uid
FROM ir_ui_view
WHERE name LIKE '%freeform%'
   OR key LIKE '%freeform%'
   OR name LIKE '%invoice%'
   OR key LIKE '%invoice%'
   OR name LIKE '%report%'
   OR arch_db LIKE '%freeform%'
   OR model = 'account.move'
ORDER BY name;

-- =============================================================================
-- 7. FONT AND TYPOGRAPHY SETTINGS
-- =============================================================================
SELECT 'FONT_ANALYSIS' as analysis_type,
       'Company Font Settings' as category,
       name as company_name,
       font as font_setting
FROM res_company
WHERE font IS NOT NULL
UNION ALL
SELECT 'FONT_ANALYSIS' as analysis_type,
       'System Font Parameters' as category,
       key as parameter_name,
       value as font_value
FROM ir_config_parameter
WHERE key LIKE '%font%';

-- =============================================================================
-- 8. ATTACHMENT AND FILE STORAGE SETTINGS
-- =============================================================================
SELECT 'ATTACHMENT_ANALYSIS' as analysis_type,
       name,
       res_model,
       res_field,
       type,
       url,
       file_size,
       checksum,
       mimetype,
       create_date,
       write_date
FROM ir_attachment
WHERE name LIKE '%report%'
   OR name LIKE '%css%'
   OR name LIKE '%style%'
   OR mimetype LIKE '%css%'
   OR res_model = 'ir.actions.report'
ORDER BY create_date DESC;

-- =============================================================================
-- 9. TRANSLATION AND LOCALIZATION SETTINGS
-- =============================================================================
SELECT 'LOCALIZATION_ANALYSIS' as analysis_type,
       'Language Settings' as category,
       lang.name as language_name,
       lang.code as language_code,
       lang.direction,
       lang.date_format,
       lang.time_format,
       lang.decimal_point,
       lang.thousands_sep,
       lang.active
FROM res_lang lang
WHERE lang.active = true
ORDER BY lang.name;

-- =============================================================================
-- 10. MODULE AND ADDON ANALYSIS
-- =============================================================================
SELECT 'MODULE_ANALYSIS' as analysis_type,
       name,
       state,
       latest_version,
       author,
       website,
       summary,
       create_date,
       write_date
FROM ir_module_module
WHERE name LIKE '%report%'
   OR name LIKE '%pdf%'
   OR name LIKE '%account%'
   OR name LIKE '%invoice%'
   OR state = 'installed'
ORDER BY name;

-- =============================================================================
-- 11. SEQUENCE AND NUMBERING FORMATS
-- =============================================================================
SELECT 'SEQUENCE_ANALYSIS' as analysis_type,
       name,
       code,
       prefix,
       suffix,
       number_next,
       number_increment,
       padding,
       company_id,
       active
FROM ir_sequence
WHERE code LIKE '%account%'
   OR code LIKE '%invoice%'
   OR name LIKE '%invoice%'
ORDER BY name;

-- =============================================================================
-- 12. CURRENCY AND DECIMAL PRECISION
-- =============================================================================
SELECT 'CURRENCY_PRECISION_ANALYSIS' as analysis_type,
       c.name as currency_name,
       c.symbol,
       c.position,
       c.rounding,
       c.decimal_places,
       c.active,
       dp.name as precision_name,
       dp.digits as precision_digits
FROM res_currency c
LEFT JOIN decimal_precision dp ON dp.name LIKE '%Account%' OR dp.name LIKE '%Product%'
WHERE c.active = true
ORDER BY c.name, dp.name;

-- =============================================================================
-- 13. ACCOUNTING SPECIFIC SETTINGS
-- =============================================================================
SELECT 'ACCOUNTING_SETTINGS_ANALYSIS' as analysis_type,
       'Chart of Accounts' as category,
       name,
       code,
       company_id
FROM account_account
WHERE code IS NOT NULL
LIMIT 10;

-- =============================================================================
-- 14. WEB CLIENT SETTINGS
-- =============================================================================
SELECT 'WEB_CLIENT_ANALYSIS' as analysis_type,
       key,
       value
FROM ir_config_parameter
WHERE key LIKE '%web%'
   OR key LIKE '%client%'
   OR key LIKE '%session%'
ORDER BY key;

-- =============================================================================
-- 15. DATABASE SPECIFIC ANALYSIS
-- =============================================================================
SELECT 'DATABASE_ANALYSIS' as analysis_type,
       'Database Encoding' as parameter,
       pg_encoding_to_char(encoding) as value
FROM pg_database
WHERE datname = current_database()
UNION ALL
SELECT 'DATABASE_ANALYSIS' as analysis_type,
       'Database Locale' as parameter,
       datcollate as value
FROM pg_database
WHERE datname = current_database()
UNION ALL
SELECT 'DATABASE_ANALYSIS' as analysis_type,
       'Database Character Type' as parameter,
       datctype as value
FROM pg_database
WHERE datname = current_database();