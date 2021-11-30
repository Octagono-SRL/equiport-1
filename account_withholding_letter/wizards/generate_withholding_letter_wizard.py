# -*- coding=utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

month_map = {
    '01': 'Enero',
    '02': 'Febrero',
    '03': 'Marzo',
    '04': 'Abril',
    '05': 'Mayo',
    '06': 'Junio',
    '07': 'Julio',
    '08': 'Agosto',
    '09': 'Septiembre',
    '10': 'Octubre',
    '11': 'Noviembre',
    '12': 'Diciempre',
}


class GenerateWithholdingLetterWizard(models.TransientModel):
    _name = 'generate.withholding.letter.wizard'
    _description = 'Model to generate withholding letters'

    partner_id = fields.Many2one('res.partner', string='Proveedor')
    date_from = fields.Date('Desde')
    date_to = fields.Date('Hasta')
    invoice_ids = fields.Many2many('account.move', string='Facturas')
    month = fields.Char(string='Mes')
    year = fields.Char(string='Año')
    tax_id = fields.Many2one('account.tax', string='Retención ISR')

    @api.onchange('partner_id', 'date_from', 'date_to')
    def onchange_dates(self):
        if self.date_from and self.date_to and self.partner_id:
            if self.date_from > self.date_to:
                raise ValidationError('La fecha desde debe estar antes de la fecha hasta!')
            invoices = self.env['account.move'].search([
                ('company_id', '=', self.env.user.company_id.id),
                ('partner_id', '=', self.partner_id.id),
                ('invoice_date', '>=', self.date_from),
                ('invoice_date', '<=', self.date_to),
                ('state', '=', 'posted'),
                ('move_type', '=', 'in_invoice'),
            ])

            print(invoices)

            self.month = self.date_to.month
            self.year = self.date_to.year
            self.invoice_ids = [(6, 0, invoices.ids)]

    def generate_letter(self):
        if not self.invoice_ids:
            raise ValidationError('No se puede crear una carta de retención sin facturas')

        report = self.env.ref('account_withholding_letter.withholding_letter_report').report_action(self.id, config=False)
        return report