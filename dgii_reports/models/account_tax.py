
from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _get_isr_retention_type(self):
        return [('01', 'Alquileres'),
                ('02', 'Honorarios por Servicios'),
                ('03', 'Otras Rentas'),
                ('04', 'Rentas Presuntas'),
                ('05', u'Intereses Pagados a Personas Jurídicas'),
                ('06', u'Intereses Pagados a Personas Físicas'),
                ('07', u'Retención por Proveedores del Estado'),
                ('08', u'Juegos Telefónicos')]

    purchase_tax_type = fields.Selection(
        [('itbis', 'ITBIS Pagado'),
         ('ritbis', 'ITBIS Retenido'),
         ('isr', 'ISR Retenido'),
         ('rext', 'Pagos al Exterior (Ley 253-12)'),
         ('none', 'No Deducible')],
        default="none",
        string="Tipo de Impuesto en Compra")

    isr_retention_type = fields.Selection(
        selection=_get_isr_retention_type,
        string="Tipo de Retención en ISR")