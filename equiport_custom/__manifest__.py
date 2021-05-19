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
    'version': '14.0.0.0.5',

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
        'sale_stock_renting',
        'purchase_discount',
        'crm',
    ],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/stock_location_data.xml',
        'data/stock_warehouse_data.xml',
        'data/account_account_data.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/res_employee_views.xml',
        'views/stock_orderpoint_views.xml',
        'views/stock_menuitems.xml',
        'views/stock_picking_views.xml',
        'views/stock_production_lot_views.xml',
        'views/product_category.xml',
        'views/product_pricelist_views.xml',
        'views/unit_model_views.xml',
        'views/purchase_order_menuitems.xml',
        'views/product_template_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_requisition_views.xml',
        'views/sale_order_views.xml',
        'views/rental_order_views.xml',
        'views/crm_lead_views.xml',
        'views/repair_views.xml',
        'views/product_unit_view.xml',
        'report/report_purchaseorder_equiport_inherit.xml',
        'report/report_purchase_order_comparison.xml',
        'report/report_purchase_requisition_order_comparison.xml',
        'report/report_holding_tax_view.xml',
        'wizard/wizard_purchase_order_cancel_views.xml',
        'wizard/wizard_purchase_order_comparison_report_view.xml',
        'wizard/wizard_rental_payment_register_views.xml',
        # 'views/',
    ],
}
