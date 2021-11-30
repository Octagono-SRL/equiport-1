# -*- coding: utf-8 -*-

{
    'name': 'Cartas de retención',
    'version': '14.0.1',
    'category': 'Accounting',
    'summary': 'Este módulo agrega la funcionalidad de generar las cartas de retenciones.',
    'description': """""",
    'author': 'José Romero - jromero@octagono.com.do',
    'website': '',
    'depends': ['base', 'account'],
    "data": [
        'security/ir.model.access.csv',
        'wizards/generate_withholding_letter_wizard_views.xml',
        'report/withholding_letter_report.xml',
    ],
}
