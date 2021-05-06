# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError, ValidationError


class ComparisonReportWizard(models.TransientModel):
    _name = "comparison.report.wizard"
    _description = "Modelo para generar comparacion entre ordenes de compras confirmadas"

    date_start = fields.Date(string="Desde")
    date_end = fields.Date(string="Hasta")

    def get_all_fields_vals(self, obj):
        keys = obj.fields_get().keys()
        lista = {}
        for k in keys:
            lista[k] = obj[k]

    def _get_data_details(self):
        model_orders = self.env['purchase.order']
        records = model_orders.search([
            ('state', 'in', ['purchase', 'done']),
            ('date_approve', '>=', self.date_start),
            ('date_approve', '<=', self.date_end)
        ])
        if records:
            products_set = []
            products = list(set(line.product_id for line in records.mapped('order_line')))
            partners = list(set(line.partner_id for line in records.mapped('order_line')))
            for order in records:
                products = []
                for line in order.order_line:
                    if line.product_id not in products:
                        products.append(line.product_id)
                        products_set.append({
                            'partner_id': line.partner_id,
                            'order_id': line.order_id,
                            'product_id': line.product_id,
                            'date_approve': order.date_approve,
                            'price_unit': line.price_unit,
                            'discount': line.discount,
                        })
            return partners, products, products_set

    def view_onscreen(self):
        self.ensure_one()

        def last_price(obj):
            i = len(obj)
            return 0 if 1 >= i else obj[1]['price_unit']

        def last_discount(obj):
            i = len(obj)
            return 0 if 1 >= i else obj[1]['discount']

        def last_date(obj):
            i = len(obj)
            return False if 1 >= i else obj[1]['date_approve']

        # Busqueda de las vistas del modelo
        tree_view_id = self.env.ref('equiport_custom.comparison_report_tree_view').id
        pivot_view_id = self.env.ref('equiport_custom.comparison_report_pivot_view').id
        graph_view_id = self.env.ref('equiport_custom.comparison_report_graph_view').id

        # Definicion de variables de entorno para el modelo
        model_report_view = self.env['comparison.report.view']

        # Limpiando registros existentes en la tabla visual
        rec_search = model_report_view.search([])
        if len(rec_search) > 0:
            rec_search.unlink()

        # Recolectando y procesando informacion
        model_orders = self.env['purchase.order']
        data = model_orders.search([
            ('state', 'in', ['purchase', 'done']),
            ('date_approve', '>=', self.date_start),
            ('date_approve', '<=', self.date_end)
        ])

        if data:
            partners, products, products_set = self._get_data_details()
            for par in partners:
                for prod in products:
                    info = list(filter(lambda r: r['partner_id'] == par and r['product_id'] == prod, products_set))

                    if not info:
                        break

                    info.sort(key=lambda s: s['date_approve'], reverse=True)

                    model_report_view.create({
                        'partner_id': par.id,
                        'order_id': info[0]['order_id'].id,
                        'product_id': prod.id,
                        'last_price': last_price(info),
                        'last_discount': last_discount(info),
                        'last_date_approve': last_date(info),
                        'recent_date_approve': info[0]['date_approve'],
                        'recent_price': info[0]['price_unit'],
                        'recent_discount': info[0]['discount'],
                    })

            action = {'type': 'ir.actions.act_window',
                      'views': [(tree_view_id, 'tree'), (graph_view_id, 'graph'), (pivot_view_id, 'pivot')],
                      'view_mode': 'tree',
                      'name': _('Reporte comparativo'),
                      'res_model': 'comparison.report.view',
                      'context': {},
                      }

            return action

        else:
            raise ValidationError("El reporte no puede ser generado. No existen ordenes de compras confirmadas.")

