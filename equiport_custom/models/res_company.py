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

    # region Fleet Alerts

    user_fleet_notify = fields.Many2many(comodel_name='res.users', relation='fleet_notify_users_rel')
    fuel_services_fleet = fields.Many2many(comodel_name='fleet.service.type', relation='fuel_services_fleet_rel')

    # endregion
