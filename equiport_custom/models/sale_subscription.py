# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleSubscription(models.Model):
    _inherit = ['sale.subscription']

    rental_order_id = fields.Many2one(comodel_name='sale.order', string="Orden de alquiler",
                                      domain=[('is_rental_order', '=', True)], ondelete='cascade')

    def write(self, vals):
        res = super(SaleSubscription, self).write(vals)
        self.update_rental_lines()
        return res

    def unlink(self):
        if self.rental_order_id and self.rental_order_id.state == 'sale':
            raise ValidationError("No puede eliminar esta subscripción, debe cancelar la orden de alquiler primero.")
        res = super(SaleSubscription, self).unlink()
        return res

    def generate_recurring_invoice(self):
        res = super(SaleSubscription, self).generate_recurring_invoice()
        self.update_rental_lines()

        return res

    def update_rental_lines(self):

        if self.rental_order_id:
            lines = self.rental_order_id.order_line.filtered(lambda l: l.product_id.rent_ok)
            if lines:
                # Asignando fecha de subcripcion a lineas de alquiler
                for line in lines:
                    next_date = datetime.combine(self.recurring_next_date, line.return_date.time())

                    line.write({
                        'return_date': next_date,
                    })
                    line.product_id_change()

                    # actualizando lineas de subscripcion
                    sub_line = self.recurring_invoice_line_ids.filtered(
                        lambda l: l.rental_order_line_id == line
                    )
                    if sub_line:
                        sub_line[0].name = line.name
                        sub_line[0].quantity = line.product_uom_qty

                    # Actualizando precio de lineas nuevas
                    if line.new_rental_addition:
                        sub_line[0].price_unit = line.price_unit


class SaleSubscriptionLine(models.Model):
    _inherit = ['sale.subscription.line']

    rental_order_line_id = fields.Many2one('sale.order.line', string="Linea de alquiler")
