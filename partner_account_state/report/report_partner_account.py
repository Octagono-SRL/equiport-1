# -*- coding: utf-8 -*-
import datetime
import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import xlsxwriter
import base64
# import string


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
    report = fields.Binary(string='Reporte')


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

    def generate_xlsx_report(self):
        this = self[0]

        mfl_date = "{0}{1}{2}".format(self.date_to.year, self.date_to.month, self.date_to.day)
        file_path = '/tmp/Estado de Cuenta-{}.xlsx'.format(mfl_date)

        workbook = xlsxwriter.Workbook(file_path, {'strings_to_numbers': True})
        worksheet = workbook.add_worksheet()

        # Add a number format for cells with money.
        money = workbook.add_format({'num_format': '$#,##0'})

        # Headers del Excel
        file_header = ['Número de Documento', 'Fecha de Documento', 'NCF', 'Plazo de pago', 'Días Transc.', 'Total', 'Pendiente']
        bold = workbook.add_format({'font_size': 14,
                                    'bold': 1})

        self.ensure_one()

        # List the alphabet
        # Esto es para graduar las lineas del excel
        # alphabet = ["%s%d" % (l, 1) for l in string.ascii_uppercase]
        date_from = self.date_from
        date_to = self.date_to

        #Campos de fechas en reporte
        worksheet.write(2, 5, 'Desde:')
        worksheet.write(2, 6, date_from)
        worksheet.write(3, 6, 'A la fecha:')
        worksheet.write(3, 5, date_to)

        worksheet.write(1, 1, 'Datos del Cliente')

        #Nombre de cliente
        worksheet.write(2, 1, 'Cliente')
        worksheet.write(2, 2, self.company_id.partner_id.name)

        #RNC
        worksheet.write(2, 3, 'RNC')
        worksheet.write(2, 4, self.company_id.vat)

        #Dirección
        worksheet.write(3, 1, 'Dirección')
        worksheet.write(3, 2, self.partner_id.street + ', ' + self.partner_id.city + ', ' + self.partner_id.country_id.name)

        for col, header in enumerate(file_header):
            worksheet.write(col, 2, str(header), bold)

        lines = self.line_ids

        pos = 0
        for i, line in enumerate(lines):
            pos += 1
            worksheet.write(i + 4, 3, str(line.move_id.name), bold)
            worksheet.write(i + 4, 4, str(line.invoice_date), bold)
            worksheet.write(i + 4, 5, str(line.l10n_do_fiscal_number), bold)
            worksheet.write(i + 4, 6, str(line.invoice_payment_term_id.name), bold)
            worksheet.write(i + 4, 7, str(line.trans_days), bold)
            worksheet.write(i + 4, 8, str(line.amount_total), bold)
            worksheet.write(i + 4, 9, str(line.amount_residual), bold)

        amount_total = sum(lines.mapped('amount_total'))
        amount_residual = sum(lines.mapped('amount_residual'))

        worksheet.write(pos + 5, 9, sum(lines.mapped('amount_residual')), money)
        worksheet.write(pos + 6, 9, (amount_total - amount_residual), money)
        pos = 0

        # format1 = workbook.add_format({'font_size': 14,
        #                               'align': 'vcenter',
        #                               'Bold': True})

        workbook.close()

        this.write({
            'report_name': file_path.replace('/tmp/', ''),
            'report': base64.b64encode(
                open(file_path, 'rb').read())
        })

        # return {
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'historical.balance.report.wizard',
        #     'view_mode': 'form',
        #     'view_type': 'form',
        #     'res_id': this.id,
        #     'views': [(False, 'form')],
        #     'target': 'new',
        # }


class ReportPartnerAccountLine(models.TransientModel):
    _name = 'report.partner.account.line'
    _description = _("Modelo para visualizar las lineas del estado de cuentas de los clientes")
    _order = 'trans_days DESC'

    report_partner_id = fields.Many2one(comodel_name='report.partner.account')
    partner_id = fields.Many2one(related='report_partner_id.partner_id', string=_('Customer'))
    move_id = fields.Many2one(string=_("Document Number"), comodel_name='account.move')
    invoice_date = fields.Date(related='move_id.invoice_date', string=_("Document Date"))
    move_date = fields.Date(related='move_id.date')
    invoice_payment_term_id = fields.Many2one(related='move_id.invoice_payment_term_id')
    trans_days = fields.Integer(compute="_compute_trans_days", string=_("Aging"), store=True)
    l10n_do_fiscal_number = fields.Char(related='move_id.l10n_do_fiscal_number', string=_("NCF"))
    amount_total = fields.Monetary(related='move_id.amount_total', string=_("Total"))
    amount_residual = fields.Monetary(related='move_id.amount_residual', string=_("Amount Residual"))
    currency_id = fields.Many2one(related='move_id.currency_id', string=_("Currency"))
    company_id = fields.Many2one(comodel_name='res.company', default=lambda s: s.env.company)

    @api.depends('move_id', 'invoice_date', 'invoice_payment_term_id')
    def _compute_trans_days(self):
        for rec in self:
            rec.trans_days = (datetime.date.today() - (rec.invoice_date or rec.move_date)).days
