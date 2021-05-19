# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def check_credit_warning(self):
        self.ensure_one()
        partner = self.partner_id
        if partner.allowed_credit:
            user_id = self.env['res.users'].search([
                ('partner_id', '=', partner.id)], limit=1)
            if user_id and not user_id.has_group('base.group_portal') or not \
                    user_id:

                confirm_sale_order = self.search([('partner_id', '=', partner.id),
                                                  ('state', '=', 'sale')])
                amount_total = 0.0
                for sale in confirm_sale_order.filtered(lambda s: len(s.invoice_ids) < 1 or s.invoice_ids.filtered(
                        lambda inv: inv.payment_state not in ['in_payment', 'paid'])):
                    amount_total += sale.amount_total
                if amount_total >= ((partner.credit_limit * partner.credit_warning)/100):
                    if not partner.over_credit:
                        msg = 'El crédito disponible' \
                              ' Monto = %s' % (round(partner.credit_limit - amount_total, 2))
                        return {'value': {}, 'warning': {'title': f'Alerta {partner.credit_warning}% del credito alcanzado',
                                                         'message': msg}}

    def check_limit(self):
        self.ensure_one()
        partner = self.partner_id
        if partner.allowed_credit:
            user_id = self.env['res.users'].search([
                ('partner_id', '=', partner.id)], limit=1)
            if user_id and not user_id.has_group('base.group_portal') or not \
                    user_id:

                confirm_sale_order = self.search([('partner_id', '=', partner.id),
                                                  ('state', '=', 'sale')])
                amount_total = 0.0
                for sale in confirm_sale_order.filtered(lambda s: len(s.invoice_ids) < 1 or s.invoice_ids.filtered(lambda inv: inv.payment_state not in ['in_payment', 'paid'])):
                    amount_total += sale.amount_total
                if amount_total > partner.credit_limit:
                    if not partner.over_credit:
                        msg = 'El crédito disponible' \
                              ' Monto = %s \nVerifique "%s" Cuentas o Limites de ' \
                              'Crédito.' % (partner.credit_limit,
                                           self.partner_id.name)
                        raise UserError('No puede confirmarse la venta.\n' + msg)

        return True

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.is_rental_order:
                order.check_limit()
        return res

    @api.constrains('amount_total')
    def check_amount(self):
        for order in self:
            if not order.is_rental_order:
                order.check_limit()