# -*- coding: utf-8 -*-
"""
AR-I Portal Controller

Handles employee self-service portal for AR-I declarations.
"""

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError


class ARIPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add AR-I count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if 'ari_count' in counters:
            employee = self._get_current_employee()
            if employee:
                ari_count = request.env['hr.employee.ari'].search_count([
                    ('employee_id', '=', employee.id)
                ])
                values['ari_count'] = ari_count
            else:
                values['ari_count'] = 0
        return values

    def _get_current_employee(self):
        """Get current user's employee record."""
        return request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid)
        ], limit=1)

    # -------------------------------------------------------------------------
    # AR-I LIST
    # -------------------------------------------------------------------------
    @http.route(['/my/ari', '/my/ari/page/<int:page>'], type='http',
                auth='user', website=True)
    def portal_my_ari(self, page=1, sortby=None, **kw):
        """Display list of AR-I declarations for current employee."""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')

        ARI = request.env['hr.employee.ari'].sudo()

        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'submission_date desc'},
            'year': {'label': _('Year'), 'order': 'fiscal_year desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count and paging
        domain = [('employee_id', '=', employee.id)]
        ari_count = ARI.search_count(domain)
        pager = portal_pager(
            url='/my/ari',
            total=ari_count,
            page=page,
            step=10
        )

        # Get records
        aris = ARI.search(domain, order=order, limit=10,
                          offset=pager['offset'])

        values = {
            'aris': aris,
            'page_name': 'ari',
            'pager': pager,
            'default_url': '/my/ari',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        }
        return request.render('ueipab_ari_portal.portal_my_ari', values)

    # -------------------------------------------------------------------------
    # AR-I DETAIL
    # -------------------------------------------------------------------------
    @http.route(['/my/ari/<int:ari_id>'], type='http', auth='user', website=True)
    def portal_my_ari_detail(self, ari_id, **kw):
        """Display AR-I declaration detail."""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')

        ari = request.env['hr.employee.ari'].sudo().browse(ari_id)

        # Security check
        if not ari.exists() or ari.employee_id.id != employee.id:
            raise AccessError(_('You do not have access to this AR-I declaration.'))

        values = {
            'ari': ari,
            'page_name': 'ari',
        }
        return request.render('ueipab_ari_portal.portal_my_ari_detail', values)

    # -------------------------------------------------------------------------
    # AR-I CREATE/EDIT
    # -------------------------------------------------------------------------
    @http.route(['/my/ari/new'], type='http', auth='user', website=True)
    def portal_ari_new(self, **kw):
        """Display form to create new AR-I declaration."""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')

        # Get employee's contract
        contract = request.env['hr.contract'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open')
        ], limit=1)

        # Calculate estimated income
        estimated_income = 0
        if contract:
            monthly = contract.wage or 0
            if hasattr(contract, 'ueipab_salary_v2') and contract.ueipab_salary_v2:
                monthly = contract.ueipab_salary_v2
            estimated_income = monthly * 16  # 12 months + 4 months bonuses

        values = {
            'employee': employee,
            'contract': contract,
            'estimated_income': estimated_income,
            'page_name': 'ari_new',
            'error': {},
            'error_message': [],
        }
        return request.render('ueipab_ari_portal.portal_ari_form', values)

    @http.route(['/my/ari/create'], type='http', auth='user',
                website=True, methods=['POST'])
    def portal_ari_create(self, **post):
        """Handle AR-I form submission."""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')

        error = {}
        error_message = []

        # Validate required fields
        required_fields = ['income_employer_primary', 'deduction_type']
        for field in required_fields:
            if not post.get(field):
                error[field] = 'missing'

        if error:
            error_message.append(_('Please fill in all required fields.'))
            values = {
                'employee': employee,
                'error': error,
                'error_message': error_message,
                'page_name': 'ari_new',
                **post,
            }
            return request.render('ueipab_ari_portal.portal_ari_form', values)

        # Prepare values
        vals = {
            'employee_id': employee.id,
            'fiscal_year': int(post.get('fiscal_year', request.env.cr.execute(
                "SELECT EXTRACT(YEAR FROM CURRENT_DATE)::INT") or 2025)),
            'variation_month': post.get('variation_month', 'january'),
            'is_variation': post.get('is_variation') == 'on',
            'income_employer_primary': float(post.get('income_employer_primary', 0)),
            'income_employer_b': float(post.get('income_employer_b', 0) or 0),
            'income_employer_c': float(post.get('income_employer_c', 0) or 0),
            'income_employer_d': float(post.get('income_employer_d', 0) or 0),
            'employer_b_name': post.get('employer_b_name', ''),
            'employer_c_name': post.get('employer_c_name', ''),
            'employer_d_name': post.get('employer_d_name', ''),
            'ut_value': float(post.get('ut_value', 9.00)),
            'deduction_type': post.get('deduction_type', 'unique'),
            'deduction_education': float(post.get('deduction_education', 0) or 0),
            'deduction_insurance': float(post.get('deduction_insurance', 0) or 0),
            'deduction_medical': float(post.get('deduction_medical', 0) or 0),
            'deduction_housing': float(post.get('deduction_housing', 0) or 0),
            'deduction_housing_type': post.get('deduction_housing_type'),
            'rebaja_spouse': post.get('rebaja_spouse') == 'on',
            'rebaja_children_under_25': int(post.get('rebaja_children_under_25', 0) or 0),
            'rebaja_children_disabled': int(post.get('rebaja_children_disabled', 0) or 0),
            'rebaja_parents': int(post.get('rebaja_parents', 0) or 0),
            'rebaja_prior_excess': float(post.get('rebaja_prior_excess', 0) or 0),
        }

        # Create AR-I
        ari = request.env['hr.employee.ari'].sudo().create(vals)

        return request.redirect(f'/my/ari/{ari.id}?message=created')

    # -------------------------------------------------------------------------
    # AR-I ACTIONS
    # -------------------------------------------------------------------------
    @http.route(['/my/ari/<int:ari_id>/submit'], type='http', auth='user',
                website=True, methods=['POST'])
    def portal_ari_submit(self, ari_id, **kw):
        """Submit AR-I for HR review."""
        employee = self._get_current_employee()
        ari = request.env['hr.employee.ari'].sudo().browse(ari_id)

        if ari.employee_id.id != employee.id:
            raise AccessError(_('Access denied.'))

        if ari.state == 'draft':
            ari.action_submit()

        return request.redirect(f'/my/ari/{ari_id}?message=submitted')

    @http.route(['/my/ari/<int:ari_id>/download'], type='http', auth='user')
    def portal_ari_download(self, ari_id, **kw):
        """Download AR-I Excel file."""
        employee = self._get_current_employee()
        ari = request.env['hr.employee.ari'].sudo().browse(ari_id)

        if ari.employee_id.id != employee.id:
            raise AccessError(_('Access denied.'))

        # Generate Excel if not exists
        if not ari.excel_file:
            generator = request.env['ari.excel.generator'].sudo()
            excel_data, filename = generator.generate_ari_excel(ari)
            ari.write({
                'excel_file': excel_data,
                'excel_filename': filename
            })

        import base64
        content = base64.b64decode(ari.excel_file)
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', f'attachment; filename="{ari.excel_filename}"'),
            ('Content-Length', len(content)),
        ]
        return request.make_response(content, headers)
