# -*- coding: utf-8 -*-
from datetime import timedelta, datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    # region Campos modificados

    model_id = fields.Many2one('fleet.vehicle.model', 'Model',
                               tracking=True, required=False, help='Model of the vehicle')

    # endregion

    # region Nuevos campos para unidades

    custom_type = fields.Char(string="Tipo")
    vehicle_token = fields.Char(string="Ficha")

    product_unit_id = fields.Many2one(comodel_name='product.product', string="Unidad",
                                      domain="[('unit_type', '=', unit_type), ('unit_model_id', '=', unit_model_id)]")
    unit_type = fields.Selection(
        [('vehicle', 'Vehiculo'), ('container', 'Contenedor'), ('gen_set', 'Gen Set'), ('chassis', 'Chasis')],
        tracking=True, string="Tipo de unidad", default='vehicle')
    unit_brand_id = fields.Many2one('unit.model.brand', related="unit_model_id.brand_id", store=True, readonly=False,
                                    string="Marca de unidad")
    unit_model_id = fields.Many2one(comodel_name='unit.model', tracking=True,
                                    string="Modelo de unidad", domain="[('unit_type', '=', unit_type)]")

    container_type = fields.Selection(related='product_unit_id.container_type', string="Tipo de contenedor")

    unit_size = fields.Selection(related='product_unit_id.unit_size', string="Tamaño")

    unit_lot_id = fields.Many2one(
        'stock.production.lot', 'Serial', tracking=True,
        domain="[('product_id','=', product_unit_id), ('company_id', '=', company_id)]", check_company=True,
        help="Número de parte / Serie de esta unidad")


    unit_image_128 = fields.Image(related='unit_model_id.image_128', string="Logo unidad", readonly=True)


    hourmeter_count = fields.Integer(compute="_compute_count_all", string='Horómetro')
    hourmeter = fields.Float(compute='_get_hourmeter', inverse='_set_hourmeter', string='Último horómetro',
                             help='Medida del horómetro al momento de este registro')
    hourmeter_unit = fields.Selection([
        ('hours', 'Hr')
    ], 'Medida horómetro', default='hours', help='Medida de horometro ', required=True)

    odometer_km_cost = fields.Float(compute='compute_use_cost', string="Costo por kilometro", store=True)
    hourmeter_hr_cost = fields.Float(compute='compute_use_cost', string="Costo por hora", store=True)

    # endregion

    # region Nuevas funciones
    @api.depends('odometer', 'hourmeter')
    def compute_use_cost(self):
        FleetVehicleHourometer = self.env['fleet.unit.hourmeter']
        FleetVehicleOdometer = self.env['fleet.vehicle.odometer']
        fuel_company_services = self.env.company.fuel_services_fleet
        if not fuel_company_services:
            for rec in self:
                rec.hourmeter_hr_cost = 0
                rec.odometer_km_cost = 0
        for record in self:
            cost = 0
            services = record.log_services.filtered(lambda s: s.service_type_id.id in fuel_company_services.ids)
            if services:
                cost = sum(services.mapped('amount'))
            if record.unit_type == 'gen_set' and cost > 0:
                first_hourmeter = FleetVehicleHourometer.search([('vehicle_id', '=', record.id)], limit=1,
                                                                order='value asc')
                fuel_hourmeter = record.hourmeter - first_hourmeter.value
                record.hourmeter_hr_cost = (fuel_hourmeter / cost)
            else:
                record.hourmeter_hr_cost = 0

            if record.unit_type == 'vehicle' and cost > 0:
                first_odometer = FleetVehicleOdometer.search([('vehicle_id', '=', record.id)], limit=1,
                                                             order='value asc')
                first_odometer = record.odometer - first_odometer.value
                record.odometer_km_cost = (first_odometer / cost)
            else:
                record.odometer_km_cost = 0

    @api.onchange('unit_type')
    def clean_related_fields_value(self):
        self.model_id = False
        self.license_plate = False
        self.unit_model_id = False
        self.product_unit_id = False
        self.unit_lot_id = False
        if self.unit_type != 'vehicle':
            self.model_year = self.product_unit_id.unit_year

    def _get_hourmeter(self):
        FleetVehicalHourometer = self.env['fleet.unit.hourmeter']
        for record in self:
            vehicle_hourmeter = FleetVehicalHourometer.search([('vehicle_id', '=', record.id)], limit=1,
                                                              order='value desc')
            if vehicle_hourmeter:
                record.hourmeter = vehicle_hourmeter.value
            else:
                record.hourmeter = 0

    def _set_hourmeter(self):
        for record in self:
            if record.hourmeter:
                date = fields.Date.context_today(record)
                data = {'value': record.hourmeter, 'date': date, 'vehicle_id': record.id}
                self.env['fleet.unit.hourmeter'].create(data)

    # endregion

    # region Funciones Heredadas
    @api.depends('model_id.brand_id.name', 'model_id.name', 'license_plate', 'product_unit_id.name', 'unit_type',
                 'unit_model_id.name', 'unit_model_id.brand_id.name', 'unit_lot_id.name')
    def _compute_vehicle_name(self):
        for record in self:
            if record.unit_type == 'vehicle':
                record.name = (record.model_id.brand_id.name or '') + '/' + (record.model_id.name or '') + '/' + (
                        record.license_plate or _('No Plate'))
            else:
                record.name = (record.unit_model_id.brand_id.name or '') + '/' + (
                        record.unit_model_id.name or '') + '/' + (record.product_unit_id.name or '') + '/' + (
                                      record.unit_lot_id.name or 'Sin Serial')

    def _compute_count_all(self):
        res = super(FleetVehicle, self)._compute_count_all()

        Hourmeter = self.env['fleet.unit.hourmeter']
        for record in self:
            record.hourmeter_count = Hourmeter.search_count([('vehicle_id', '=', record.id)])

        return res

    def return_action_to_open(self):
        self.ensure_one()
        xml_origin = self.env.context.get('xml_origin')
        if xml_origin and xml_origin == 'hourmeter':
            xml_id = self.env.context.get('xml_id')
            res = self.env['ir.actions.act_window']._for_xml_id('equiport_custom.%s' % xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return super(FleetVehicle, self).return_action_to_open()

    # endregion


class FleetUnitHourmeter(models.Model):
    _name = 'fleet.unit.hourmeter'
    _description = 'Historial de horometro para unidades'
    _order = 'date desc'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Valor de horómetro', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Unidad', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Medida", readonly=True)

    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        for record in self:
            name = record.vehicle_id.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.unit = self.vehicle_id.hourmeter_unit


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    repair_id = fields.Many2one(comodel_name='repair.order', string="Orden")
    location_id = fields.Many2one('stock.location', 'Ubicación de origen', domain="[('usage', '=', 'internal')]")
    unit_type = fields.Selection(related='vehicle_id.unit_type')
    category = fields.Selection(related='service_type_id.category')
    hourmeter = fields.Float(compute='_get_hourmeter', inverse='_set_hourmeter', string='Último horómetro',
                             help='Medida del horómetro al momento de este registro')
    hourmeter_unit = fields.Selection([
        ('hours', 'Hr')
    ], 'Medida horómetro', default='hours', help='Medida de horometro ', required=True)

    # region Alerts
    km_waited = fields.Float(string="Kilometros próximo cambio", compute='_next_odometer_service', default=0.0,
                             store=True)
    date_waited = fields.Date(string="Fecha próximo cambio", compute='_next_date_service', store=True)
    hr_waited = fields.Float(string="Horas próximo cambio", compute='_next_hourmeter_service', store=True)
    check_done = fields.Boolean(string="Servicio realizado", compute='compute_done_service', store=True)
    check_notify = fields.Boolean(string="Notificaciones configuradas", compute='compute_notify_service', store=True)

    @api.depends('service_type_id.hr_service', 'service_type_id.km_service', 'service_type_id.date_service')
    def compute_notify_service(self):
        for rec in self:
            if (
                    rec.service_type_id.hr_service > 0 or rec.service_type_id.km_service > 0 or rec.service_type_id.date_service > 0) and (
                    rec.state != 'cancelled'):
                rec.check_notify = True
            else:
                rec.check_notify = False

    @api.depends('state', 'repair_id.state')
    def compute_done_service(self):
        for rec in self:
            if rec.category in ['repair', 'maintenance'] and rec.repair_id:
                rec.check_done = rec.repair_id.state == 'done'
                if rec.repair_id.state == 'done':
                    rec.state = 'done'
            elif rec.category not in ['repair', 'maintenance']:
                rec.check_done = rec.state == 'done'
            if rec.state == 'cancelled':
                rec.repair_id.state = 'cancel'

    @api.constrains('odometer', 'hourmeter')
    def constraint_use_fields(self):
        for rec in self:
            if rec.unit_type == 'vehicle':
                if rec.odometer > 0:
                    if rec.odometer < rec.vehicle_id.odometer:
                        raise ValidationError("El valor del odómetro debe ser mayor de %.2f" % self.vehicle_id.odometer)
            elif rec.unit_type == 'gen_set':
                if rec.hourmeter > 0:
                    if rec.hourmeter < rec.vehicle_id.hourmeter:
                        raise ValidationError(
                            "El valor del Horómetro debe ser mayor de %.2f" % self.vehicle_id.hourmeter)

    @api.onchange('odometer')
    def check_odometer(self):
        if self.odometer > 0:
            if self.odometer < self.vehicle_id.odometer:
                raise ValidationError("El valor del odómetro debe ser mayor de %.2f" % self.vehicle_id.odometer)

    @api.onchange('hourmeter')
    def check_hourmeter(self):
        if self.hourmeter > 0:
            if self.hourmeter < self.vehicle_id.hourmeter:
                raise ValidationError("El valor del Horómetro debe ser mayor de %.2f" % self.vehicle_id.hourmeter)

    @api.depends('odometer', 'service_type_id.km_service')
    def _next_odometer_service(self):
        for rec in self:
            km_service = rec.service_type_id.km_service
            rec.km_waited = rec.odometer + km_service

    @api.depends('hourmeter', 'service_type_id.hr_service')
    def _next_hourmeter_service(self):
        for rec in self:
            hr_service = rec.service_type_id.hr_service
            rec.hr_waited = rec.hourmeter + hr_service

    @api.depends('date', 'service_type_id.date_service')
    def _next_date_service(self):
        for rec in self:
            date_service = rec.service_type_id.date_service
            rec.date_waited = rec.date + timedelta(days=date_service)

    # endregion

    def _get_hourmeter(self):
        FleetVehicalHourometer = self.env['fleet.unit.hourmeter']
        for record in self:
            vehicle_hourmeter = FleetVehicalHourometer.search([('vehicle_id', '=', record.vehicle_id.id)], limit=1,
                                                              order='value desc')
            if vehicle_hourmeter:
                record.hourmeter = vehicle_hourmeter.value
            else:
                record.hourmeter = 0

    def _set_hourmeter(self):
        for record in self:
            if record.hourmeter:
                date = fields.Date.context_today(record)
                data = {'value': record.hourmeter, 'date': date, 'vehicle_id': record.vehicle_id.id}
                self.env['fleet.unit.hourmeter'].create(data)

    def action_repair_quotations_new(self):
        RepairOrder = self.env['repair.order']
        repair_lines = []
        fees_lines = []
        if self.repair_id:
            raise ValidationError('Ya posee una orden atada a este documento.')
        if self.service_type_id.category in ['repair', 'maintenance']:
            for rl in self.service_type_id.material_ids:
                repair_lines.append((0, 0, {
                    'product_id': rl.product_id.id,
                    'name': rl.name,
                    'product_uom_qty': rl.product_uom_qty,
                    'product_uom': rl.product_uom.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.env['stock.location'].search(
                        [('usage', '=', 'production'), ('company_id', '=', self.company_id.id)], limit=1).id,
                    'price_unit': rl.product_id.list_price,
                }))
            for fl in self.service_type_id.operation_ids:
                fees_lines.append((0, 0, {
                    'product_id': fl.product_id.id,
                    'name': fl.name,
                    'product_uom_qty': fl.product_uom_qty,
                    'product_uom': fl.product_uom.id,
                    'price_unit': fl.product_id.list_price,
                }))
        if self.vehicle_id.unit_type == 'vehicle':

            product = self.vehicle_id.product_unit_id or self.sudo().env['product.product'].search(
                [('vehicle_id', '=', self.vehicle_id.id)])
            if not product:
                self.vehicle_id.product_unit_id = self.sudo().env['product.product'].create({
                    'name': self.vehicle_id.name,
                    'vehicle_id': self.vehicle_id.id,
                    'is_vehicle': True,
                    'sale_ok': False,
                    'purchase_ok': False,
                    'type': 'product',
                    'list_price': 0,
                    'stock_quant_ids': [(0, 0, {
                        'inventory_quantity': 1,
                        'location_id': self.location_id.id
                    })],
                })

        self.repair_id = RepairOrder.create({
            "vehicle_service_log_id": self.id,
            "invoice_method": 'none',
            "location_id": self.location_id.id,
            "product_id": self.sudo().vehicle_id.product_unit_id.id,
            "product_qty": 1,
            "product_uom": self.sudo().vehicle_id.product_unit_id.uom_id.id,
            "user_id": self.env.user.id,
            "operations": repair_lines,
            "fees_lines": fees_lines,
            "is_fleet_origin": True,
            "internal_notes": self.service_type_id.name + ((" / " + self.description) or ''),
            "company_id": self.company_id.id or self.env.company.id,
        })
        self.amount = self.repair_id.amount_total
        return self.action_view_repair_quotation()

    def action_view_repair_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("repair.action_repair_order_tree")

        action.update({
            'views': [(self.env.ref("repair.view_repair_order_form").id, "form")],
            'res_id': self.repair_id.id,
        })
        return action

    @api.model
    def create(self, vals_list):
        res = super(FleetVehicleLogServices, self).create(vals_list)

        if res.category in ['repair', 'maintenance'] and res.repair_id:
            res.amount = res.repair_id.amount_total
        return res

    def write(self, values):
        if self.category in ['repair', 'maintenance'] and self.repair_id:
            values['amount'] = self.repair_id.amount_total
        res = super(FleetVehicleLogServices, self).write(values)

        return res

    # region Service Alerts

    def get_users_to_alert(self):
        partners = self.env['res.partner']
        for user in self.company_id.user_fleet_notify:
            if user.partner_id.email:
                partners += user.partner_id
            else:
                raise ValidationError(f"El usuario {user.name} no cuenta con un correo electrónico en su contacto.")
        if partners:
            return str(partners.ids).replace('[', '').replace(']', '')
        else:
            raise ValidationError("No se encontró personal asignado para recibir notificaciones de flota.")

    def fleet_alerts_send_mail(self):
        template_id = self.env.ref('equiport_custom.email_template_fleet_alerts')
        vehicleModel = self.env['fleet.vehicle']
        serviceTypeModel = self.env['fleet.service.type']
        current_date = datetime.now().date()
        local_context = self.env.context.copy()
        date_alert = False
        km_alert = False
        hr_alert = False
        category_dict = {
            'repair': 'reparación',
            'maintenance': 'mantenimiento',
            'contract': 'contracto',
            'service': 'servicio',
        }
        service_ids = serviceTypeModel.search([('category', '!=', 'contract')])
        vehicle_ids = vehicleModel.search([])
        for service in service_ids:
            for vehicle in vehicle_ids:
                last_service_log = self.search([('vehicle_id', '=', vehicle.id), ('state', '!=', 'cancelled'), ('service_type_id', '=', service.id)],
                                               limit=1, order='create_date desc')
                if not last_service_log:
                    continue

                if last_service_log.check_notify:
                    msg = ""
                    if ((current_date >= last_service_log.date_waited) or (vehicle.odometer > last_service_log.km_waited) or (
                                    (vehicle.hourmeter > last_service_log.hr_waited) and (last_service_log.unit_type == 'gen_set'))):

                                if current_date >= last_service_log.date_waited:
                                    msg += "\n Se ha superado la fecha esperada."
                                    date_alert = True
                                if vehicle.odometer > last_service_log.km_waited:
                                    msg += "\n Se han superado los kilometros esperados."
                                    km_alert = True
                                if (vehicle.hourmeter > last_service_log.hr_waited) and (last_service_log.unit_type == 'gen_set'):
                                    msg += "\n Se han superado las horas esperadas."
                                    hr_alert = True

                                # Alerta en odoo
                                last_service_log.activity_schedule(
                                    'fleet.mail_act_fleet_service_to_renew', last_service_log.date_waited,
                                    summary=msg,
                                    user_id=last_service_log.create_uid.id)

                                new_context = {
                                    'date_alert': date_alert,
                                    'km_alert': km_alert,
                                    'hr_alert': hr_alert,
                                    'service_type': category_dict[last_service_log.category]
                                }
                                local_context.update(new_context)
                                # Correo electronico
                                template_id.with_context(local_context).send_mail(last_service_log.id, force_send=True,
                                                                                  notif_layout="mail.mail_notification_light")

    # endregion


class FleetServiceType(models.Model):
    _inherit = 'fleet.service.type'

    category = fields.Selection(selection_add=[
        ('repair', 'Reparación'),
        ('maintenance', 'Mantenimiento'),
    ], ondelete={'repair': 'cascade',
                 'maintenance': 'cascade'})

    material_ids = fields.One2many(comodel_name='fleet.service.repair.line', inverse_name='service_type_id',
                                   string="Piezas")
    operation_ids = fields.One2many(comodel_name='fleet.service.repair.fee', inverse_name='service_type_id',
                                    string="Operaciones")

    km_service = fields.Float(string="Kilometros para próximo servicio")
    hr_service = fields.Float(string="Horas para próximo servicio")
    date_service = fields.Integer(string="Dias para próximo servicio")

    @api.constrains('date_service', 'km_service', 'hr_service')
    def check_no_negative_values(self):
        for rec in self:
            if rec.date_service < 0 or rec.km_service < 0 or rec.hr_service < 0:
                raise ValidationError(" Los campos Kilometros para próximo servicio,"
                                      " Horas para próximo servicio y"
                                      " Dias para próximo servicio no pueden contener valores menores a cero(0).")


class FleetServiceRepairLine(models.Model):
    _name = 'fleet.service.repair.line'
    _description = 'Lineas de reparacion tipo de servicio (Partes)'

    name = fields.Text('Descripción', required=True)
    service_type_id = fields.Many2one(
        'fleet.service.type', 'Tipo de servicio de referencia', required=True,
        index=True, ondelete='cascade', check_company=True)

    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    product_id = fields.Many2one(
        'product.product', 'Producto', required=True, check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    product_uom_qty = fields.Float(
        'Cantidad', default=1.0,
        digits='Unidad de medida del producto', required=True)

    product_uom = fields.Many2one(
        'uom.uom', 'Unidad de medida', required=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    @api.onchange('service_type_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        if not self.product_id:
            return

        self = self.with_company(self.company_id)

        self.name = self.product_id.display_name
        self.product_uom = self.product_id.uom_id.id
        if self.product_id.description_sale:
            self.name += '\n' + self.product_id.description_sale

    @api.onchange('product_uom')
    def onchange_product_uom(self):
        res = {}
        if not self.product_id or not self.product_uom:
            return res
        if self.product_uom.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {'title': _('Warning'), 'message': _(
                'The product unit of measure you chose has a different category than the product unit of measure.')}
            self.product_uom = self.product_id.uom_id.id
        return res


class FleetServiceRepairFee(models.Model):
    _name = 'fleet.service.repair.fee'
    _description = 'Lineas de reparacion tipo de servicio (Servicios)'

    name = fields.Text('Descripción', required=True)
    service_type_id = fields.Many2one(
        'fleet.service.type', 'Tipo de servicio de referencia', required=True,
        index=True, ondelete='cascade', check_company=True)

    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    product_id = fields.Many2one(
        'product.product', 'Producto', required=True, check_company=True,
        domain="[('type', 'in', ['service']), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    product_uom_qty = fields.Float(
        'Cantidad', default=1.0,
        digits='Unidad de medida del producto', required=True)

    product_uom = fields.Many2one(
        'uom.uom', 'Unidad de medida', required=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    @api.onchange('service_type_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        if not self.product_id:
            return

        self = self.with_company(self.company_id)

        self.name = self.product_id.display_name
        self.product_uom = self.product_id.uom_id.id
        if self.product_id.description_sale:
            self.name += '\n' + self.product_id.description_sale

    @api.onchange('product_uom')
    def onchange_product_uom(self):
        res = {}
        if not self.product_id or not self.product_uom:
            return res
        if self.product_uom.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {'title': _('Warning'), 'message': _(
                'The product unit of measure you chose has a different category than the product unit of measure.')}
            self.product_uom = self.product_id.uom_id.id
        return res
