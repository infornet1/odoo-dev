{
    'name': 'UEIPAB Recruitment Evaluation',
    'version': '17.0.3.4.0',
    'category': 'Human Resources',
    'summary': 'CV scoring + Glenda AI evaluation pipeline with dual-AI confidence score',
    'depends': ['hr_recruitment', 'ueipab_ai_agent'],
    'data': [
        'security/ir.model.access.csv',
        'data/recruitment_stages.xml',
        'views/hr_applicant_eval_invite_wizard_view.xml',
        'views/hr_applicant_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
