# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

LONG_OPTIONS = [('20', '20'), ('40', '40'), ('45', '45')]


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    picking_ids = fields.One2many(comodel_name='stock.picking', inverse_name='repair_id', string="Conduces")
    delivery_count = fields.Integer(
        compute='_compute_picking_count', string="Número de conduces")

    opportunity_id = fields.Many2one(comodel_name='crm.lead', string="Oportunidad")

    is_readonly_user = fields.Boolean(compute='_compute_readonly_flag', store=False)
    x_css = fields.Html(
        string='CSS/JS',
        sanitize=False,
        compute='_compute_readonly_flag',
        store=False,
    )

    def _compute_readonly_flag(self):
        for rec in self:
            rec.x_css = False
            rec.is_readonly_user = False
            if self.env.user.has_group('equiport_custom.repair_account_user_readonly'):
                rec.is_readonly_user = True
                rec.x_css = '<style>.o_form_button_edit, .o_form_button_create, .oe_subtotal_footer {display: none !important;}</style>'
                rec.x_css += """<script>
                            var action = document.querySelector(".o_cp_action_menus")?.lastChild
                            if(action){
                                action.style.display='none'
                            }
                            </script>"""
            else:
                rec.is_readonly_user = False
                rec.x_css = False

    # region Modifying existing fields

    # endregion

    # region Flota
    vehicle_service_log_id = fields.Many2one(comodel_name='fleet.vehicle.log.services', string="Registro de servicio")
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', related='vehicle_service_log_id.vehicle_id',
                                 string="Unidad")
    is_fleet_origin = fields.Boolean(string="Originado en flota")
    product_fleet_name = fields.Char(related='product_id.display_name', string="Nombre producto flota")
    is_fuel_replenishment = fields.Boolean(string="Reposición de combustible", compute='compute_is_fuel_replenishment',
                                           store=True)

    order_type = fields.Selection([('maintenance_fleet', 'Mantenimiento Flota'),
                                   ('repair_fleet', 'Reparación Flota'),
                                   ('repair', 'Reparación')], string="Tipo de Servicio",
                                  compute="compute_category_order_type", store=True)

    @api.depends('is_fleet_origin', 'operations')
    def compute_is_fuel_replenishment(self):
        fuel_product = self.env.ref('equiport_custom.fuel_product')
        for rec in self:
            if fuel_product in rec.operations.mapped('product_id'):
                rec.is_fuel_replenishment = True
            else:
                rec.is_fuel_replenishment = False

    @api.depends('vehicle_service_log_id')
    def compute_category_order_type(self):
        for rec in self:
            if rec.vehicle_service_log_id:
                if rec.vehicle_service_log_id.category == 'maintenance':
                    rec.order_type = 'maintenance_fleet'
                elif rec.vehicle_service_log_id.category == 'repair':
                    rec.order_type = 'repair_fleet'
            else:
                rec.order_type = 'repair'

    # endregion

    # Gathering repair info
    inspection_date = fields.Date(string="Fecha inspección")
    no_unit = fields.Char(string="No. Contenedor")
    size = fields.Selection(selection=LONG_OPTIONS, string="Tamaño")
    material = fields.Selection(
        [('rf_steel', 'RF Acero'), ('rf_aluminum', 'RF aluminio'), ('f_steel', 'F Acero'), ('other', 'Otros')],
        string="Material")
    other_material = fields.Char(string="Otros")
    entry_date = fields.Date(string="Fecha entrada")
    exit_date = fields.Date(string="Fecha salida")
    entry_status = fields.Char(string="Estado de entrada")
    exit_status = fields.Char(string="Estado de salida")
    line_location = fields.Char(string="Linea")
    inspection_worker = fields.Many2one(comodel_name='hr.employee', string="Inspecionado por")
    inspection_location = fields.Char(string="Lugar de inspección")
    inspection_air = fields.Boolean(string="Inspección compartidor de aire (bandeja interior)")
    inspection_top = fields.Boolean(string="Inspección tapas interiores")
    inspection_screw = fields.Boolean(string="Inspección tornillos y remaches completos")
    inspection_patch = fields.Boolean(string="No se observan parches inusuales")

    repair_info_line_ids = fields.One2many(comodel_name='repair.panel.info.line', inverse_name='repair_order_id',
                                           string="Detalles de reparación")

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for rec in self:
            rec.delivery_count = len(rec.picking_ids)

    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        # Prepare the context.
        picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]
        action['context'] = dict(self._context, default_partner_id=self.partner_id.id,
                                 default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name,
                                 default_group_id=picking_id.group_id.id)
        return action

    def check_repair_product_availability(self):
        if self.product_id.is_vehicle:
            return
        if self.product_id.tracking in ['serial', 'lot']:
            free_qty = self.env['stock.quant']._get_available_quantity(product_id=self.product_id,
                                                                       location_id=self.location_id, lot_id=self.lot_id,
                                                                       strict=True)
        else:
            free_qty = self.env['stock.quant']._get_available_quantity(product_id=self.product_id,
                                                                       location_id=self.location_id, strict=True)
        if self.product_qty > free_qty:
            raise ValidationError(
                _(" El producto: %s Número: %s no esta disponible en la Ubicación: %s", self.product_id.name, self.lot_id.name, self.location_id.display_name))

    def check_lines_availability(self):

        error_message_lines = []
        for line in self.operations:
            if line.product_id.tracking in ['serial', 'lot']:
                free_qty = self.env['stock.quant']._get_available_quantity(product_id=line.product_id,
                                                                           location_id=line.location_id,
                                                                           lot_id=line.lot_id,
                                                                           strict=True)
            else:
                free_qty = self.env['stock.quant']._get_available_quantity(product_id=line.product_id,
                                                                           location_id=line.location_id, strict=True)

            if line.product_uom_qty > free_qty:
                if _(" - Producto: %s", line.product_id.name) not in error_message_lines:
                    error_message_lines.append(
                        _(" - Producto: %s", line.product_id.name))

        if error_message_lines:
            raise ValidationError(
                _('No tiene cantidades disponibles.\nLos siguientes no estan disponibles:\n') + '\n'.join(
                    error_message_lines))

    @api.model
    def create(self, vals):
        res = super(RepairOrder, self).create(vals)

        if res.product_id.unit_type and res.lot_id:
            res.lot_id.rent_state = 'to_check'
        return res

    def action_repair_cancel(self):
        res = super(RepairOrder, self).action_repair_cancel()
        if self.location_id == self.company_id.rental_loc_id:
            self.lot_id.rent_state = 'rented'
        else:
            self.lot_id.rent_state = 'available'
        return res

    def action_validate(self):
        self = self.with_user(self.env.ref('base.user_root'))
        self.check_repair_product_availability()
        if self.product_id.unit_type and self.lot_id:
            self.lot_id.rent_state = 'to_repair'

        return super(RepairOrder, self).action_validate()

    def action_repair_end(self):
        """ Writes repair order state to 'To be invoiced' if invoice method is
        After repair else state is set to 'Ready'.
        @return: True
        """
        self = self.with_user(self.env.ref('base.user_root'))
        for repair in self:
            work_time_product_id = self.env.ref('sale_timesheet.time_product_product_template')
            if work_time_product_id not in repair.fees_lines.mapped('product_id.product_tmpl_id'):
                raise ValidationError("Se deben registar las horas trabajadas en el área de operaciones")

        if self.product_id.unit_type and self.lot_id:
            if self.location_id == self.company_id.rental_loc_id:
                self.lot_id.rent_state = 'rented'
            else:
                self.lot_id.rent_state = 'available'

        context = dict(self.env.context)
        context.pop('default_lot_id', None)

        return super(RepairOrder, self.with_context(context)).action_repair_end()

    def action_repair_done(self):
        """ Creates stock move for operation and stock move for final product of repair order.
        @return: Move ids of final products

        """
        self = self.with_user(self.env.ref('base.user_root'))
        self.check_lines_availability()
        context = dict(self.env.context)
        context.pop('default_lot_id', None)
        res = super(RepairOrder, self.with_context(context)).action_repair_done()
        for repair in self:
            picking = None
            if len(repair.picking_ids) == 0:
                picking = self.env['stock.picking'].create({
                    'name': f'Orden de reparación: {repair.name}',
                    'partner_id': repair.partner_id.id,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'location_id': repair.location_id.id,
                    'location_dest_id': self.env['stock.location'].search(
                        [('usage', '=', 'production'), ('company_id', '=', repair.company_id.id)], limit=1).id,
                    'move_lines': [],
                    'material_picking': True,
                    'repair_id': repair.id,
                    'origin': repair.name,
                })
            else:
                repair.picking_ids[0].write({
                    'partner_id': repair.partner_id.id,
                    'location_id': repair.location_id.id,
                    'location_dest_id': self.env['stock.location'].search(
                        [('usage', '=', 'production'), ('company_id', '=', repair.company_id.id)], limit=1).id,
                    'material_picking': True,
                })
                picking = repair.picking_ids[0]

            for line in repair.operations.filtered(lambda l: l.product_id.type in ['product', 'consu']):
                move_line_ids = self.env['stock.move.line'].search(
                    [('product_id', '=', line.product_id.id), ('move_id.repair_id', '=', line.repair_id.id)])
                if move_line_ids:
                    move_line_id = move_line_ids[0]
                    move_line_id.picking_id = picking.id
                    picking.move_lines += move_line_id.move_id
            repair.picking_ids += picking
            picking.state = 'done'
        return res


class RepairPanelInfoLine(models.Model):
    _name = 'repair.panel.info.line'
    _description = 'Lineas de detalle para el levantamiento fisico en las reparaciones'

    name = fields.Char(string="Nombre", compute='_compute_rec_name')
    damage_type = fields.Char(string="Tipo de daño")
    affected_panel_qty = fields.Float(string="Cantidad de paneles afectados")
    repair_panel_description = fields.Text(string="Localidad")
    panel_location = fields.Char(string="Ubicación de paneles afectados")
    height = fields.Char(string="Altura")
    long = fields.Char(string="Longitud")
    repair_order_id = fields.Many2one('repair.order', string="Orden de reparación")

    def _compute_rec_name(self):
        for rec in self:
            rec.name = f"{rec.repair_order_id.name} / {rec.repair_panel_description}"
