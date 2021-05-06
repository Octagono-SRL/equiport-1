# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import ValidationError


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def generate_order_comparison(self):
        self.ensure_one()

        # Busqueda de las vistas del modelo
        tree_view_id = self.env.ref('equiport_custom.report_order_comparison_tree_view').id

        # Definicion de variables de entorno para el modelo
        model_report_view = self.env['report.order.comparison']

        # Limpiando registros existentes en la tabla visual
        rec_search = model_report_view.search([])
        if len(rec_search) > 0:
            rec_search.unlink()

        # Recolectando y procesando informacion
        model_orders = self.env['purchase.order']
        data = model_orders.search([
            ('origin', '=', self.name)
        ])

        if data:
            partners = list(set(data.mapped('partner_id')))
            products = list(set(data.mapped('order_line').mapped('product_id')))

            for par in partners:
                for prod in products:
                    info = data.order_line.filtered(lambda l: l.product_id == prod and l.partner_id == par)

                    if not info:
                        break

                    model_report_view.create({
                        'partner_id': par.id,
                        'order_id': info.order_id.id,
                        'product_id': prod.id,
                        'price_unit': info.price_unit,
                        'product_qty': info.product_uom_qty,
                        'discount': info.discount,
                        'date_approve': info.order_id.date_approve,
                        'subtotal': info.price_subtotal,
                    })

            action = {'type': 'ir.actions.act_window',
                      'views': [(tree_view_id, 'tree')],
                      'view_mode': 'tree',
                      'name': 'Reporte comparativo',
                      'res_model': 'report.order.comparison',
                      'context': {},
                      }

            return action

        else:
            raise ValidationError("El reporte no puede ser generado. No existen ordenes de compras.")