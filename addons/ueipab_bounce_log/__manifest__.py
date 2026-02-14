# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Bounce Log',
    'version': '17.0.1.4.0',
    'category': 'Contacts',
    'summary': 'Email bounce tracking and resolution workflow for Contacts',
    'description': """
UEIPAB Bounce Log
==================
Extends the Contacts app with an Email Bounce Log feature.

Features:
---------
* Track bounced emails with reason and technical detail
* Link bounces to res.partner and mailing.contact records
* Resolution workflow: Restore original email or apply new email
* State tracking: Pending → Notified → Contacted → Pendiente Akdemia → Resolved
* Chatter audit trail on partner records
* Mailing contact sync: resolution updates mailing.contact records by email match
* Future: WhatsApp AI agent integration
""",
    'author': 'UEIPAB',
    'depends': ['contacts', 'mail', 'mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_bounce_log_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
