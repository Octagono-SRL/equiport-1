# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools, api


class RentalReport(models.Model):
    _inherit = "sale.rental.report"

    rental_subscription_id = fields.Many2one(comodel_name='sale.subscription', string="Suscripción")
    rental_template_id = fields.Many2one(comodel_name='sale.subscription.template', string="Plantilla de suscripción")
    recurring_rule_type = fields.Selection(string='Recuerrencia',
                                           help="Factura automatica en el intervalo indicado",
                                           related="rental_template_id.recurring_rule_type", readonly=True)
    recurring_interval = fields.Integer(string='Repetir', help="Repetir cada (Dia/Semana/Mes/Año)",
                                        related="rental_template_id.recurring_interval", readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    currency_rate = fields.Float('Tasa de Registro', digits=0, readonly=True, store=True)
    pickup_date = fields.Datetime('Fecha de entrega', readonly=True)
    return_date = fields.Datetime('Fecha de retorno', readonly=True)
    rental_status = fields.Selection([
        ('draft', 'Cotizacion'),
        ('sent', 'Cotiacion enviada'),
        ('pickup', 'Confirmada'),
        ('return', 'Recogida'),
        ('returned', 'Devuelta'),
        ('cancel', 'Cancelado'),
    ], string="Estado de renta")

    def _get_currency_rate(self):
        return """CASE COALESCE(so.currency_rate, 0) WHEN 0 THEN 1.0 ELSE 1/so.currency_rate END"""

    def _select(self):
        res = super(RentalReport, self)._select()
        res += """,
            sub.id AS rental_subscription_id,
            so.rental_template_id,
            so.warehouse_id,
            pickup_date,
            return_date,
            so.rental_status AS rental_status,
            %s AS currency_rate
        """ % (self._get_currency_rate())

        return res

    def _from(self):
        res = super(RentalReport, self)._from()
        res += """
            join sale_order AS so on so.id=sol.order_id
            join sale_subscription AS sub on sub.id=so.rental_subscription_id
        """
        return res
