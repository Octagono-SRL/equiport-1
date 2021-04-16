# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campos para definir Contenedores, Gen set, Chasis
    unit_type = fields.Selection([('container', 'Contenedor'), ('gen_set', 'Gen Set'), ('chassis', 'Chasis')],
                                 string="Tipo de unidad")
    unit_brand = fields.Many2one(comodel_name='fleet.vehicle.model.brand',
                                 string="Marca de unidad")
    unit_model = fields.Many2one(comodel_name='fleet.vehicle.model',
                                 string="Modelo de unidad")
    unit_year = fields.Char(string="Año de unidad")
    container_type = fields.Selection([('dry', 'Seco'), ('cooled', 'Refrigerado')], string="Tipo de contenedor")

    # Campos servicio (Get In/Get Out) para definir a quien pertenece la unidad y su tiempo en el patio

    external_owner = fields.Boolean(string="Unidad Externa")
    owner_partner_id = fields.Many2one(comodel_name='res.partner', string="Propietario")
    gate_in_date = fields.Date(string="Fecha de entrada")
    gate_out_date = fields.Date(string="Fecha de salida")
    storage_rate = fields.Monetary(string="Tasa de estadia")

    # Campos para manejo de inventario

    is_tool = fields.Boolean(string="Es herramienta")
    assign_user_id = fields.Many2one(comodel_name='res.users', string="Asignado a")