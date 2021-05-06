# -*- coding: utf-8 -*-
from odoo import fields, api, models
from odoo.exceptions import UserError, ValidationError


class UnitModel(models.Model):
    _name = 'unit.model'
    _description = ""

    name = fields.Char('Nombre de modelo', required=True)
    brand_id = fields.Many2one('unit.model.brand', 'Marca', required=True,
                               help='')
    image_128 = fields.Image(related='brand_id.image_128', readonly=True)
    active = fields.Boolean(default=True)
    # unit_type = fields.Selection([('container', 'Contenedor'), ('gen_set', 'Gen Set'), ('chassis', 'Chasis')], default='container', required=True, string="Tipo de unidad")

    @api.depends('name', 'brand_id')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.brand_id.name:
                name = record.brand_id.name + '/' + name
            res.append((record.id, name))
        return res


class UnitModelBrand(models.Model):
    _name = 'unit.model.brand'
    _description = ""

    name = fields.Char(required=True, string="Marca")
    unit_type = fields.Selection([('container', 'Contenedor'), ('gen_set', 'Gen Set'), ('chassis', 'Chasis')], default='container', required=True, string="Tipo de unidad")
    image_128 = fields.Image("Logo", max_width=128, max_height=128)
    model_count = fields.Integer(compute="_compute_model_count", string="", store=True)
    model_ids = fields.One2many('unit.model', 'brand_id')

    @api.depends('model_ids')
    def _compute_model_count(self):
        Model = self.env['unit.model']
        for record in self:
            record.model_count = Model.search_count([('brand_id', '=', record.id)])

