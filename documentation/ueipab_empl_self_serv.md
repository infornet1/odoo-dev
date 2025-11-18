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
