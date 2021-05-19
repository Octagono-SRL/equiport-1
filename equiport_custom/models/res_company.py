# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    #   region PO Approval Amount

    active_op_approval = fields.Boolean(string="Aprobación de pedido de compra",
                                        help="Solicitar a administradores que aprueben pedidos superiores a un importe mínimo")

    # Amount by levels
    op_ini_level = fields.Monetary(default=5000)
    op_mid_level = fields.Monetary(default=10000)
    op_top_level = fields.Monetary(default=20000)

    # Responsible by levels
    op_ini_user_id = fields.Many2one(comodel_name='res.users')
    op_mid_user_id = fields.Many2one(comodel_name='res.users')
    op_top_user_id = fields.Many2one(comodel_name='res.users')

    # Functions
    @api.onchange('active_op_approval')
    def clear_user_ids(self):
        self.op_ini_user_id = False
        self.op_mid_user_id = False
        self.op_top_user_id = False

    @api.constrains('op_ini_level', 'op_mid_level', 'op_top_level')
    def check_op_level_amount(self):
        for rec in self:
            if rec.active_op_approval:
                if not rec.op_ini_level < rec.op_mid_level < rec.op_top_level:
                    raise ValidationError("Debe mantener una escalabilidad entre niveles.")

    #   endregion

    # region PO Allow Cancel
    user_po_allow_cancel = fields.Many2many(comodel_name='res.users', relation='op_allow_cancel_users_rel')

    # endregion
    # region SL services

    @api.model
    def _prepare_gate_service(self):
        default_gate_service = self.env['product.product'].search([('is_gate_service', '=', True)])
        if not default_gate_service:
            property_account_income_val = self.env['ir.property']._get_default_property(
                name='property_account_income_categ_id', model='product.category')

            vals = {
                'name': 'Gate In / Gate Out',
                'type': 'service',
                'is_gate_service': True,
                'invoice_policy': 'order',
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'property_account_income_id': int(property_account_income_val[1][1]),
                'taxes_id': [(6, 0, [])],
                'company_id': False,
            }
            default_gate_service = self.env['product.product'].create(vals)
            return default_gate_service.id
        else:
            return default_gate_service.id

    default_gate_service = fields.Many2one(comodel_name='product.product', domain=[('is_gate_service', '=', True)],
                                           string="Servicio Gate In / Gate Out", ondelete='restrict')

    default_stock = fields.Many2one(comodel_name='stock.warehouse', string="Almancen",
                                    domain=[('is_gate_stock', '=', True)], ondelete='restrict')

    # endregion

    # region SP Access
    user_sp_access = fields.Many2many(comodel_name='res.users', relation='sp_access_users_rel')
    # endregion

    # region Rental Pickup Access
    user_rental_access = fields.Many2many(comodel_name='res.users', relation='rental_access_users_rel')

    # endregion

    # region Deposit Rental

    # default_deposit_account_id = fields.Many2one(comodel_name='account.account', string="Cuenta",
    #                                              domain=[('to_deposit', '=', True)], ondelete='restrict')
    # endregion
