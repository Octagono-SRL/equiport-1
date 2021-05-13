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

    @api.model
    def _prepare_stock(self):
        default_location = self.env['stock.location'].search([('is_gate_location', '=', True)])
        if not default_location:
            default_location = self.env['stock.location'].create({
                'name': 'Clientes',
                'usage': 'internal',
                'is_gate_location': True,
            })

        default_stock = self.env['stock.warehouse'].search([('is_gate_stock', '=', True)])
        if not default_stock:
            default_stock = self.env['stock.warehouse'].create({
                'name': 'Clientes',
                'code': 'WG',
                'partner_id': self.partner_id.id,
                'lot_stock_id': default_location.id
            })
            return default_stock.id
        else:
            return default_stock.id

    default_gate_service = fields.Many2one(comodel_name='product.product', domain=[('type', '=', 'service')],
                                           string="Servicio Gate In / Gate Out", default=_prepare_gate_service)

    default_stock = fields.Many2one(comodel_name='stock.warehouse', string="Almancen", default=_prepare_stock)

    # endregion

    # region SP Access
    user_sp_access = fields.Many2many(comodel_name='res.users', relation='sp_access_users_rel')
    # endregion

    # region Rental Pickup Access
    user_rental_access = fields.Many2many(comodel_name='res.users', relation='rental_access_users_rel')
    # endregion
