# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    #   region PO Approval Amount

    active_op_approval = fields.Boolean(string="Aprobación de pedido de compra",
                                        help="Solicitar a administradores que aprueben pedidos superiores a un importe mínimo")

    # Amount by levels
    op_ini_level = fields.Monetary(string="Monto minimo", default=5000)
    op_mid_level = fields.Monetary(string="Monto minimo", default=10000)
    op_top_level = fields.Monetary(string="Monto minimo", default=20000)

    # Responsible by levels
    op_ini_user_id = fields.Many2one(comodel_name='res.users', string="Responsable")
    op_mid_user_id = fields.Many2one(comodel_name='res.users', string="Responsable")
    op_top_user_id = fields.Many2one(comodel_name='res.users', string="Responsable")

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
    user_po_allow_cancel = fields.Many2many(comodel_name='res.users', relation='op_allow_cancel_users_rel', string="Usuarios")
    # endregion

    # region SP Access
    user_sp_access = fields.Many2many(comodel_name='res.users', relation='sp_access_users_rel', string="Usuarios")

    # endregion



