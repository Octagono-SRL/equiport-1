# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        if 'is_rental_order' in vals:
            if vals['is_rental_order']:
                partner_id = self.env['res.partner'].browse(vals['partner_id'])
                if not partner_id.allowed_rental:
                    if not partner_id.commercial_register or not partner_id.leasing_contract:
                        raise ValidationError("El contacto no tiene los documentos necesarios para continuar.")

        return super(SaleOrder, self).create(vals)

    def write(self, values):
        if self.is_rental_order:
            if 'partner_id' in values:
                partner_id = self.env['res.partner'].browse(values['partner_id'])
                if not partner_id.allowed_rental:
                    if not partner_id.commercial_register or not partner_id.leasing_contract:
                        raise ValidationError("El contacto no tiene los documentos necesarios para continuar.")

        res = super(SaleOrder, self).write(values)

        return res

    def _get_order_notification(self):
        self.ensure_one()
        order = self.id
        if order:
            action = self.env.ref('sale_renting.rental_order_action')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'The following replenishment order has been generated',
                    'message': '%s',
                    # 'links': [{
                    #     'label': order.display_name,
                    #     'url': f'#action={action.id}&id={order.id}&model=sale.order',
                    # }],
                    'sticky': False,
                    'type': 'success',  # warning and error for now
                }
            }
        return False

    @api.onchange('partner_id')
    def check_rent_documents(self):
        if self.is_rental_order:
            if self.partner_id and not self.partner_id.allowed_rental:
                if not self.partner_id.commercial_register and not self.partner_id.leasing_contract:
                    return {'value': {}, 'warning': {'title': 'Contacto sin documentos',
                                                     'message': 'El contacto seleccionado no posee los siguientes documentos: '
                                                                '\n**Contrato de arrendamiento**\n'
                                                                '**Registro mercantil**'}}
                elif not self.partner_id.commercial_register:
                    return {'value': {}, 'warning': {'title': 'Contacto sin documentos',
                                                     'message': 'El contacto seleccionado no posee los siguientes documentos: '
                                                                '\n**Registro mercantil**'}}
                elif not self.partner_id.leasing_contract:
                    return {'value': {}, 'warning': {'title': 'Contacto sin documentos',
                                                     'message': 'El contacto seleccionado no posee los siguientes documentos: '
                                                                '\n**Contrato de arrendamiento**'}}

    def open_pickup(self):
        self = self.with_company(self.company_id)
        deposit_product = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        if deposit_product:
            deposit_product = self.env['product.product'].browse(int(deposit_product))
            verification_list = [(inv.payment_state in ['paid', 'in_payment']) for inv in self.invoice_ids if
                        inv.invoice_line_ids.filtered(lambda l: l.product_id == deposit_product)]
            if not any(verification_list):
                raise ValidationError("No se puede despachar sin depósito o pago registrado.")

        if len(self.invoice_ids) >= 0:
            if not self.invoice_ids.filtered(lambda inv: inv.payment_state in ['paid', 'in_payment']):
                raise ValidationError("No se puede despachar sin depósito o pago registrado.")

        res = super(SaleOrder, self).open_pickup()
        return res
