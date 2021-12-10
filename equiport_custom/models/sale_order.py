# -*- coding: utf-8 -*-
import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_gate_service = fields.Boolean(string="Servicio Gate In / Gate Out", compute='compute_is_gate_service')
    fsm_invoice_available = fields.Boolean(string="Facturación interna", compute='compute_fsm_invoice_available')
    is_fsm = fields.Boolean(string="Es rescate", compute='compute_fsm_invoice_available')
    section_gate_service_seq = fields.Integer(string="Sectión Gate Service")

    @api.depends('tasks_ids')
    def compute_fsm_invoice_available(self):
        for rec in self:
            rec.fsm_invoice_available = True
            if rec.tasks_count <= 1:
                for task_id in rec.tasks_ids:
                    if task_id.is_fsm and task_id.main_cause == 'wear':
                        rec.fsm_invoice_available = False
                    else:
                        rec.fsm_invoice_available = True

                if any(rec.tasks_ids.mapped('is_fsm')):
                    rec.is_fsm = True
                else:
                    rec.is_fsm = False

    # TODO Desabilido Proceso Gate In/Out
    # def _create_invoices(self, grouped=False, final=False, date=None):
    #     res = super(SaleOrder, self)._create_invoices()
    #     if res.is_gate_service:
    #
    #         invoice_lines = []
    #         for inv_line in res.invoice_line_ids.filtered(
    #                 lambda il: not il.product_id.is_gate_service and il.display_type == False):
    #             if inv_line.storage_rate > 0:
    #                 name_string = ""
    #                 total_days = 0
    #                 for serial in inv_line.reserved_lot_ids:
    #                     start = serial.gate_in_date
    #                     end = serial.gate_out_date or datetime.datetime.now()
    #                     diff = end - start
    #
    #                     name_string += f'{serial.name} - {diff.days} días'
    #                     total_days += diff.days
    #
    #                 val = (0, 0, {
    #                     'product_id': self.env.ref('equiport_custom.storage_rate_product').id,
    #                     'name': f'{inv_line.product_id.name}\n'
    #                             f'seriares: {name_string}',
    #                     'quantity': total_days,
    #                     'price_unit': inv_line.storage_rate,
    #                 })
    #                 invoice_lines.append(val)
    #
    #         res.update({'invoice_line_ids': invoice_lines})
    #
    #     return res

    # def _prepare_invoice(self):
    #     invoice_vals = super(SaleOrder, self)._prepare_invoice()
    #     if self.is_gate_service:
    #         invoice_vals.update({
    #             'is_gate_service': True,
    #         })
    #     return invoice_vals

    # def action_cancel(self):
    #     res = super(SaleOrder, self).action_cancel()
    #     if len(self.picking_ids) > 1 and self.is_gate_service:
    #         in_picking_ids = self.env['stock.picking']
    #         out_picking_ids = self.env['stock.picking']
    #         for picking in self.picking_ids:
    #             if picking.picking_type_code == 'outgoing':
    #                 out_picking_ids += picking
    #             elif picking.picking_type_code == 'incoming':
    #                 in_picking_ids += picking
    #
    #         if any(in_p.state == 'done' for in_p in in_picking_ids):
    #             raise ValidationError(
    #                 "No se puede cancelar. Se ha validado la recepcion de las unidades en este documento")
    #
    #     return res

    @api.depends('order_line')
    def compute_is_gate_service(self):
        for so in self:
            so.is_gate_service = any(line.product_id.is_gate_service for line in so.order_line)

    # TODO Desabilido Proceso Gate In/Out
    # @api.onchange('is_gate_service')
    # def set_client_warehouse(self):
    #
    #     if self.is_gate_service:
    #         self.warehouse_id = self.env.ref('equiport_custom.client_equiport_stock_warehouse').id
    #     else:
    #         self.warehouse_id = self.env.ref('stock.warehouse0').id

    # TODO Desabilido Proceso Gate In/Out
    # @api.onchange('is_gate_service')
    # def add_gate_section(self):
    #     gate_service = self.order_line.filtered(lambda l: l.product_id.is_gate_service)
    #     section_line = self.order_line.filtered(lambda l: l.name == 'Unidades')
    #     if gate_service and self.is_gate_service and not section_line:
    #         self.section_gate_service_seq = gate_service.sequence + 1
    #         order_lines = []
    #         val = (0, 0, {
    #             'display_type': 'line_section',
    #             'name': 'Unidades',
    #             'sequence': self.section_gate_service_seq,
    #         })
    #         order_lines.append(val)
    #         self.update({'order_line': order_lines})
    #     elif not gate_service and not self.is_gate_service and len(self.order_line) > 0:
    #         if section_line:
    #             section_line.unlink()
    #             self.section_gate_service_seq = 0

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
                if amount_total >= ((partner.credit_limit * partner.credit_warning) / 100):
                    if not partner.over_credit:
                        msg = 'El crédito disponible' \
                              ' Monto = %s' % (round(partner.credit_limit - amount_total, 2))
                        return {'value': {},
                                'warning': {'title': f'Alerta {partner.credit_warning}% del credito alcanzado',
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
                for sale in confirm_sale_order.filtered(lambda s: len(s.invoice_ids) < 1 or s.invoice_ids.filtered(
                        lambda inv: inv.payment_state not in ['in_payment', 'paid'])):
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


class RentalOrderLine(models.Model):
    _inherit = ['sale.order.line']

    # TODO Desabilido Proceso Gate In/Out
    storage_rate = fields.Float(string="Tasa de estadia")

    # Domain for gate products

    # @api.onchange('product_id')
    # def set_domain_for_gate_products(self):
    #     res = {}
    #     domain = [('sale_ok', '=', True), '|', ('company_id', '=', False),
    #               ('company_id', '=', self.company_id)]
    #     gate_domain = [('sale_ok', '=', False), ('rent_ok', '=', False), ('purchase_ok', '=', False), '|',
    #                    ('company_id', '=', False),
    #                    ('company_id', '=', self.company_id)]
    #
    #     if self.order_id.is_gate_service:
    #         res['domain'] = {'product_id': gate_domain}
    #     else:
    #         res['domain'] = {'product_id': domain}
    #     return res
    #
    def _prepare_invoice_line(self, **optional_values):
        res = super(RentalOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.move_ids:
            res.update(
                reserved_lot_ids=[(6, 0, self.mapped('move_ids.lot_ids').ids)],
            )

        return res
