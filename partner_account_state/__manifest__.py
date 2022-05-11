{
    'name': 'Report Account State',
    'version': '14.0.0.2',
    'summary': 'Report about the customer balance',
    'description': '',
    'category': 'Accounting',
    'author': 'Octagono',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'account_followup', 'l10n_do_accounting', 'sales_team'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/res_partner_views.xml',
        'report/report_partner_account_views.xml',
        'report/report_partner_account_state.xml',
        'wizard/wizard_generate_account_state_views.xml'
    ],
    'installable': True,
    'auto_install': False
}
