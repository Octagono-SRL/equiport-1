# -*- coding: utf-8 -*-
{
    'name': "Equiport Customizations",

    'summary': """
        Module to extends and customize some base features. """,

    'description': """
        This module is to customize the Odoo's base modules
        for the company Equiport.
    """,

    'author': "Octagono SRL",
    'website': "",

    'category': 'Customizations',
    'version': '14.0.0.7',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
        'stock',
        'stock_barcode',
        'stock_landed_costs',
        'purchase_requisition_stock',
        'hr',
        'fleet',
        'repair',
        'account',
        'sale_subscription',
        'account_check_printing',
        'sale_renting',
        'sale_stock_renting',
        'purchase_discount',
        'crm',
        'project',
        'industry_fsm',
        'industry_fsm_sale',
        'sale_timesheet',
        'l10n_latam_invoice_document',
        'l10n_do_accounting',
        'dgii_reports'
    ],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/stock_location_data.xml',
        'data/stock_warehouse_data.xml',
        'data/account_account_data.xml',
        'data/product_product_data.xml',
        'data/damage_option_data.xml',
        'data/ir_con_data.xml',
        'data/ir_sequence.xml',
        'data/fleet_service_data.xml',
        'data/unit_model_size.xml',
        'data/unit_model_type.xml',
        'data/tire_state_data.xml',
        'wizard/wizard_service_picking_views.xml',
        'wizard/wizard_purchase_order_cancel_views.xml',
        'wizard/wizard_purchase_order_comparison_report_view.xml',
        'wizard/wizard_rental_processing_views.xml',
        'wizard/wizard_rental_payment_register_views.xml',
        'wizard/wizard_alert_document_type_views.xml',
        'views/res_currency_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/res_company_views.xml',
        'views/res_employee_views.xml',
        'views/stock_orderpoint_views.xml',
        'views/stock_service_picking_views.xml',
        'views/stock_menuitems.xml',
        'views/stock_picking_views.xml',
        'views/stock_production_lot_views.xml',
        'views/stock_warehouse_views.xml',
        'views/product_category.xml',
        'views/product_pricelist_views.xml',
        'views/unit_model_views.xml',
        'views/stock_quant_views.xml',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_requisition_views.xml',
        'views/sale_order_views.xml',
        'views/rental_order_views.xml',
        'views/crm_lead_views.xml',
        'views/project_task.xml',
        'views/repair_views.xml',
        'views/product_unit_view.xml',
        'views/account_journal_views.xml',
        'views/account_move.xml',
        'views/menu_items.xml',
        'views/l10n_latam_document_type_views.xml',
        'views/fleet_vehicle_view.xml',
        'views/fleet_vehicle_log_views.xml',
        'views/unit_model_type.xml',
        'views/unit_model_size.xml',
        'views/tire_state_views.xml',
        'views/sale_subscription_view.xml',
        'views/dgii_report_views.xml',
        'views/account_payment_views.xml',
        'report/report_external_layout.xml',
        'report/report_purchase_order_comparison.xml',
        'report/report_deliveryslip.xml',
        'report/report_purchase_requisition_order_comparison.xml',
        'report/custom_rental_report.xml',
        'report/report_invoice_document.xml',
        'report/report_project_task_user_fsm.xml',
        'report/repair_templates_repair_order.xml',
        'report/sale_report_template_inherit.xml',
        'report/report_service_receipt.xml',
        'report/report_purchase_order.xml',

        # 'views/',
    ],
}
