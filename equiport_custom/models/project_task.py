# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError

LONG_OPTIONS = [('20', '20'), ('40', '40'), ('45', '45')]


class ProjectTask(models.Model):
    _inherit = 'project.task'

    extra_user1_id = fields.Many2one(comodel_name='hr.employee', string="Técnico 1")
    extra_user2_id = fields.Many2one(comodel_name='hr.employee', string="Técnico 2")
    fsm_invoice_available = fields.Boolean(string="Facturación interna", compute='compute_fsm_invoice_available')

    @api.depends('main_cause')
    def compute_fsm_invoice_available(self):
        for rec in self:
            if rec.is_fsm and rec.main_cause == 'wear':
                rec.fsm_invoice_available = False
            else:
                rec.fsm_invoice_available = True

    # Form rescue and assistant

    transport_name = fields.Char(string="Nombre del transporte")
    rescue_truck_id = fields.Many2one('stock.warehouse', string="Camion de rescate",
                                      domain="[('is_mobile_stock', '=', True)]")
    consumption = fields.Float(string="Consumo en rescate")
    performance = fields.Float(string="Rendiminto del viaje")
    driver_name = fields.Char(string="Nombre del chofer")
    rescue_location = fields.Char(string="Lugar de rescate")
    employee_worker_ids = fields.Many2many(comodel_name='hr.employee', relation='external_service_employee_rel',
                                           string="Personal de rescate")

    @api.onchange('consumption', 'rescue_truck_id')
    def get_truck_performance(self):
        vehicle_id = self.rescue_truck_id.vehicle_id
        if self.consumption > 0 and self.rescue_truck_id:
            self.performance = (vehicle_id.performance / self.consumption) * 100
        if vehicle_id.performance <= 0 and self.rescue_truck_id:
            self.performance = 0
            return {
                'warning': {'title': "Advertencia",
                            'message': "El campo de rendimiento en el Camion tiene un valor de cero o no valido."},
            }

    def action_fsm_validate(self):
        """ Moves Task to next stage.
            If allow billable on task, timesheet product set on project and user has privileges :
            Create SO confirmed with time and material.
        """
        res = super(ProjectTask, self).action_fsm_validate()
        for task in self:
            if task.is_fsm:
                # region Condicionales
                validate_fields = {}
                msg = "Debe completar las siguientes secciones: \n"
                if not task.transport_name:
                    validate_fields.update({
                        'Nombre del transporte': False,
                    })
                if not task.driver_name:
                    validate_fields.update({
                        'Nombre del chofer': False,
                    })

                if not task.effective_date:
                    validate_fields.update({
                        'Fecha efectiva': False,
                    })
                if not task.phone:
                    validate_fields.update({
                        'Teléfono': False,
                    })
                if not task.rescue_location:
                    validate_fields.update({
                        'Lugar de rescate': False,
                    })

                if len(task.employee_worker_ids) < 1:
                    validate_fields.update({
                        'Personal de rescate': False,
                    })
                if not task.main_cause:
                    validate_fields.update({
                        'Causa rescate': False,
                    })
                if task.arrive_time == 0:
                    validate_fields.update({
                        'Hora de llegada': False,
                    })
                if task.leave_time == 0:
                    validate_fields.update({
                        'Hora de salida': False,
                    })
                if task.odometer_start == 0:
                    validate_fields.update({
                        'Odómetro inicial': False,
                    })
                if task.odometer_end == 0:
                    validate_fields.update({
                        'Odómetro final': False,
                    })
                if task.th_gen_set and task.hourmeter == 0:
                    validate_fields.update({
                        'Horómetro': False,
                    })

                if not task.container_type:
                    validate_fields.update({
                        'Tipo de contenedor': False,
                    })
                if not task.container_long or not task.chassis_long:
                    validate_fields.update({
                        'Longitud de las unidades': False,
                    })

                if not task.damage_type_ids and not task.other_damage:
                    validate_fields.update({
                        'Tipo averia': False,
                    })

                if not task.timesheet_ids:
                    validate_fields.update({
                        'Horas trabajadas': False,
                    })
                if task.container_type == 'cooled':
                    if not task.before_temp or not task.after_temp or not task.before_oxy or not task.after_oxy or not task.before_vent or not task.after_vent or not task.before_carb or not task.after_carb or not task.before_diox or not task.after_diox or not task.before_humid or not task.after_humid:
                        validate_fields.update({
                            'Configuración de la nevera': False,
                        })
                if not task.partner_name:
                    validate_fields.update({
                        'Nombre del cliente': False,
                    })
                if not task.partner_vat:
                    validate_fields.update({
                        'Cédula del cliente': False,
                    })

                # endregion

                for k, val in validate_fields.items():
                    if not val:
                        msg += f"\n**{k}**"
                if len(validate_fields.items()) > 0:
                    raise ValidationError(msg)

        for task in self.filtered(
                lambda task: task.allow_billable and (task.allow_timesheets or task.allow_material)):
            if task.is_fsm:
                if not task.sale_line_id and not task.timesheet_ids:  # Prevent creating a SO if there are no products and no timesheets
                    continue
                task._fsm_ensure_sale_order()
                if task.rescue_truck_id:
                    task.sudo().sale_order_id.write({
                        'warehouse_id': task.rescue_truck_id.id
                    })

        return res

    @api.onchange('user_id', 'extra_user1_id', 'extra_user2_id')
    def set_worker_ids(self):
        worker_ids = self.env['hr.employee']
        if self.user_id and self.user_id.employee:
            rel_employee = self.env['hr.employee'].browse([('user_id', '=', self.user_id)])
            worker_ids += rel_employee
        if self.extra_user1_id:
            worker_ids += self.extra_user1_id
        if self.extra_user2_id:
            worker_ids += self.extra_user2_id

        self.employee_worker_ids = [(6, 0, worker_ids.ids)]

    effective_date = fields.Date(string="Fecha efectiva")
    phone = fields.Char(string="Teléfono")
    arrive_time = fields.Float(string="Hora de llegada (lugar del rescate)")
    leave_time = fields.Float(string="Hora de salida (lugar del rescate)")
    km_travelled = fields.Float(string="Km recorridos")
    main_cause = fields.Selection([('bad_use', 'Mal uso'), ('wear', 'Deterioro')], string="Causa rescate")
    chassis_long = fields.Selection(selection=LONG_OPTIONS, string="Long. Chasis")
    th_gen_set = fields.Boolean(string="¿Hay Gen Set?")
    th_freeze = fields.Boolean(string="Nevera?")
    container_type = fields.Selection([('dry', 'Seco'), ('cooled', 'Refrigerado')], string="Tipo de contenedor")
    container_long = fields.Selection(selection=LONG_OPTIONS, string="Long. Contenedor")

    @api.onchange('chassis_long')
    def set_unit_chassis_long(self):
        self.container_long = self.chassis_long

    @api.onchange('container_long')
    def set_unit_container_long(self):
        self.chassis_long = self.container_long

    container = fields.Char(string="Contenedor nombre")
    product_container_id = fields.Many2one('product.product', string="Contenedor")
    container_lot_id = fields.Many2one('stock.production.lot', string="Número de contenedor")

    chassis = fields.Char(string="Chasis nombre")
    product_chassis_id = fields.Many2one('product.product', string="Chasis")
    chassis_lot_id = fields.Many2one('stock.production.lot', string="Número de Chasis")

    gen_set = fields.Char(string="Gen set nombre")
    product_gen_set_id = fields.Many2one('product.product', string="Gen Set")
    gen_set_lot_id = fields.Many2one('stock.production.lot', string="Número de Gen set")

    @api.onchange('container_lot_id', 'chassis_lot_id', 'gen_set_lot_id')
    def setup_units_serial_name(self):
        if self.container_lot_id:
            self.container = self.container_lot_id.name
        else:
            self.container = False

        if self.chassis_lot_id:
            self.chassis = self.chassis_lot_id.name
        else:
            self.chassis = False

        if self.gen_set_lot_id:
            self.gen_set = self.gen_set_lot_id.name
        else:
            self.gen_set = False

    @api.onchange('product_gen_set_id')
    def clear_gen_serial(self):
        self.gen_set_lot_id = False

    @api.onchange('product_container_id')
    def clear_container_serial(self):
        self.container_lot_id = False

    @api.onchange('product_chassis_id')
    def clear_chassis_serial(self):
        self.chassis_lot_id = False

    damage_type_ids = fields.Many2many(comodel_name='damage.option', relation='task_damage_option_rel',
                                       string="Tipo de averia")
    other_damage = fields.Char(string="Otros")
    value_damage_type = fields.Char(string="Valor tipos de averia", compute='compute_main_cause_value', store=True)

    @api.depends('stage_id', 'damage_type_ids', 'other_damage')
    def compute_main_cause_value(self):
        for rec in self:
            value = ''
            for elem in rec.damage_type_ids:
                value += f'{elem.name}, '
            if rec.other_damage:
                value += f'{rec.other_damage}'
            else:
                value = value[:len(value) - 2]
            rec.value_damage_type = value
            # dict_select = dict(rec._fields['main_cause'].selection)

    # Unidad de rescate
    odometer_start = fields.Float(string="Odómetro inicial")
    odometer_end = fields.Float(string="Odómetro final")

    @api.onchange('odometer_start', 'odometer_end')
    def set_travelled_distance(self):
        if self.odometer_end > self.odometer_start:
            self.km_travelled = self.odometer_end - self.odometer_start
        else:
            self.odometer_end = 0.0
            self.km_travelled = 0.0
            return {
                'warning': {'title': "Advertencia",
                            'message': "No olvide colocar el odometro final, este debe ser mayor al inicial."},
            }

    hourmeter = fields.Float(string="Horómetro")

    product_line_ids = fields.One2many(comodel_name='sale.order.line', related='sale_order_id.order_line')
    product_line_value = fields.Char(string="Materiales", compute='compute_product_line_values', store=True)
    diet_value = fields.Float(string="Dieta", compute='compute_product_line_values', store=True)
    toll_tax_value = fields.Float(string="Precio de Peaje", compute='compute_product_line_values', store=True)
    time_product_value = fields.Float(string="Costo por trabajo realizado", compute='compute_product_line_values',
                                      store=True)
    km_travelled_product_value = fields.Float(string="Costo por kilometros", compute='compute_product_line_values',
                                              store=True)
    fuel_product_value = fields.Float(string="Costo de combustible", compute='compute_product_line_values', store=True)
    fuel_product_qty = fields.Float(string="Cantidad de combustible", compute='compute_product_line_values', store=True)
    fuel_product_price = fields.Float(string="Precio del galón", compute='compute_product_line_values', store=True)
    product_amount_total = fields.Float(string="Precio de las piezas", compute='compute_product_line_values',
                                        store=True)
    rescue_amount_total = fields.Float(string="Total de rescate", compute='compute_product_line_values', store=True)

    @api.depends('stage_id', 'product_line_ids', 'product_line_ids.product_id')
    def compute_product_line_values(self):
        for rec in self:
            line_value = ''
            diet_value = 0.0
            toll_tax_value = 0.0
            time_product_value = 0.0
            product_amount_total = 0.0
            km_product_value = 0.0
            fuel_product_value = 0.0
            fuel_product_qty = 0.0
            fuel_product_price = 0.0
            for line in rec.product_line_ids:
                line_value += f'[{line.name}: {line.qty_delivered}]\n'
                if line.product_id == self.env.ref('equiport_custom.fuel_product'):
                    fuel_product_value = line.price_subtotal
                    fuel_product_qty = line.qty_delivered
                    fuel_product_price = line.price_unit
                elif line.product_id == self.env.ref('equiport_custom.km_travelled_product'):
                    km_product_value = line.price_unit
                elif line.product_id == self.env.ref('equiport_custom.diet_product'):
                    diet_value = line.price_subtotal
                elif line.product_id == self.env.ref('equiport_custom.toll_tax_product'):
                    toll_tax_value = line.price_subtotal
                elif line.product_id == self.env.ref('sale_timesheet.time_product'):
                    time_product_value = line.price_subtotal if (line.price_subtotal > 0) else (
                            line.qty_delivered * line.price_unit)
                elif line.product_id.type != 'service':
                    product_amount_total += line.price_subtotal if (line.price_subtotal > 0) else (
                            line.qty_delivered * line.price_unit)

            rec.diet_value = diet_value
            rec.toll_tax_value = toll_tax_value
            rec.time_product_value = time_product_value
            rec.km_travelled_product_value = km_product_value
            rec.fuel_product_value = fuel_product_value
            rec.fuel_product_qty = fuel_product_qty
            rec.fuel_product_price = fuel_product_price
            rec.product_line_value = line_value
            rec.product_amount_total = product_amount_total
            rec.rescue_amount_total = rec.sale_order_id.amount_total or 0.0

    rescue_notes = fields.Char(string="Observaciones")
    partner_sign = fields.Binary(string="Firma cliente")
    partner_name = fields.Char(string="Nombre cliente")
    partner_vat = fields.Char(string="Cédula cliente")
    employee_sign = fields.Binary(string="Firma empleado")

    @api.constrains('partner_vat')
    def partner_vat_length_constrain(self):
        for rec in self:
            if rec.partner_vat and len(rec.partner_vat) != 11:
                raise ValidationError("Verifique la longitud de la Cédula. Deben ser 11 digitos")

    # Reefer settings table
    before_temp = fields.Char(string="Temp. antes")
    before_humid = fields.Char(string="Humed. antes")
    before_diox = fields.Char(string="Diox. antes")
    before_vent = fields.Char(string="Vent. antes")
    before_carb = fields.Char(string="Carb. antes")
    before_oxy = fields.Char(string="Oxig. antes")
    after_temp = fields.Char(string="Temp. despues")
    after_humid = fields.Char(string="Humed. despues")
    after_diox = fields.Char(string="Diox. despues")
    after_vent = fields.Char(string="Vent. despues")
    after_carb = fields.Char(string="Carb. despues")
    after_oxy = fields.Char(string="Oxig. despues")


class DamageOption(models.Model):
    _name = 'damage.option'
    _description = 'Registro de tipos de averias'

    name = fields.Char(string="Nombre", required=1)
