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
                if not partner_id.commercial_register or not partner_id.leasing_contract:
                    raise ValidationError("El contacto no tiene los documentos necesarios para continuar.")

        return super(SaleOrder, self).create(vals)

    def write(self, values):
        if self.is_rental_order:
            if 'partner_id' in values:

                partner_id = self.env['res.partner'].browse(values['partner_id'])
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
            if self.partner_id:
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
