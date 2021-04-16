# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OctBankReconciliationLine(models.Model):
    _name = 'oct.bank.reconciliation.line'
    _order = "date asc"

    oct_bank_reconciliation_id = fields.Many2one('oct.bank.reconciliation', string=u"Conciliación")
    date = fields.Date('Fecha')
    ref = fields.Char('Referencia')
    account_id = fields.Many2one('account.account', string="Cuenta")
    partner_id = fields.Many2one('res.partner', string="Empresa")
    debit = fields.Float("Débito")
    credit = fields.Float("Crédito")
    bank_reconciliated = fields.Boolean("Conciliado con el banco?")