from odoo import fields, models, api


class DgiiReport(models.Model):
    _inherit = 'dgii.reports'

    # IR17
    # retention_summary_ids = fields.One2many('dgii.reports.retention.summary',
    #                                        'dgii_report_id',
    #                                        string='Retenciones',
    #                                        copy=False)
    # Fields
    ret_rent = fields.Monetary(string="Alquileres")
    ret_service_honoraries = fields.Monetary(string="Honorarios por Servicios")
    ret_award = fields.Monetary(string="Premios")
    ret_title_transfer = fields.Monetary(string="Transderencia de Titulo y Propiedades")
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

    @api.model
    def _compute_ir17_data(self):
        for rec in self:
            invoice_ids = self._get_invoices(['posted'],
                                             ['in_invoice', 'in_refund'])
            ret_dict = self._get_retention_vals_dict()

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

# class DgiiReportRetentionSummary(models.Model):
#     _name = 'dgii.reports.retention.summary'
#     _description = "DGII Report retention Summary"
#     _order = 'sequence'
#
#     name = fields.Char()
#     sequence = fields.Integer()
#     qty = fields.Integer()
#     amount = fields.Monetary()
#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Currency',
#         required=True,
#         default=lambda self: self.env.user.company_id.currency_id)
#     dgii_report_id = fields.Many2one('dgii.reports', ondelete='cascade')
