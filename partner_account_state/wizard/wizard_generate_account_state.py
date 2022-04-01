from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class WizardGenerateAccountState(models.TransientModel):
    _name = 'wizard.generate.account.state'
    _description = 'Wizard to select details for account state'

    currency_id = fields.Many2one(comodel_name='res.currency', string="Moneda")
    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta", default=fields.Date.today())
    partner_id = fields.Many2one(comodel_name='res.partner', default=lambda s: s._context.get('active_id'))

    def generate_account_state(self):
        self.ensure_one()

        # Busqueda de las vistas del modelo
        form_view_id = self.env.ref('partner_account_state.report_partner_account_from_view').id

        # Definicion de variables de entorno para el modelo
        model_report_view = self.env['report.partner.account']

        # Limpiando registros existentes en la tabla visual
        rec_search = model_report_view.search([])
        if len(rec_search) > 0:
            rec_search.unlink()

        values = {}
        if not self.partner_id.invoice_ids and not self.partner_id.unpaid_invoices:
            raise ValidationError("El reporte no puede ser generado. No existen ordenes de compras confirmadas.")
        if self.partner_id.unpaid_invoices:
            report_lines = []
            if self.date_from:
                for inv in self.partner_id.unpaid_invoices.filtered(
                        lambda s: s.state == 'posted' and s.currency_id == self.currency_id and (
                                self.date_from <= s.invoice_date <= self.date_to)):
                    report_lines.append((0, 0, {
                        'move_id': inv.id
                    }))
            else:
                for inv in self.partner_id.unpaid_invoices.filtered(
                        lambda s: s.state == 'posted' and s.currency_id == self.currency_id and s.invoice_date <= self.date_to):
                    report_lines.append((0, 0, {
                        'move_id': inv.id
                    }))
            values.update({
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'credit_limit': self.partner_id.credit_limit,
                'line_ids': report_lines
            })

        # elif self.unpaid_invoices:
        #     report_lines = []
        #     for inv in self.unpaid_invoices:
        #         report_lines.append((0, 0, {
        #             'move_id': inv.id
        #         }))
        #     values.update({
        #         'partner_id': self.id,
        #         'credit_limit': self.credit_limit,
        #         'line_ids': report_lines
        #     })

        account_state = model_report_view.create(values)

        action = {'type': 'ir.actions.act_window',
                  'views': [(form_view_id, 'form')],
                  'view_mode': 'form',
                  'name': _('Estado de Cuenta'),
                  'res_model': 'report.partner.account',
                  'res_id': account_state.id,
                  }

        return action
