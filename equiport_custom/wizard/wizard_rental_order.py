# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RentalProcessing(models.TransientModel):
    _inherit = 'rental.order.wizard'

    def apply(self):
        res = super(RentalProcessing, self).apply()

        if self.status == 'pickup':
            for line in self.rental_wizard_line_ids:
                if line.product_id.tracking == 'serial':
                    if not any(self.rental_wizard_line_ids.mapped('pickedup_lot_ids')):
                        raise ValidationError("Coloque un serial para la unidad a recoger")
            lines = []
            pick_output = self.env['stock.picking'].create({
                # 'name': f'Movimiento de Alquiler: Entrega {self.order_id.name}',
                'partner_id': self.order_id.partner_id.id,
                'picking_type_id': self.env.ref('stock.picking_type_out').id,
                'location_id': self.order_id.warehouse_id.lot_stock_id.id,
                'location_dest_id': self.order_id.company_id.rental_loc_id.id,
                'move_lines': lines,
                'is_rental': True,
                'sale_id': self.order_id.id,
                'origin': self.order_id.name,
            })
            pick_output.name += f'/Movimiento de Alquiler: Entrega {self.order_id.name}'

            for line in self.order_id.order_line.filtered(lambda l: l.product_id.type == 'product'):
                check_list = self.order_id.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing').mapped(
                    'move_line_ids').ids
                move_line_ids = self.env['stock.move.line'].search(
                    [('product_id', '=', line.product_id.id), ('lot_id', '=', line.pickedup_lot_ids.ids), ('id', 'not in', list(check_list))])
                if move_line_ids:

                    move_line_id = move_line_ids.filtered(lambda ml: self.order_id.name in ml.reference.split(' '))

                    move_line_id.rent_state = 'rented'
                    move_line_id.lot_id.rent_state = 'rented'
                    move_line_id.picking_id = pick_output.id
                    pick_output.move_lines += move_line_id.move_id
            self.order_id.picking_ids += pick_output
            pick_output.state = 'assigned'

        elif self.status == 'return':
            lines = []
            pick_input = self.env['stock.picking'].create({
                # 'name': f'Movimiento de Alquiler: Devolución {self.order_id.name}',
                'partner_id': self.order_id.partner_id.id,
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
                'location_id': self.order_id.company_id.rental_loc_id.id,
                'location_dest_id': self.order_id.warehouse_id.lot_stock_id.id,
                'move_lines': lines,
                'is_rental': True,
                'sale_id': self.order_id.id,
                'origin': self.order_id.name,
            })
            pick_input.name += f'/Movimiento de Alquiler: Devolución {self.order_id.name}'

            for line in self.order_id.order_line.filtered(lambda l: l.product_id.type == 'product'):
                check_list = self.order_id.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming').mapped(
                    'move_line_ids').ids
                move_line_ids = self.env['stock.move.line'].search(
                    [('product_id', '=', line.product_id.id), ('location_id', '=', line.company_id.rental_loc_id.id),
                     ('id', 'not in', list(check_list)), ('rent_state', '=', False)])
                if move_line_ids:
                    move_line_id = move_line_ids.filtered(lambda ml: self.order_id.name in ml.reference.split(' '))
                    # if not move_line_id.picking_id:
                    move_line_id.picking_id = pick_input.id
                    pick_input.move_lines += move_line_id.move_id
            self.order_id.picking_ids += pick_input
            pick_input.state = 'assigned'

        return res
