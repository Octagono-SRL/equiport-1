# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = ['account.payment']

    is_rental_deposit = fields.Boolean(string="Deposito de renta")
    rental_order_id = fields.Many2one(comodel_name='sale.order', string="Orden de alquiler",
                                      domain=[('is_rental_order', '=', True)])

    ncf_reference = fields.Char(string="Referencia de Pago", compute='compute_payment_reference', store=True)
    # ncf_reference = fields.Char(string="Referencia de Pago", compute='compute_payment_reference', store=True,
    #                             default=lambda s: s.default_payment_reference())

    @api.depends('name', 'reconciled_invoices_count', 'reconciled_invoice_ids', 'reconciled_bill_ids',
                 'reconciled_bills_count', 'rental_order_id', 'is_rental_deposit')
    def compute_payment_reference(self):
        for rec in self:
            if rec.reconciled_bill_ids:
                rec.ncf_reference = ', '.join(i.l10n_do_fiscal_number for i in rec.reconciled_bill_ids)
            elif rec.reconciled_invoice_ids:
                rec.ncf_reference = ', '.join(i.l10n_do_fiscal_number for i in rec.reconciled_invoice_ids)
            elif rec.is_rental_deposit and rec.rental_order_id:
                rec.ncf_reference = rec.rental_order_id.name
            else:
                rec.ncf_reference = ''

    def unlink(self):
        is_deposit = self.is_rental_deposit
        order_id = self.rental_order_id
        res = super().unlink()
        if is_deposit:
            order_id.deposit_status = False
        return res

