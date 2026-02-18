{
    'name': 'UEIPAB AI Agent',
    'version': '17.0.1.17.0',
    'category': 'Services',
    'summary': 'AI-powered WhatsApp agent for automated customer interactions',
    'author': 'UEIPAB',
    'website': '',
    'depends': ['contacts', 'mail', 'mass_mailing', 'account', 'ueipab_bounce_log', 'hr', 'ueipab_hr_employee'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/skills_data.xml',
        'data/cron.xml',
        'wizard/start_conversation_wizard_view.xml',
        'views/ai_agent_dashboard_views.xml',
        'views/ai_agent_skill_views.xml',
        'views/ai_agent_conversation_views.xml',
        'views/ai_agent_message_views.xml',
        'views/hr_data_collection_request_views.xml',
        'views/menus.xml',
    ],
    'post_init_hook': '_load_api_configs',
    'external_dependencies': {
        'python': ['fitz'],  # PyMuPDF — PDF-to-image for Claude Vision
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
