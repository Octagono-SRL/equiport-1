{
    'name': 'Reportes Extra DGII',
    'version': '14.0.0.1',
    'summary': 'Otros reportes no cubiertos en el modulo DGII Reports',
    'description': '',
    'category': 'Accounting',
    'author': 'Wander Paniagua',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'dgii_reports'
    ],
    'data': [
        'views/dgii_report_views.xml',
        'views/account_account_views.xml'
    ],
    'installable': True,
    'auto_install': False
}
