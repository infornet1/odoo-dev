# -*- coding: utf-8 -*-
import base64
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class EmployeePortal(CustomerPortal):

    # def _prepare_home_portal_values(self, counters):
    #     values = super()._prepare_home_portal_values(counters)
    #     payslip_count = request.env['hr.payslip'].search_count([('employee_id.user_id', '=', request.env.user.id)])
    #     if 'payslip_count' in values:
    #         values['payslip_count'] += payslip_count
    #     else:
    #         values['payslip_count'] = payslip_count
    #     return values

    def _get_employee(self):
        return request.env['hr.employee'].search([('user_id', '=', request.env.user.id)], limit=1)

    @http.route(['/my/details', '/my/details/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_details(self, page=1, sortby=None, filterby=None, search=None, search_in='content', **kw):
        employee = self._get_employee()
        if not employee:
            # Render a specific template if the portal user has no linked employee record
            return request.render("ueipab_empl_self_serv.portal_my_details_no_employee")

        # Payslip List using sudo to bypass potential access errors on related fields,
        # security is enforced by the record rule defined in security.xml
        payslip_sudo = request.env['hr.payslip'].sudo()
        domain = [('employee_id', '=', employee.id)]

        payslip_count = payslip_sudo.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/details",
            url_args={},
            total=payslip_count,
            page=page,
            step=self._items_per_page
        )
        
        payslips = payslip_sudo.search(domain, order='date_from desc', limit=self._items_per_page, offset=pager['offset'])

        values = {
            'employee': employee,
            'payslips': payslips,
            'page_name': 'details',
            'pager': pager,
            'default_url': '/my/details',
        }
        if kw.get('success'):
            values['success'] = _('Details updated successfully.')
        if kw.get('error'):
            values['error'] = kw.get('error')

        return request.render("ueipab_empl_self_serv.portal_my_details", values)

    @http.route(['/my/details'], type='http', auth="user", website=True, method=['POST'])
    def portal_my_details_post(self, **kw):
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my')

        # Whitelist fields that can be updated from the portal
        fields_to_update = {}
        updatable_fields = ['private_phone', 'private_street', 'vat', 'marital']
        for field in updatable_fields:
            if field in kw:
                fields_to_update[field] = kw[field]
        
        if fields_to_update:
            try:
                # Use sudo to write as the portal user may not have write access to all fields
                # Record rules prevent them from editing any employee but their own.
                employee.sudo().write(fields_to_update)
            except Exception as e:
                # Provide a generic error message for security
                return request.redirect(f'/my/details?error=An error occurred while updating your details.')
        
        return request.redirect('/my/details?success=1')

    @http.route(['/my/payslip/print'], type='http', auth='user', website=True)
    def portal_payslip_print(self, payslip_id=None, **kw):
        try:
            # _document_check_access uses record rules to ensure user can access this document
            payslip_sudo = self._document_check_access('hr.payslip', int(payslip_id))
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Standard payslip report action in hr_payroll module
        report_action = request.env.ref('hr_payroll.action_report_payslip', raise_if_not_found=False)
        if not report_action:
             return request.redirect(f'/my/details?error=Payslip report action could not be found.')

        pdf, _ = report_action._render_qweb_pdf(payslip_sudo.id)

        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename="Payslip_{payslip_sudo.number or payslip_sudo.id}.pdf"')
        ]
        return request.make_response(pdf, headers=pdf_http_headers)
