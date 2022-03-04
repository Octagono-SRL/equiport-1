# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = ['account.payment']

    is_rental_deposit = fields.Boolean(string="Deposito de renta")
    rental_order_id = fields.Many2one(comodel_name='sale.order', string="Orden de alquiler",
                                      domain=[('is_rental_order', '=', True)])
    first_assigned_check_number = fields.Char(
        "Defined check number",
        index=True,
        copy=False,
        help="Stored field equivalent of check_number to maintain number",
    )

    def write(self, values):
        # Add code here
        if 'check_number' in values and not self.first_assigned_check_number:
            values['first_assigned_check_number'] = values.get('check_number')

        check_next_sequence = False
        if 'check_number' in values:
            payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
            payments = self.search([]).filtered(
                lambda p: p.payment_method_id == payment_method_check and p.check_manual_sequencing).sorted(
                lambda p: int(p.check_number) if p.check_number else 1, reverse=True).mapped('check_number')
            if payments and len(payments) > 0:
                check_next_sequence = int(payments[0]) + 1

        res = super(AccountPayment, self).write(values)

        for rec in self:
            if rec.check_number != rec.first_assigned_check_number and rec.first_assigned_check_number not in [False, '']:
                rec.check_number = rec.first_assigned_check_number
            if check_next_sequence:
                rec.journal_id.check_sequence_id.number_next_actual = check_next_sequence
                rec.journal_id.check_sequence_id.number_next = check_next_sequence
                rec.journal_id.check_next_number = check_next_sequence

        return res


    ncf_reference = fields.Char(string="Referencia de Pago", compute='compute_payment_reference', store=True)


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
