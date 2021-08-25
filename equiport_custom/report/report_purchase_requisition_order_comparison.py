# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ReportOrderComparison(models.TransientModel):
    _name = 'report.order.comparison'
    _description = "Modulo para realizar comparacion de precios por productos dentro de los acuerdos de compra"

    name = fields.Char(string='name', compute='_compute_rec_name')
    order_id = fields.Many2one(comodel_name='purchase.order', string='Referencia', readonly=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Producto', readonly=True)
    discount = fields.Float(string='Descuento(%)', readonly=True)
    date_approve = fields.Datetime(string='Fecha de aprovacion', readonly=True)
    price_unit = fields.Float(string='Precio por unidad', readonly=True)
    product_qty = fields.Float(string='Cantidad', readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', readonly=True)
    subtotal = fields.Float(string='Subtotal', readonly=True)

    def _compute_rec_name(self):
        for rec in self:
            rec.name = f"{rec.order_id.name} / {rec.partner_id.name}"
