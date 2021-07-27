# -*- coding: utf-8 -*-
import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = ['account.move']

    # Gate Service
    is_gate_service = fields.Boolean(string="Servicio Gate In / Gate Out")

    def action_post(self):

        if self.is_gate_service:

            storage_rate_service = self.env.ref('equiport_custom.storage_rate_product')

            # Borrando lineas a actualizar

            storage_rate_lines = self.invoice_line_ids.filtered(lambda l: l.product_id == storage_rate_service)
            storage_rate_lines.unlink()

            # XXXXXXXXXXXXXXXXXXXXXXXX

            invoice_lines = []
            for inv_line in self.invoice_line_ids.filtered(
                    lambda il: not il.product_id.is_gate_service and il.display_type == False):
                if inv_line.storage_rate > 0:
                    name_string = ""
                    total_days = 0
                    for serial in inv_line.reserved_lot_ids:
                        start = serial.gate_in_date
                        end = serial.gate_out_date or datetime.datetime.now()
                        diff = end - start

                        name_string += f'{serial.name} - {diff.days} días'
                        total_days += diff.days

                    val = (0, 0, {
                        'product_id': storage_rate_service.id,
                        'name': f'{inv_line.product_id.name}\n'
                                f'seriares: {name_string}',
                        'quantity': total_days,
                        'price_unit': inv_line.storage_rate,
                    })
                    invoice_lines.append(val)

            self.update({'invoice_line_ids': invoice_lines})

        res = super(AccountMove, self).action_post()

        return res

    # Invoice flow origin

    flow_origin = fields.Char(string='Generado en', compute='compute_flow_origin', store=True, tracking=True)

    @api.depends('invoice_origin', 'name')
    def compute_flow_origin(self):
        for rec in self:
            if rec.invoice_origin and rec.move_type == 'out_invoice':
                obj_list = list(map(lambda e: e.strip(), rec.invoice_origin.split(',')))
                model_list = []
                SaleOrder = self.env['sale.order']
                SaleSubscription = self.env['sale.subscription']
                RepairOrder = self.env['repair.order']
                if len(obj_list) == 1:
                    obj = obj_list[0]
                    domain = [('name', '=', obj), ('company_id', '=', rec.company_id.id)]
                    sale_order = SaleOrder.search(domain)
                    repair_order = RepairOrder.search(domain)
                    sale_subscription = SaleSubscription.search([('code', '=', obj), ('company_id', '=', rec.company_id.id)])

                    if sale_order:
                        if sale_order.is_rental_order:
                            rec.flow_origin = "Alquiler"
                        elif sale_order.is_fsm:
                            rec.flow_origin = "Servicio de campo"
                        else:
                            rec.flow_origin = "Ventas"

                    elif repair_order:
                        if repair_order.is_fleet_origin:
                            rec.flow_origin = "Flota"
                        else:
                            rec.flow_origin = "Reparaciones"
                    elif sale_subscription:
                        if sale_subscription.rental_order_id:
                            rec.flow_origin = "Alquiler recurrente"
                        else:
                            rec.flow_origin = "Subscripción"
                    else:
                        rec.flow_origin = "Sin origen"
                else:
                    for obj in obj_list:
                        domain = [('name', '=', obj), ('company_id', '=', rec.company_id.id)]
                        sale_order = SaleOrder.search(domain)
                        repair_order = RepairOrder.search(domain)
                        sale_subscription = SaleSubscription.search(domain)

                        if sale_order:
                            model_list.append(sale_order._name)
                        elif repair_order:
                            model_list.append(repair_order._name)
                        elif sale_subscription:
                            model_list.append(sale_subscription._name)

                    o_list = [True for e in model_list if e == 'sale.order']
                    r_list = [True for e in model_list if e == 'repair.order']
                    s_list = [True for e in model_list if e == 'sale.subscription']
                    if all(o_list) and (len(o_list) == len(model_list)):
                        rec.flow_origin = "Documentos combinados: Ventas"
                    elif all(r_list) and (len(r_list) == len(model_list)):
                        rec.flow_origin = "Documentos combinados: Reparaciones"
                    elif all(s_list) and (len(s_list) == len(model_list)):
                        rec.flow_origin = "Documentos combinados: Subscripciones"
                    else:
                        rec.flow_origin = "Documentos combinados"
            else:
                rec.flow_origin = "Sin origen"

    @api.constrains('invoice_origin')
    def _check_user_group_to_save(self):
        for rec in self:
            if not rec.invoice_origin and self.user_has_groups('!equiport_custom.create_customer_invoices'):
                if rec.move_type == 'out_invoice':
                    raise ValidationError(
                        "No puede crear facturas sin origen, contacte con gerencia y solicite poder realizar esta acción")


class AccountMoveLine(models.Model):
    _inherit = ['account.move.line']

    reserved_lot_ids = fields.Many2many(compute='_get_stock_reserved_lot_ids', comodel_name='stock.production.lot',
                                        relation='invoice_reserved_lot_rel', domain="[('product_id','=',product_id)]",
                                        copy=False, string="Números de serie")
    # Gate Service
    storage_rate = fields.Float(string="Tasa de estadia")

    booking = fields.Char(string="Número de reserva", compute='compute_gate_info', store=True)
    stamp = fields.Char(string="Sello", compute='compute_gate_info', store=True)
    boat = fields.Char(string="Barco", compute='compute_gate_info', store=True)

    @api.depends('sale_line_ids', 'name', 'move_id.is_gate_service')
    def compute_gate_info(self):
        for rec in self:
            booking_string = ''
            stamp_string = ''
            boat_string = ''
            if rec.move_id.is_gate_service:
                for item in rec.reserved_lot_ids:
                    booking_string += f'{item.booking}/{item.name} \n'
                    stamp_string += f'{item.stamp}/{item.name}\n'
                    boat_string += f'{item.boat}/{item.name}\n'

            rec.booking = booking_string
            rec.stamp = stamp_string
            rec.boat = boat_string

    @api.depends('sale_line_ids')
    def _get_stock_reserved_lot_ids(self):
        for rec in self:
            rec.reserved_lot_ids = [(6, 0, rec.mapped('sale_line_ids.move_ids.lot_ids').ids)]
