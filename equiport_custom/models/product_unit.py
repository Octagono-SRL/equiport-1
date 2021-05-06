# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ProductState(models.Model):
    _name = 'product.state'
    _description = 'Product State'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Char(string='Activo')

class ProductGrade(models.Model):
    _name = 'product.grade'
    _description = 'ProductGrade'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Char(string='Activo')
