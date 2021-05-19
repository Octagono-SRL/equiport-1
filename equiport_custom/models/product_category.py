from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    description = fields.Char("Detalles de categoria")
