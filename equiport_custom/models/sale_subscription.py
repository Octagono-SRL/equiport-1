# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleSubscription(models.Model):
    _inherit = ['sale.subscription']

    rental_order_id = fields.Many2one(comodel_name='sale.order', string="Orden de alquiler",
                                      domain=[('is_rental_order', '=', True)], ondelete='cascade')
    generated_last_invoice = fields.Boolean(string="Ultima factura generada")

    # is_readonly_user = fields.Boolean(compute='_compute_readonly_flag', store=False)
    # x_css = fields.Html(
    #     string='CSS/JS',
    #     sanitize=False,
    #     compute='_compute_readonly_flag',
    #     store=False,
    # )
    #
    # def _compute_readonly_flag(self):
    #     for rec in self:
    #         rec.x_css = False
    #         rec.is_readonly_user = False
    #         if self.env.user.has_group('equiport_custom.subscription_account_user_readonly'):
    #             rec.is_readonly_user = True
    #             rec.x_css = '<style>.o_form_button_edit, .o_form_button_create, .oe_subtotal_footer {display: none !important;}</style>'
    #             rec.x_css += """<script>
    #                     var action = document.querySelector(".o_cp_action_menus")?.lastChild
    #                     if(action){
    #                         action.style.display='none'
    #                     }
    #                     </script>"""
    #         else:
    #             rec.is_readonly_user = False
    #             rec.x_css = False

    def write(self, vals):
        res = super(SaleSubscription, self).write(vals)
        self.update_rental_lines()
        return res

    def unlink(self):
        if self.rental_order_id and self.rental_order_id.state == 'sale':
            raise ValidationError("No puede eliminar esta subscripción, debe cancelar la orden de alquiler primero.")
        res = super(SaleSubscription, self).unlink()
        return res
    # TODO en generar factura indicar la linea de cotizacion que ha sido totalmente facturada.

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
                    next_date = datetime.combine(self.recurring_next_date,
                                                 line.return_date.time() if line.return_date else datetime.now().time())

                    line.write({
                        'return_date': next_date,
                    })
                    line.product_id_change()

                    # Actualizando descripciones
                    actual_desc = line.name
                    if line.product_id.type == 'product':
                        desc_list = actual_desc.split(line.get_rental_order_line_description() or ' ')
                        if len(desc_list) == 2 and desc_list[1] == '':
                            line.name = desc_list[0]

                    # actualizando lineas de subscripcion
                    sub_line = self.recurring_invoice_line_ids.filtered(
                        lambda l: l.rental_order_line_id == line
                    )
                    if sub_line and len(sub_line) > 0:
                        sub_line[0].name = line.name
                        sub_line[0].quantity = line.product_uom_qty

                    # Actualizando precio de lineas nuevas
                    if line.new_rental_addition and len(sub_line) > 0:
                        sub_line[0].price_unit = line.price_unit


class SaleSubscriptionLine(models.Model):
    _inherit = ['sale.subscription.line']

    rental_order_line_id = fields.Many2one('sale.order.line', string="Linea de alquiler")
