from odoo import fields, models, api


class DgiiReport(models.Model):
    _inherit = 'dgii.reports'

    # IR17
    # Fields
    ret_rent = fields.Monetary(string="Alquileres")
    ret_service_honoraries = fields.Monetary(string="Honorarios por Servicios")
    ret_award = fields.Monetary(string="Premios")
    ret_title_transfer = fields.Monetary(string="Transferencia de Titulo y Propiedades")
    ret_dividends = fields.Monetary(string="Dividendos")
    ret_legal_person10 = fields.Monetary(string="Intereses a personas Juridicas 10%")
    ret_legal_person5 = fields.Monetary(string="Intereses a personas Juridicas 5%")
    ret_physical_person10 = fields.Monetary(string="Intereses a personas Fisicas 10%")
    ret_physical_person5 = fields.Monetary(string="Intereses a personas Fisicas 5%")
    ret_remittances = fields.Monetary(string="Remesas al exterior")
    ret_special_remittances = fields.Monetary(string="Remesas acuerdos especiales")
    ret_local_supplier = fields.Monetary(string="Pago a proveedores del estado")
    ret_phone_set = fields.Monetary(string="Juegos Telefónicos")
    ret_capital_earning = fields.Monetary(string="Ganancia de capital")
    ret_internet_games = fields.Monetary(string="Juegos via internet")
    ret_others_rent10 = fields.Monetary(string="Otras rentas 10%")
    ret_others_rent2 = fields.Monetary(string="Otras rentas 2%")
    ret_others_ret = fields.Monetary(string="Otras retenciones")
    ret_finance_entity_legal = fields.Monetary(
        string="Intereses pagados por entidades financieras a personas juridicas")
    ret_finance_entity_physical = fields.Monetary(
        string="Intereses pagados por entidades financieras a personas fisicas")
    ret_total = fields.Monetary(string="Total otras retenciones")

    @api.model
    def _compute_ir17_data(self):
        for rec in self:
            invoice_ids = self._get_invoices(['posted'],
                                             ['in_invoice', 'in_refund'])
            ret_dict = self._get_retention_vals_dict()
            for inv in invoice_ids:
                def return_balance(inv_line):
                    return inv.currency_id._convert(inv_line.amount_currency, inv.company_id.currency_id, inv.company_id,
                                                   inv.date or fields.Date.context_today(self))
                ret_dict.update({
                    'ret_rent':  ret_dict['ret_rent'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '01' and abs(l.tax_line_id.amount) == 10).mapped(return_balance))),
                    'ret_service_honoraries': ret_dict['ret_service_honoraries'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '02' and abs(l.tax_line_id.amount) == 10).mapped(return_balance))),
                    'ret_award': ret_dict['ret_award'] + 0,
                    'ret_title_transfer': ret_dict['ret_title_transfer'] + 0,
                    'ret_dividends': ret_dict['ret_dividends'] + 0,
                    'ret_legal_person10': ret_dict['ret_legal_person10'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '05').mapped(return_balance))),
                    'ret_legal_person5': ret_dict['ret_legal_person5'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '05').mapped(return_balance))),
                    'ret_physical_person10': ret_dict['ret_physical_person10'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '06').mapped(return_balance))),
                    'ret_physical_person5': ret_dict['ret_physical_person5'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '06').mapped(return_balance))),
                    'ret_remittances': ret_dict['ret_remittances'] + 0,
                    'ret_special_remittances': ret_dict['ret_special_remittances'] + 0,
                    'ret_local_supplier': ret_dict['ret_local_supplier'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '07' and abs(l.tax_line_id.amount) == 5).mapped(return_balance))),
                    'ret_phone_set': ret_dict['ret_phone_set'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '08' and abs(l.tax_line_id.amount) == 5).mapped(return_balance))),
                    'ret_capital_earning': ret_dict['ret_capital_earning'] + 0,
                    'ret_internet_games': ret_dict['ret_internet_games'] + 0,
                    'ret_others_rent10': ret_dict['ret_others_rent10'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '03' and abs(l.tax_line_id.amount) == 10).mapped(return_balance))),
                    'ret_others_rent2': ret_dict['ret_others_rent2'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '03' and abs(l.tax_line_id.amount) == 2).mapped(return_balance))),
                    'ret_others_ret': ret_dict['ret_others_ret'] + abs(sum(inv.line_ids.filtered(lambda l: l.account_id.account_fiscal_type == 'ISR' and l.account_id.isr_retention_type == '03' and abs(l.tax_line_id.amount) not in [2, 10]).mapped(return_balance))),
                    'ret_finance_entity_legal': ret_dict['ret_finance_entity_legal'] + 0,
                    'ret_total': 0,
                })
            ret_dict['ret_total'] = sum([v for k, v in ret_dict.items() if k != 'ret_total'])
            rec._set_retention_fields_vals(ret_dict)

    def _get_retention_vals_dict(self):
        return {
            'ret_rent': 0,
            'ret_service_honoraries': 0,
            'ret_award': 0,
            'ret_title_transfer': 0,
            'ret_dividends': 0,
            'ret_legal_person10': 0,
            'ret_legal_person5': 0,
            'ret_physical_person10': 0,
            'ret_physical_person5': 0,
            'ret_remittances': 0,
            'ret_special_remittances': 0,
            'ret_local_supplier': 0,
            'ret_phone_set': 0,
            'ret_capital_earning': 0,
            'ret_internet_games': 0,
            'ret_others_rent10': 0,
            'ret_others_rent2': 0,
            'ret_others_ret': 0,
            'ret_finance_entity_legal': 0,
        }

    def _set_retention_fields_vals(self, ret_dict):
        self.write(ret_dict)

    @api.model
    def _generate_report(self):
        self._compute_ir17_data()
        return super(DgiiReport, self)._generate_report()
