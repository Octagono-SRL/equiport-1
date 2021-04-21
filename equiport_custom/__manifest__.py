# -*- coding: utf-8 -*-
{
    'name': "Equiport Customizations",

    'summary': """
        Module to extends and customize some base features. """,

    'description': """
        This module is to customize the Odoo's base modules
        for the company Equiport.
    """,

    'author': "Wander Paniagua",
    'website': "",

    'category': 'Customizations',
    'version': '14.0.2.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
        'stock',
        'stock_landed_costs',
        'purchase_requisition',
        'hr',
        'fleet',
        'repair',
        'sale_renting',
        'purchase_discount',
        'crm',
    ],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/res_employee_views.xml',
        'views/stock_orderpoint_views.xml',
        'views/stock_menuitems.xml',
        'views/stock_picking_views.xml',
        'views/purchase_order_menuitems.xml',
        'views/product_template_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
        'views/rental_order_views.xml',
        'views/crm_lead_views.xml',
        'views/repair_views.xml',
        'report/report_purchaseorder_equiport_inherit.xml',
        'report/report_purchase_order_comparison.xml',
        'wizard/wizard_purchase_order_cancel_views.xml',
        'wizard/wizard_purchase_order_comparison_report_view.xml',
        # 'views/',
    ],

}