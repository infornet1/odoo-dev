# Documentation: UEIPAB Employee Self-Service Module (`ueipab_empl_self_serv`)

## 1. Module Purpose

This module provides a secure portal for employees to access and manage their own HR information within Odoo 17. It empowers employees by giving them direct access to their personal data and payslips, reducing the administrative burden on the HR department.

The interface is integrated directly into the standard Odoo portal, accessible under the "My Account" section for any logged-in user who is linked to an employee record.

## 2. Features

-   **Personal Details Management:**
    -   Employees can view and edit a whitelisted set of their personal information:
        -   Home Phone
        -   Home Address
        -   VAT / Tax ID
        -   Marital Status
    -   Read-only view of key contract details like Job Title and Contract Start Date.

-   **Payslip Viewing:**
    -   A "My Payslips" tab lists all of the employee's historical payslips, sorted from newest to oldest.
    -   Provides a "Download" button for each payslip, allowing the employee to retrieve the official PDF report.
    -   The list is paginated for employees with a large number of payslips.

## 3. Dependencies

To install this module, the following Odoo applications must be present:
-   **Contacts (`contacts`)**
-   **Employees (`hr`)**
-   **Contracts (`hr_contract`)**
-   **Website (`website`)**
-   **Odoo Payroll (`hr_payroll_community` or equivalent)**

## 4. Security Model

Data privacy and security are the foundation of this module, enforced through two levels of Odoo's security system.

-   **Access Rights (`ir.model.access.csv`):**
    -   Portal users are granted `read` and `write` access to their own `hr.employee` record and `read` access to `hr.payslip`.

-   **Record Rules (`security/security.xml`):**
    -   A strict record rule is applied to the `hr.employee` model to ensure users can only see the record where the `user_id` matches their own.
    -   A second record rule is applied to the `hr.payslip` model, ensuring users can only view payslips linked to their specific employee record (`employee_id.user_id`).
    -   These rules prevent users from accessing the data of other employees, even if they attempt to guess URL addresses.

## 5. User Guide

1.  **Log In:** Log into the Odoo portal with your user account.
2.  **Navigate:** Go to the "My Account" area.
3.  **Access:** Click on the new **"My Details & Payslips"** link.
4.  **Edit Information:** On the "Personal Details" tab, update your information in the form and click "Save Changes".
5.  **View Payslips:** Click on the "My Payslips" tab to see a list of your payslips.
6.  **Download:** Click the "Download" button next to any payslip to save its PDF file.

## 6. Technical Overview

-   **Controller:** A new controller at `/my/details` handles all web requests.
-   **Templates:** QWeb templates (XML) are used to build the UI, featuring a tabbed interface for a clean user experience. The templates are integrated with the standard Odoo portal layout.
-   **Models:** The module does not introduce new models but interacts with existing Odoo models:
    -   `hr.employee`
    -   `hr.payslip`
    -   `hr.contract`

## 7. Debugging Notes (Current Status: 2025-11-18)

### Persistent JavaScript Error

A `TypeError: Cannot set properties of null (setting 'textContent')` error occurs on the `/my/home` portal page when loading. This error is consistently reported even after applying multiple fixes targeting the `ueipab_empl_self_serv` module's view and controller logic. The stack trace points to Odoo's core `portal.js` (`web.assets_frontend_lazy.js`) attempting to update a counter element that it cannot find in the DOM.

### Investigation Summary

-   **Initial Diagnosis:** Believed to be related to the `payslip_count` from `ueipab_empl_self_serv` module, specifically the missing HTML element in `portal.portal_my_home`.
-   **Fixes Applied:**
    1.  Conditional rendering for `t-field` (to handle missing currency).
    2.  Changed `t-field` to `t-esc` for rendering calculated `Net Salary`.
    3.  Modified `portal_my_home_add_details_link` template to include the correct `<span class="badge ... o_portal_payslip_count">`.
    4.  Overrode `/my/counters` route in `controllers/portal.py` to only return `payslip_count` and suppress other potential counters.
-   **Module Actions:** Upgrades and reinstallations of `ueipab_empl_self_serv` were performed.
-   **Result:** The error persists on `/my/home`, even after isolating the `ueipab_empl_self_serv` module's counter functionality.

### Current Hypothesis

The error is likely caused by a **pre-existing misconfiguration or bug in the Odoo environment's base portal setup**, independent of the `ueipab_empl_self_serv` module. The `portal.js` script is attempting to update a counter element (from a default Odoo counter like 'Invoices', 'Tasks', etc.) that is missing from the customized `portal.portal_my_home` template in this specific Odoo instance. The `ueipab_empl_self_serv` module, by introducing its own counter, may have merely exposed this underlying issue.

### Pending Action

A diagnostic "poison pill" (deliberate Python crash) was introduced into `controllers/portal.py` to definitively determine if updated Python files are being loaded by the Odoo server. The result of this test is pending user feedback. The "poison pill" has been removed, and the controller has been reverted to its last functional state (with the `/my/counters` override).

---
**Next Steps:** Wait for user feedback on the "poison pill" test. The root cause (environment vs. code not loading) needs to be confirmed.