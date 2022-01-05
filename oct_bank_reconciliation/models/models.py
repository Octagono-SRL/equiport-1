# -*- coding: utf-8 -*-

import calendar
from datetime import datetime as dt
from odoo import models, fields, api
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class OctBankReconciliation(models.Model):
    _name = 'oct.bank.reconciliation'
    _rec_name = 'rec_name'

    def set_access_for_previous_balance(self):
        self.able_to_modify_previous_balance = self.env.user.has_group('oct_bank_reconciliation.group_oct_bank_reconciliation_manager')

    date = fields.Date(string="Fecha")
    rec_name = fields.Char(compute='_compute_full_name', string="Nombre Completo")
    # Below field is just used for the sql constraint and the _rec_name
    period = fields.Char('Periodo', compute='_compute_period', store=True)

    @api.depends('period','account_id')
    def _compute_full_name(self):
        for rec in self:
            rec.rec_name = rec.period +' - '+ rec.account_id.name

    @api.depends('date')
    def _compute_period(self):
        for rec in self.filtered('date'):
            month = rec.date.month
            year = rec.date.year

            rec.period = str(month) + '/' + str(year)

    account_id = fields.Many2one("account.account", string="Cuenta")
    company_id = fields.Many2one('res.company', string=u"Compañía", default=lambda self: self.env.user.company_id)

    # Grupo segun banco
    current_balance1 = fields.Float(string="Balance disponible segun banco")  # Entrada manual
    current_checks1 = fields.Float(string="Créditos en transito", compute='_compute_current_checks1')  # Computado(resta)
    debit_checks1 = fields.Float(string="Débitos en transito", compute='_compute_debit_checks1')  # Computado(resta)
    final_balance1 = fields.Float(string="Balance al corte del mes", compute='_compute_final_balance1')  # Computado

    # Grupo segun libro
    previous_balance = fields.Float(string="Balance anterior", compute='_compute_previous_balance', store=True)
    issued_deposits = fields.Float(string="Depositos emitidos",
                                   compute='_compute_issued_deposits_and_current_checks2') #se suma
    current_checks2 = fields.Float(string="Créditos emitidos",
                                   compute='_compute_issued_deposits_and_current_checks2') #se resta
    final_balance2 = fields.Float(string="Balance al corte del mes")
    difference = fields.Float(string="Diferencia", compute='_compute_difference')

    # payment_ids = fields.Many2many("account.move.line")
    payment_ids = fields.Many2many("oct.bank.reconciliation.line")
    state = fields.Selection([('draft', 'Borrador'), ('generated', 'Generado'), ('canceled', 'Cancelado'), ('validated', 'Validado')], string="Estado", default="draft")
    total = fields.Float(string=u"Total de conciliación del mes", compute='_compute_total', store=False)
    able_to_modify_previous_balance = fields.Boolean(compute=set_access_for_previous_balance, store=False,
                                                     string="Tiene este usuario permitido editar el balance anterior?")
    _sql_constraints = [('period_account_id_company_id_unique', 'UNIQUE(period, account_id, company_id)', "No puede tener dos conciliaciones en la misma fecha y la misma cuenta bancaria")]

    @api.depends('date', 'account_id')
    def _compute_previous_balance(self):
        for rec in self:
            previous_reconciliation = self.env['oct.bank.reconciliation'].search(
                                    [('account_id', '=', rec.account_id.id),
                                     ('company_id', '=', rec.company_id.id),
                                     ('date', '<', rec.date)], limit=1, order='date desc')

            if not previous_reconciliation:
                return
            if previous_reconciliation.state not in ['validated']:
                raise ValidationError(u"La conciliación del periodo anterior no está validada.")
            rec.previous_balance = previous_reconciliation.total

    @api.depends('previous_balance', 'issued_deposits', 'current_checks2', 'debit_checks1')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.previous_balance + rec.issued_deposits - rec.current_checks2 - rec.debit_checks1

    @api.depends('final_balance1', 'total')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.final_balance1 - rec.total

    def generate_reconciliation(self):
        domain = [('date', '<', self.date), ('state', 'in', ['validated']),
                  ('account_id', '=', self.account_id.id), ('company_id', '=', self.company_id.id),
                  ('id', '!=', self.id)]# This filter is in case someone generates after saving
                                        # the record would have id in database
        previous_reconciliation = self.env['oct.bank.reconciliation'].search(domain, order='date asc')

        unvalidated_reconciliations_previous = self.env['oct.bank.reconciliation.line']

        for line in previous_reconciliation.mapped('payment_ids').filtered(lambda p: not p.bank_reconciliated):
            # Bellow search is in case a reconciliation line passes through 2 or more months being unreconciliated,
            # so we dont add it again to the list
            search = unvalidated_reconciliations_previous.filtered(lambda x: x.date == line.date and
                                                                       x.ref == line.ref and
                                                                       x.account_id == line.account_id and
                                                                       x.partner_id == line.partner_id and
                                                                       x.debit == line.debit and
                                                                       x.credit == line.credit and
                                                                       x.bank_reconciliated == line.bank_reconciliated)
            if not search:
                unvalidated_reconciliations_previous += line

        for urp in unvalidated_reconciliations_previous:
            urp_reconciled = previous_reconciliation.mapped('payment_ids').filtered(lambda x: x != urp and
                                                                                       x.date == urp.date and
                                                                                       x.ref == urp.ref and
                                                                                       x.account_id == urp.account_id and
                                                                                       x.partner_id == urp.partner_id and
                                                                                       x.debit == urp.debit and
                                                                                       x.credit == urp.credit and
                                                                                       x.bank_reconciliated)
            if urp_reconciled:
                unvalidated_reconciliations_previous -= urp

        month, year = self.period.split('/')
        last_day = calendar.monthrange(int(year), int(month))[1]
        date_from = '{}-{}-01'.format(year, month)
        date_from = dt.strptime(date_from, '%Y-%m-%d')
        date_to = '{}-{}-{}'.format(year, month, last_day)
        date_to = dt.strptime(date_to, '%Y-%m-%d')
        unvalidated_reconciliations_current = []
        for p in self.env['account.move.line'].search([('date', '>=', date_from), ('date', '<=', date_to), ('account_id', '=', self.account_id.id), ('move_id.state', '=', 'posted')]):
            unvalidated_reconciliations_current.append(p)

        lines = []
        for line in unvalidated_reconciliations_previous:
            lines.append((0, 0, {'date': line.date,
                                 'ref': line.ref,
                                 'account_id': line.account_id.id,
                                 'partner_id': line.partner_id.id,
                                 'debit': line.debit,
                                 'credit': line.credit}))

        for line in unvalidated_reconciliations_current:
            ref = line.ref or ''
            if line.payment_id:
                ref += (' || ' + line.payment_id.name) if line.payment_id.name else ''
                if line.payment_id.ref:
                    ref += ' || ' + str(line.payment_id.ref)

            debit = True if line.debit > 0 else False
            diff_currency = self.account_id.currency_id != self.company_id.currency_id if self.account_id.currency_id else False
            debit_amount = 0
            credit_amount = 0

            if debit:
                debit_amount = abs(line.amount_currency) if diff_currency else line.debit
            else:
                credit_amount = abs(line.amount_currency) if diff_currency else line.credit

            lines.append((0, 0, {'date': line.date,
                                 'ref': ref,
                                 'account_id': line.account_id.id,
                                 'partner_id': line.partner_id.id,
                                 'debit': debit_amount,
                                 'credit': credit_amount}))
        self.payment_ids.unlink()
        self.write({'payment_ids': lines, 'state': 'generated'})

    @api.depends('payment_ids', 'payment_ids.bank_reconciliated')
    def _compute_issued_deposits_and_current_checks2(self):
        for rec in self:
            if rec.period and rec.payment_ids:
                month, year = rec.period.split('/')
                date_from = '{}-{}-01'.format(year, month)
                date_from = dt.strptime(date_from, '%Y-%m-%d').date()
                rec.issued_deposits = sum(line.debit for line in rec.payment_ids if line.date >= date_from)
                rec.current_checks2 = sum(line.credit for line in rec.payment_ids if line.date >= date_from)
            else:
                rec.issued_deposits = 0.0
                rec.current_checks2 = 0.0

    def validate_reconciliation(self):
        if float_compare(self.difference, 0.0, precision_rounding=0.01) != 0:
            raise ValidationError("No se puede validar una conciliación con diferencia positiva o negativa.")
        self.state = "validated"

    def validate_lines_reconciliation(self):
        for rec in self.payment_ids:
            rec.bank_reconciliated = True

    def cancel_reconciliation(self):
        for line in self.payment_ids:
            line.bank_reconciliated = False
        self.state = "canceled"

    def return_draft(self):
        self.state = "draft"

    @api.depends('payment_ids.bank_reconciliated')
    def _compute_current_checks1(self):
        for rec in self:
            rec.current_checks1 = sum(line.credit if not line.bank_reconciliated else 0.0 for line in rec.payment_ids)

    @api.depends('payment_ids.bank_reconciliated')
    def _compute_debit_checks1(self):
        for rec in self:
            rec.debit_checks1 = sum(line.debit if not line.bank_reconciliated else 0.0 for line in rec.payment_ids)

    @api.depends('current_balance1', 'current_checks1')
    def _compute_final_balance1(self):
        for rec in self:
            rec.final_balance1 = rec.current_balance1 - rec.current_checks1