# -*- coding: utf-8 -*-
import datetime
import math

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReportPartnerAccount(models.TransientModel):
    _name = 'report.partner.account'
    _description = _("Modelo para visualizar el estado de cuentas de los clientes")

    name = fields.Char(string=_('Title'), compute='_compute_rec_name')
    date_from = fields.Date(string=_('From'))
    date_to = fields.Date(string=_('To'), default=fields.Date.today())

    @api.depends('partner_id')
    def _compute_rec_name(self):
        for rec in self:
            rec.name = rec.partner_id.name

    partner_id = fields.Many2one(comodel_name='res.partner', string=_('Customer'), readonly=True)
    credit_limit = fields.Float(string=_("Credit Limit"))
    company_id = fields.Many2one(comodel_name='res.company', default=lambda s: s.env.company)
    currency_id = fields.Many2one(comodel_name='res.currency')
    line_ids = fields.One2many(comodel_name='report.partner.account.line', inverse_name='report_partner_id')
    amount_total = fields.Monetary(string=_('Total'), store=True, readonly=True,
                                   compute='_compute_amount')
    amount_residual = fields.Monetary(string=_('Total Owed'), store=True, readonly=True,
                                      compute='_compute_amount')

    @api.depends('line_ids', 'partner_id')
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('amount_total'))
            rec.amount_residual = sum(rec.line_ids.mapped('amount_residual'))

    def action_document_print(self):
        if len(self.line_ids) > 0:
            return self.env.ref('partner_account_state.report_action_partner_account_state').report_action(self)
        else:
            raise UserError(_("There is not information to process the PDF"))

    @staticmethod
    def split_list(alist, wanted_parts=1):
        length = len(alist)
        return [alist[i * length // wanted_parts: (i + 1) * length // wanted_parts] for i in range(wanted_parts)]

    def split_list_len(self, alist, fix_len=1):
        length = len(alist)
        qty = math.ceil(length / fix_len)
        return self.split_list(alist, qty)


class ReportPartnerAccountLine(models.TransientModel):
    _name = 'report.partner.account.line'
    _description = _("Modelo para visualizar las lineas del estado de cuentas de los clientes")

    report_partner_id = fields.Many2one(comodel_name='report.partner.account')
    partner_id = fields.Many2one(related='report_partner_id.partner_id', string=_('Customer'))
    move_id = fields.Many2one(string=_("Document Number"), comodel_name='account.move')
    invoice_date = fields.Date(related='move_id.invoice_date', string=_("Document Date"))
    move_date = fields.Date(related='move_id.date')
    invoice_payment_term_id = fields.Many2one(related='move_id.invoice_payment_term_id')
    trans_days = fields.Integer(compute="_compute_trans_days", string=_("Aging"))
    l10n_do_fiscal_number = fields.Char(related='move_id.l10n_do_fiscal_number', string=_("NCF"))
    amount_total = fields.Monetary(related='move_id.amount_total', string=_("Total"))
    amount_residual = fields.Monetary(related='move_id.amount_residual', string=_("Amount Residual"))
    currency_id = fields.Many2one(related='move_id.currency_id', string=_("Currency"))
    company_id = fields.Many2one(comodel_name='res.company', default=lambda s: s.env.company)

    @api.depends('move_id', 'invoice_date', 'invoice_payment_term_id')
    def _compute_trans_days(self):
        for rec in self:
            rec.trans_days = (datetime.date.today() - (rec.invoice_date or rec.move_date)).days
