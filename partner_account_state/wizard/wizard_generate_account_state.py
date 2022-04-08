from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class WizardGenerateAccountState(models.TransientModel):
    _name = 'wizard.generate.account.state'
    _description = 'Wizard to select details for account state'

    currency_id = fields.Many2one(comodel_name='res.currency', string="Currency")
    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To", default=fields.Date.today())
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
            raise ValidationError(_("El reporte no puede ser generado. No existen ordenes de compras confirmadas."))
        if self.partner_id.unpaid_invoices:
            report_lines = []
            if self.date_from:
                for inv in self.partner_id.unpaid_invoices.filtered(
                        lambda s: s.state == 'posted' and s.currency_id == self.currency_id and (
                                self.date_from <= s.invoice_date <= self.date_to)):
                    report_lines.append((0, 0, {
                        'move_id': inv.id
                    }))

                for aml in self.partner_id.unreconciled_aml_ids.filtered(
                        lambda s: s.currency_id == self.currency_id):
                    check_date = aml.date_maturity if aml.date_maturity else aml.date
                    if aml.company_id == self.env.company and not aml.blocked and (
                            self.date_from <= check_date <= self.date_to):
                        if not aml.move_id.is_invoice():
                            report_lines.append((0, 0, {
                                'move_id': aml.move_id.id,
                                'move_line_id': aml.id,
                            }))
                        # amount = aml.amount_residual
                        # total_due += amount
                        # is_overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                        # if is_overdue:
                        #     total_overdue += amount
            else:
                for inv in self.partner_id.unpaid_invoices.filtered(
                        lambda s: s.state == 'posted' and s.currency_id == self.currency_id and s.invoice_date <= self.date_to):
                    report_lines.append((0, 0, {
                        'move_id': inv.id
                    }))

                for aml in self.partner_id.unreconciled_aml_ids.filtered(
                        lambda s: s.currency_id == self.currency_id):
                    check_date = aml.date_maturity if aml.date_maturity else aml.date
                    if aml.company_id == self.env.company and not aml.blocked and check_date <= self.date_to:
                        if not aml.move_id.is_invoice():
                            report_lines.append((0, 0, {
                                'move_id': aml.move_id.id,
                                'move_line_id': aml.id,
                            }))
            values.update({
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                # 'credit_limit': self.partner_id.credit_limit,
                'credit_limit': self.partner_id.property_product_pricelist.currency_id._convert(
                    self.partner_id.credit_limit,
                    self.currency_id,
                    self.env.company,
                    fields.Date.context_today(self)),
                'line_ids': report_lines
            })

        account_state = model_report_view.create(values)

        action = {'type': 'ir.actions.act_window',
                  'views': [(form_view_id, 'form')],
                  'view_mode': 'form',
                  'name': _('Account status'),
                  'res_model': 'report.partner.account',
                  'res_id': account_state.id,
                  }

        return action
