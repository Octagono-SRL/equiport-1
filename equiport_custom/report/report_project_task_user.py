# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models, tools


class ReportProjectTaskUser(models.Model):
    _inherit = ['report.project.task.user.fsm']

    # Form rescue and assistant

    task_id = fields.Many2one(comodel_name='project.task', default=lambda s: s.id)
    transport_name = fields.Char(related='task_id.transport_name', string="Nombre del transporte")
    driver_name = fields.Char(related='task_id.driver_name', string="Nombre del chofer")
    rescue_location = fields.Char(related='task_id.rescue_location', string="Lugar de rescate")
    employee_worker_ids = fields.Many2many(related='task_id.employee_worker_ids', string="Personal de rescate")

    effective_date = fields.Date(related='task_id.effective_date', string="Fecha efectiva")
    arrive_time = fields.Float(related='task_id.arrive_time', string="Hora de llegada")
    leave_time = fields.Float(related='task_id.leave_time', string="Hora de salida")
    km_travelled = fields.Float(string="Km recorridos")
    main_cause = fields.Selection([('bad_use', 'Mal uso'), ('wear', 'Deterioro')], string="Causa rescate")
    rescue_notes = fields.Char(string="Observaciones")
    container = fields.Char(string="Contenedor")
    chassis = fields.Char(string="Chasis")
    gen_set = fields.Char(string="Gen set")
    damage_type_ids = fields.Many2many(related='task_id.damage_type_ids',
                                       string="Tipo de averia ids")
    value_damage_type = fields.Char(string="Tipo de averia")
    product_line_value = fields.Char(string="Materiales")
    diet_value = fields.Float(string="Dieta")
    toll_tax_value = fields.Float(string="Precio de Peaje")
    time_product_value = fields.Float(string="Costo por trabajo realizado")
    km_travelled_product_value = fields.Float(string="Costo por kilometros")
    fuel_product_value = fields.Float(string="Costo de combustible")
    fuel_product_qty = fields.Float(string="Cantidad de combustible")
    fuel_product_price = fields.Float(string="Precio del galón")
    product_amount_total = fields.Float(string="Precio de las piezas")
    rescue_amount_total = fields.Float(string="Total de rescate")

    def _select(self):
        return super(ReportProjectTaskUser, self)._select() + """,
            t.id AS task_id,
            t.main_cause,
            t.km_travelled,
            t.rescue_notes,
            t.container,
            t.chassis,
            t.gen_set,
            t.value_damage_type,
            t.product_line_value,
            t.diet_value,
            t.toll_tax_value,
            t.time_product_value,
            t.km_travelled_product_value,
            t.fuel_product_value,
            t.fuel_product_qty,
            t.fuel_product_price,
            t.product_amount_total,
            t.rescue_amount_total
            """

    def _group_by(self):
        return super(ReportProjectTaskUser, self)._group_by() + """,
            t.main_cause,
            t.km_travelled,
            t.rescue_notes,
            t.container,
            t.chassis,
            t.gen_set,
            t.value_damage_type,
            t.product_line_value
            """
