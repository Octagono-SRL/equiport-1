# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ComparisonReportView(models.TransientModel):
    _name = 'comparison.report.view'

    name = fields.Char(string='name', compute='_compute_rec_name')
    order_id = fields.Many2one(comodel_name='purchase.order', string='Referencia', readonly=True)
    product_id = fields.Many2one(comodel_name='product.template', string='Producto', readonly=True)
    last_price = fields.Float(string='Precio anterior', readonly=True)
    last_discount = fields.Float(string='Descuento anterior (%)', readonly=True)
    last_date_approve = fields.Datetime(string='Fecha anterior', readonly=True)
    recent_date_approve = fields.Datetime(string='Fecha actual', readonly=True)
    recent_price = fields.Float(string='Precio actual', readonly=True)
    recent_discount = fields.Float(string='Descuento actual (%)', readonly=True)
    variation = fields.Float(string='Variación en precio', readonly=True, compute='_compute_variation')
    discount_variation = fields.Float(string='Variación en descuento (%)', readonly=True, compute='_compute_variation')
    percent_variation = fields.Float(string='Variación en precio (%)', readonly=True, compute='_compute_variation')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', readonly=True)
    total = fields.Float(string='Neto', readonly=True, compute='_compute_variation')

    def _compute_rec_name(self):
        for rec in self:
            rec.name = f"{rec.order_id.name} / {rec.partner_id.name}"

    def _compute_variation(self):
        for rec in self:
            rec.variation = rec.recent_price - rec.last_price
            rec.total = rec.recent_price - (rec.recent_price * (rec.recent_discount/100))
            rec.discount_variation = rec.recent_discount - rec.last_discount
            if rec.last_price == 0.0:
                rec.percent_variation = 100
            else:
                rec.percent_variation = ((rec.recent_price - rec.last_price)/rec.last_price) * 100
