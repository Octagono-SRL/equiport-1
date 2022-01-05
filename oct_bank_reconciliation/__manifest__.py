# -*- coding: utf-8 -*-
{
    'name': "Bank Reconciliation",

    'summary': """
        Bank Reconciliation""",

    'description': """
        This module is for make a bank reconciliation.
    """,

    'author': "José Romero",
    'website': "",

    'category': 'Accounting',
    'version': '14.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'account',
    ],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/report_conciliation.xml',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
