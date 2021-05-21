# -*- coding: utf-8 -*-

from odoo import api, tools, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campos para definir Contenedores, Gen set, Chasis
    unit_type = fields.Selection([('container', 'Contenedor'), ('gen_set', 'Gen Set'), ('chassis', 'Chasis')],
                                 string="Tipo de unidad")
    unit_brand = fields.Many2one(comodel_name='unit.model.brand',
                                 string="Marca de unidad")
    unit_model = fields.Many2one(comodel_name='unit.model',
                                 string="Modelo de unidad")
    unit_year = fields.Char(string="Año de unidad")
    unit_size = fields.Char(string="Tamaño de unidad")
    container_type = fields.Selection([('dry', 'Seco'), ('cooled', 'Refrigerado')], string="Tipo de contenedor")

    unit_state_id = fields.Many2one(comodel_name='product.state', string='Estado')
    unit_grade_id = fields.Many2one(comodel_name='product.grade', string='Grado')

    # Campos servicio (Get In/Get Out) para definir a quien pertenece la unidad y su tiempo en el patio

    external_owner = fields.Boolean(string="Unidad Externa")
    owner_partner_id = fields.Many2one(comodel_name='res.partner', string="Propietario")
    gate_in_date = fields.Date(string="Fecha de entrada")
    gate_out_date = fields.Date(string="Fecha de salida")
    storage_rate = fields.Monetary(string="Tasa de estadia")
    is_gate_service = fields.Boolean(string="Servicio Gate In / Gate Out")
    booking = fields.Char(string="Número de reserva")

    # Campos para manejo de inventario

    is_tool = fields.Boolean(string="Es herramienta")
    assign_user_id = fields.Many2one(comodel_name='hr.employee', string="Asignado a")

    # Ajustes para la subcripcion de alquileres

    @api.onchange('type')
    def _onchange_product_type(self):
        res = False
        if not self.rent_ok:
            res = super(ProductTemplate, self)._onchange_product_type()
        return res

    @api.onchange('recurring_invoice')
    def _onchange_recurring_invoice(self):
        res = False
        if not self.rent_ok:
            res = super(ProductTemplate, self)._onchange_recurring_invoice()
        return res

    @api.constrains('recurring_invoice', 'type')
    def _check_subscription_product(self):
        res = False
        if not self.rent_ok:
            res = super(ProductTemplate, self)._check_subscription_product()
        return res
