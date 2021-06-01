# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    tool_ids = fields.One2many(comodel_name='product.template', inverse_name='assign_user_id')
    create_invoice_access = fields.Boolean(compute='_compute_create_invoice_status', string="Crear facturas sueltas",
                                           tracking=True)

    @api.depends('user_id', 'user_id.groups_id')
    def _compute_create_invoice_status(self):
        for rec in self:
            if rec.user_id.has_group('equiport_custom.create_customer_invoices'):
                rec.create_invoice_access = True
            else:
                rec.create_invoice_access = False

    def allow_user_to_create_invoices(self):
        for rec in self:
            if rec.user_id:
                rec.sudo().user_id.groups_id += self.env['res.groups'].browse(
                    rec.env.ref('equiport_custom.create_customer_invoices').id)

    def block_user_to_create_invoices(self):
        for rec in self:
            if rec.user_id:
                rec.sudo().user_id.groups_id -= self.env['res.groups'].browse(
                    rec.env.ref('equiport_custom.create_customer_invoices').id)
