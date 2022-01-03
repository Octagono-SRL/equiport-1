# -*- coding: utf-8 -*-

from odoo import api, tools, fields, models, _
from odoo.exceptions import ValidationError

LONG_OPTIONS = [('20', '20'), ('40', '40'), ('45', '45')]
TYPE = [('0', 'Seco'), ('1', 'Refrigerado')]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Flota

    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string="Vehiculo")
    is_vehicle = fields.Boolean(string="Es vehiculo")
    is_tire_product = fields.Boolean(string="Es Neumatico", store=True, compute='_compute_is_tire')

    @api.depends('categ_id', 'company_id', 'company_id.tire_product_category', 'company_id.category_count')
    def _compute_is_tire(self):
        for rec in self:
            if rec.categ_id in rec.company_id.tire_product_category or rec.categ_id in self.env.company.tire_product_category:
                rec.is_tire_product = True
            else:
                rec.is_tire_product = False

    # Campos para definir Contenedores, Gen set, Chasis
    unit_type = fields.Selection([('container', 'Contenedor'), ('gen_set', 'Gen Set'), ('chassis', 'Chasis')],
                                 string="Tipo de unidad")
    unit_brand_id = fields.Many2one(comodel_name='unit.model.brand',
                                    string="Marca de unidad")
    unit_model_id = fields.Many2one(comodel_name='unit.model',
                                    string="Modelo de unidad")

    unit_size_id = fields.Many2one('unit.model.size', string="Tamaño de unidad")

    container_type_id = fields.Many2one('unit.model.type', string="Tipo de contenedor")

    # Campos servicio (Get In/Get Out) para definir a quien pertenece la unidad y su tiempo en el patio

    is_gate_service = fields.Boolean(string="Servicio Gate In / Gate Out")

    # Campos para manejo de inventario
    product_use = fields.Text(string="Uso", translate=True)
    is_tool = fields.Boolean(string="Es herramienta")
    tool_brand_id = fields.Many2one(comodel_name='tool.brand',
                                    string="Marca de Herramienta")
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
