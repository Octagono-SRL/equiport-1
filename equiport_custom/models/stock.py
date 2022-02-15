# -*- coding: utf-8 -*-
import base64
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

AVAILABLE_PRIORITIES = [
    ('0', 'Baja'),
    ('1', 'Media'),
    ('2', 'Alta'),
    ('3', 'Muy alta'),
]


class StockOrderPoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    order_use = fields.Char(string="Uso")
    priority = fields.Selection(
        AVAILABLE_PRIORITIES, string='Prioridad', index=True,
        default=AVAILABLE_PRIORITIES[0][0])


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _run_buy(self, procurements):
        for procurement, rule in procurements:
            procurement.values.update({
                'order_use': procurement.values['orderpoint_id'].order_use or '',
                'priority': procurement.values['orderpoint_id'].priority
            })

        res = super(StockRule, self)._run_buy(procurements)

        return res

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values,
                               group_id):
        res = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name,
                                                            origin, values, group_id)

        line_id = self.env['sale.order.line'].search([('id', '=', res['sale_line_id'])], limit=1)

        if line_id:
            res.update(
                storage_rate=line_id.storage_rate,
            )
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transport_partner_id = fields.Many2one(comodel_name='res.partner', domain=[('company_type', '=', 'company')], string="Compañia transportista")
    partner_driver = fields.Char(string="Conductor")
    vat_driver = fields.Char(string="Cédula del conductor")
    card_driver = fields.Char(string="Carnet del conductor")
    license_card_driver = fields.Char(string="Licencia del conductor")
    partner_truck = fields.Char(string="Placa Camión")
    access_granted = fields.Boolean(string="Acceso permitido", tracking=True)
    access_requested = fields.Boolean(string="Acceso Solicitado", tracking=True)

    is_rental = fields.Boolean(string="Proviene de una orden de alquiler", default=False)
    is_gate_service = fields.Boolean(string="Proviene de una orden de servicio gate")
    is_fsm = fields.Boolean(related='sale_id.is_fsm', string="Proviene de un Rescate")

    repair_id = fields.Many2one('repair.order', string="Orden de reparación")
    material_picking = fields.Boolean(string="Conduce de materiales")
    material_not_allow_save = fields.Boolean(string="Conduce de materiales Permitir guardar")

    @api.onchange('material_picking', 'move_ids_without_package', 'move_lines')
    def check_not_unit_in_material_picking(self):
        if self.material_picking:
            message_err = []
            for ml in self.move_line_ids:
                if ml.product_id.unit_type:
                    message_err.append(" - Producto: %s" % ml.product_id.name)
            for ml in self.move_ids_without_package:
                if ml.product_id.unit_type:
                    message_err.append(" - Producto: %s" % ml.product_id.name)
            for ml in self.move_line_ids_without_package:
                if ml.product_id.unit_type:
                    message_err.append(" - Producto: %s" % ml.product_id.name)
            if len(message_err) > 0:
                self.material_not_allow_save = True
                return {
                    'warning': {'title': "Advertencia",
                                'message': 'Los siguientes no son materiales:\n' + '\n'.join(
                                    message_err)},
                }
            else:
                self.material_not_allow_save = False

    @api.constrains('material_picking')
    def constrains_not_unit_in_material_picking(self):
        for rec in self:
            if rec.material_picking and rec.material_not_allow_save:
                raise ValidationError('Retire los productos que no sean materiales o modifique la operación')

    # @api.onchange('picking_type_code')
    # def set_material_picking_false(self):
    #     if self.picking_type_code != 'internal':
    #         self.material_picking = False

    @api.onchange('is_gate_service', 'name', 'partner_id')
    def set_domain_gate_picking_type(self):
        if self.is_gate_service:
            return {
                'domain': {
                    'picking_type_id': [('is_gate_operation', '=', True)]
                }
            }

    @api.constrains('vat_driver')
    def nif_length_constrain(self):
        if (self.is_rental and self.vat_driver and len(
                self.vat_driver) != 11) or (self.is_rental and self.vat_driver and not self.vat_driver.isnumeric()):
            raise ValidationError("Verifique la longitud de la Cédula. Deben ser 11 digitos")

    def button_validate(self):
        sale_id = self.sale_id
        fsm_invoice_available = True
        for task_id in sale_id.tasks_ids:
            if task_id.is_fsm and sale_id.tasks_count <= 1 and task_id.main_cause == 'wear':
                fsm_invoice_available = False

        if self.picking_type_code == 'outgoing':
            for ml in self.move_line_ids:
                if sale_id:
                    sale_order_line_id = sale_id.order_line.filtered(lambda sl: sl.product_id == ml.product_id)
                    for sol in sale_order_line_id:
                        if ml.qty_done > sol.product_uom_qty:
                            raise ValidationError("No puede exceder la cantidad especificada en la orden")

            for ml in self.move_line_ids_without_package:
                if sale_id:
                    sale_order_line_id = sale_id.order_line.filtered(lambda sl: sl.product_id == ml.product_id)
                    for sol in sale_order_line_id:
                        if ml.qty_done > sol.product_uom_qty:
                            raise ValidationError("No puede exceder la cantidad especificada en la orden")

        elif self.picking_type_code == 'internal':

            error_message_lines = []
            for ml in self.move_line_ids:
                free_qty = sum(ml.product_id.stock_quant_ids.filtered(
                    lambda sq: sq.location_id == self.location_id and sq.lot_id == ml.lot_id).mapped(
                    'available_quantity'))
                if ml.qty_done > free_qty and ml.qty_done != ml.product_uom_qty:
                    if _(" - Producto: %s", ml.product_id.name) not in error_message_lines:
                        error_message_lines.append(
                            _(" - Producto: %s", ml.product_id.name))

            for ml in self.move_line_ids_without_package:
                free_qty = sum(ml.product_id.stock_quant_ids.filtered(
                    lambda sq: sq.location_id == self.location_id and sq.lot_id == ml.lot_id).mapped(
                    'available_quantity'))
                if ml.qty_done > free_qty and ml.qty_done != ml.product_uom_qty:
                    if _(" - Producto: %s", ml.product_id.name) not in error_message_lines:
                        error_message_lines.append(
                            _(" - Producto: %s", ml.product_id.name))

            for ml in self.move_line_nosuggest_ids:
                free_qty = sum(ml.product_id.stock_quant_ids.filtered(
                    lambda sq: sq.location_id == self.location_id and sq.lot_id == ml.lot_id).mapped(
                    'available_quantity'))
                if ml.qty_done > free_qty and ml.qty_done != ml.product_uom_qty:
                    if _(" - Producto: %s", ml.product_id.name) not in error_message_lines:
                        error_message_lines.append(
                            _(" - Producto: %s", ml.product_id.name))

            if error_message_lines:
                raise ValidationError(
                    _('No tiene cantidades disponibles.\nLos siguientes no estan disponibles:\n') + '\n'.join(
                        error_message_lines))

        if not self.sale_id.partner_id.allowed_credit:
            if fsm_invoice_available and not sale_id.is_fsm:
                if self.picking_type_code == 'outgoing' and sale_id and sale_id.invoice_ids:
                    for inv in sale_id.invoice_ids.filtered(lambda i: i.state == 'posted'):
                        if inv.payment_state not in ['in_payment', 'paid']:
                            raise ValidationError(f"Posee facturas sin pago, no puede validar este despacho. "
                                                  f"Documento de referencia **{inv.name}**.")
                elif self.picking_type_code == 'outgoing' and sale_id.state == 'sale' and not sale_id.invoice_ids:
                    raise ValidationError(f"Se debe facturar y pagar la orden, no puede validar este despacho. ")

        # region Gate Service
        if self.is_gate_service:
            # if self.picking_type_code == 'incoming':
                # for line in self.move_line_nosuggest_ids:
                #     if line.in_booking and line.in_boat and line.in_stamp and line.in_navy_line:
                #         continue
                #     else:
                #         raise ValidationError("Debe colocar lo siguientes datos de la unidad:\n"
                #                               "\n"
                #                               "* Número de reserva\n"
                #                               "* Sello\n"
                #                               "* Barco\n"
                #                               "* Linea naviera\n")
            if self.picking_type_code == 'outgoing':
                for line in self.move_line_nosuggest_ids:
                    if line.out_booking and line.out_boat and line.out_stamp and line.out_navy_line:
                        continue
                    else:
                        raise ValidationError("Debe colocar lo siguientes datos de la unidad:\n"
                                              "\n"
                                              "* Número de reserva\n"
                                              "* Sello\n"
                                              "* Barco\n"
                                              "* Linea naviera\n")

            if len(sale_id.picking_ids) > 1 and sale_id.is_gate_service:
                in_picking_ids = self.env['stock.picking']
                out_picking_ids = self.env['stock.picking']
                for picking in sale_id.picking_ids:
                    if picking.picking_type_code == 'outgoing':
                        out_picking_ids += picking
                    elif picking.picking_type_code == 'incoming':
                        in_picking_ids += picking

                if not any(in_p.state == 'done' for in_p in in_picking_ids) and self.picking_type_code == 'outgoing':
                    raise ValidationError(
                        "No se puede validar. Se debe validar la recepcion de las unidades del documento de origen.")
        # endregion
        res = super(StockPicking, self).button_validate()

        if self.is_gate_service:
            if self.picking_type_code == 'incoming':
                for line in self.move_line_nosuggest_ids:
                    line.lot_id.in_booking = line.in_booking
                    line.lot_id.in_stamp = line.in_stamp
                    line.lot_id.in_boat = line.in_boat
                    line.lot_id.in_navy_line = line.in_navy_line
                    line.lot_id.owner_partner_id = self.partner_id
                    line.lot_id.gate_in_date = datetime.datetime.now()
                    line.lot_id.storage_rate = line.move_id.storage_rate

            elif self.picking_type_code == 'outgoing':
                for line in self.move_line_nosuggest_ids:
                    line.lot_id.out_booking = line.out_booking
                    line.lot_id.out_stamp = line.out_stamp
                    line.lot_id.out_boat = line.out_boat
                    line.lot_id.out_navy_line = line.out_navy_line
                    line.lot_id.gate_out_date = datetime.datetime.now()

        return res

    def generate_report_file(self, picking_id):
        report = self.env.ref('stock.action_report_picking', False)
        pdf = report._render_qweb_pdf(picking_id)[0]
        pdf = base64.b64encode(pdf)
        return pdf

    def get_responsible(self):
        partners = self.env['res.partner']
        for user in self.company_id.user_sp_access:
            if user.partner_id.email:
                partners += user.partner_id
            else:
                raise ValidationError(f"El usuario {user.name} no cuenta con un correo electrónico en su contacto.")
        if partners:
            return str(partners.ids).replace('[', '').replace(']', '')
        else:
            raise ValidationError("No se encontró personal asignado para autorizar esta operación.")

    def grant_access(self):
        self.access_granted = True

    def write(self, vals):
        for rec in self:
            if rec.origin and 'origin' not in vals and rec.is_rental:
                sale_id = self.env['sale.order'].search([('name', '=', rec.origin)])
                vals['sale_id'] = sale_id.id if sale_id else False
            actual_sale_id = rec.sale_id.id
            if 'sale_id' in vals and rec.is_rental:
                if not vals.get('sale_id') and actual_sale_id:
                    vals['sale_id'] = actual_sale_id
                else:
                    sale_id = self.env['sale.order'].search([('name', '=', rec.origin)])
                    vals['sale_id'] = sale_id.id if sale_id else False
        res = super(StockPicking, self).write(vals)

        return res

    def button_confirm(self):
        self = self.sudo()
        sale_id = self.sale_id
        if not sale_id:
            find_sale_id = self.env['sale.order'].search([('name', '=', self.origin)])
            self.sale_id = find_sale_id.id if find_sale_id else False

        # region Rental Order
        if self.is_rental and sale_id and sale_id.is_rental_order:
            if self.picking_type_code == 'outgoing':
                for line in sale_id.order_line:
                    line.pickup_date = datetime.datetime.now()
                    line.product_id_change()
                if sale_id.rental_subscription_id:
                    date_today = fields.Date.context_today(self)
                    recurring_invoice_day = date_today.day
                    recurring_next_date = self.env['sale.subscription']._get_recurring_next_date(
                        sale_id.rental_template_id.recurring_rule_type, sale_id.rental_template_id.recurring_interval,
                        date_today, recurring_invoice_day
                    )
                    sale_id.rental_subscription_id.write({
                        'date_start': date_today,
                        'recurring_next_date': recurring_next_date,
                        'recurring_invoice_day': recurring_invoice_day
                    })

                    sale_id.update_existing_rental_subscriptions()

                    for line in sale_id.mapped('invoice_ids.invoice_line_ids'):
                        line._get_stock_reserved_lot_ids()
            elif self.picking_type_code == 'incoming':
                returned = True
                for line in sale_id.order_line.filtered(lambda l: l.product_id.type != 'service'):
                    if line.product_uom_qty > 0 and line.qty_returned < line.qty_delivered:
                        returned = False
                if sale_id.rental_subscription_id and returned:
                    sale_id.rental_subscription_id.set_close()
                else:
                    if sale_id.rental_subscription_id:
                        for line in sale_id.order_line.filtered(lambda l: l.product_id.type != 'service'):
                            if line.return_date and line.product_uom_qty > 0 and line.qty_returned == line.qty_delivered:
                                line.product_uom_qty = 0
                        sale_id.update_existing_rental_subscriptions()

        # endregion

        if self.picking_type_code == 'incoming':
            for line in self.move_ids_without_package:
                if line.rent_state:
                    for lot in line.lot_ids:
                        lot.rent_state = line.rent_state
                else:
                    raise ValidationError("Debe colocar el estado de devolucion de la unidad.")
        self.state = 'done'
        self.date_done = fields.Datetime.now()

    def request_access(self):
        self = self.sudo()
        sale_id = self.sale_id
        if self.picking_type_code == 'outgoing' and sale_id and not self.is_gate_service:
            if not sale_id.partner_id.allowed_credit:
                if len(sale_id.invoice_ids) < 1:
                    raise ValidationError(f"El documento de origen no ha sido facturado. "
                                          f"Documento de referencia **{sale_id.name}**.")
                else:
                    checks = []
                    pay_checks = []
                    for inv in sale_id.invoice_ids:
                        if inv.state != 'posted':
                            checks.append(True)
                        elif inv.payment_state != 'paid':
                            pay_checks.append(True)
                        else:
                            pay_checks.append(False)
                            checks.append(False)
                    if all(checks):
                        raise ValidationError(f"El documento de origen no tiene facturas confirmadas. "
                                              f"Documento de referencia **{sale_id.name}**.")
                    elif all(pay_checks):
                        raise ValidationError(f"El documento de origen no ha sido totalmente pagado. "
                                              f"Documento de referencia **{sale_id.name}**.")

                # raise ValidationError(f"El documento de origen no ha sido facturado. "
                #                       f"Documento de referencia **{sale_id.name}**.")

        report_binary = self.generate_report_file(self.id)
        attachment_name = "SA_" + self.name
        attachment_id = self.env['ir.attachment'].create({
            'name': attachment_name + '.pdf',
            'type': 'binary',
            'datas': report_binary,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })

        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = \
                ir_model_data.get_object_reference('equiport_custom', 'email_template_request_picking_access')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})

        if template_id:
            self.env['mail.template'].browse(template_id).update({
                'attachment_ids': [(6, 0, [attachment_id.id])]
            })
        ctx.update({
            'default_model': self._name,
            'active_model': self._name,
            'active_id': self.id,
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'mark_requested_access': True,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_light",
            'attachment_ids': [attachment_id.id],
            'force_email': True,
        })

        ctx['model_description'] = 'Solicitud de autorizacion de conduce'

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        self = self.sudo()
        if self.env.context.get('mark_requested_access'):
            self.write({'access_requested': True})
            kwargs['attachment_ids'] = self.env.context.get('attachment_ids')

        res = super(StockPicking, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)
        # TODO find a better way to no create extra attachment
        attachment_id = self.env['ir.attachment'].search(
            [('res_model', '=', 'mail.compose.message'), ('name', '=', f"SA_{self.name}.pdf")])

        if attachment_id:
            attachment_id.unlink()

        return res


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_gate_stock = fields.Boolean(string="Almacen Gate In / Gate Out")
    is_mobile_stock = fields.Boolean(string="Almacen movil")
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string="Vehiculo Almacen")


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_gate_operation = fields.Boolean(related='warehouse_id.is_gate_stock', string="Operacion Gate In / Gate Out")


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_gate_location = fields.Boolean(string="Ubicacion Gate In / Gate Out")


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    rent_ok = fields.Boolean(related='product_id.rent_ok')
    is_tire_lot = fields.Boolean(related='product_id.is_tire_product')
    tire_state_id = fields.Many2one(string="Estado de neúmatico", comodel_name='tire.state')
    assigned_tire = fields.Boolean(string="esta asignado?")
    positive_qty = fields.Boolean(compute='_compute_positive_qty', store=True)
    unit_type = fields.Selection(related='product_id.unit_type')
    unit_year = fields.Char(string="Año de unidad")
    unit_grade_id = fields.Many2one(comodel_name='product.grade', string='Grado')
    active = fields.Boolean(string="Activo", default=True)
    in_scrap = fields.Boolean(string="En desecho", related='tire_state_id.scrap_state')

    @api.depends('product_qty', 'product_id')
    def _compute_positive_qty(self):
        for rec in self:
            if rec.product_qty > 0:
                rec.positive_qty = True
            else:
                rec.positive_qty = False

    @api.onchange('product_id', 'name', 'positive_qty')
    def set_domain_gate_picking_type(self):
        if self._context.get('fleet_menu'):
            return {
                'domain': {
                    'product_id': [('is_tire_product', '=', True)]
                }
            }

    @api.constrains('name')
    def check_general_unique_lot(self):

        for rec in self:
            domain = [('product_id', 'in', rec.product_id.ids),
                      ('company_id', 'in', rec.company_id.ids),
                      ('name', 'in', rec.mapped('name')),
                      ('id', '!=', rec.ids)]

            records = self.search(domain)
            error_message_lines = []
            for item in records:
                error_message_lines.append(
                    _(" - Producto: %s, Número de Referencia Interna: %s", item.product_id.name, rec.name))

            if error_message_lines:
                raise ValidationError(
                    _('El número de referencia interna debe ser unico por compañia.\nLos siguientes contienen duplicados:\n') + '\n'.join(
                        error_message_lines))

    # Gate service
    is_gate_product = fields.Boolean(string="Servicio Gate In / Gate Out", compute='compute_gate_product')
    external_owner = fields.Boolean(string="Unidad Externa")
    owner_partner_id = fields.Many2one(comodel_name='res.partner', string="Propietario")
    gate_in_date = fields.Datetime(string="Fecha de entrada")
    gate_out_date = fields.Datetime(string="Fecha de salida")
    storage_rate = fields.Float(string="Tasa de estadia")
    in_booking = fields.Char(string="Número de reserva entrada")
    in_stamp = fields.Char(string="Sello entrada")
    in_boat = fields.Char(string="Barco entrada")
    in_navy_line = fields.Char(string="Linea naviera entrada")

    out_booking = fields.Char(string="Número de reserva salida")
    out_stamp = fields.Char(string="Sello salida")
    out_boat = fields.Char(string="Barco salida")
    out_navy_line = fields.Char(string="Linea naviera salida")

    @api.depends('product_id')
    def compute_gate_product(self):
        for serial in self:
            if serial.product_id.type == 'product' and not serial.product_id.purchase_ok and not serial.product_id.sale_ok and not serial.product_id.rent_ok:
                serial.is_gate_product = True
            else:
                serial.is_gate_product = False

    # Campos relacionados actividad Alquiler
    rent_state = fields.Selection(
        [('available', 'Disponible'), ('rented', 'Alquilado'), ('sold', 'Vendido'),('to_check', 'Pendiente inspección'),
         ('to_repair', 'Pendiente mantenimiento'),
         ('to_wash', 'Pendiente lavado'), ('damaged', 'Averiado'), ('scrap', 'Desecho')],
        string="Estado", default="available")

    def change_state(self):
        states = list(map(lambda s: s[0], self._fields.get('rent_state').selection))
        idx = states.index(self.rent_state)

        self.write({
            'rent_state': states[idx + 1 if idx < (len(states) - 1) else 0]
        })


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    rent_state = fields.Selection(
        [('available', 'Disponible'), ('to_check', 'Pendiente inspección'),
         ('to_repair', 'Pendiente mantenimiento'),
         ('to_wash', 'Pendiente lavado'), ('damaged', 'Averiado')],
        string="Estado")

    in_booking = fields.Char(string="Número de reserva entrada")
    in_stamp = fields.Char(string="Sello entrada")
    in_boat = fields.Char(string="Barco entrada")
    in_navy_line = fields.Char(string="Linea naviera entrada")

    out_booking = fields.Char(string="Número de reserva salida")
    out_stamp = fields.Char(string="Sello salida")
    out_boat = fields.Char(string="Barco salida")
    out_navy_line = fields.Char(string="Linea naviera salida")


class StockMove(models.Model):
    _inherit = 'stock.move'

    rent_state = fields.Selection(
        [('available', 'Disponible'), ('to_check', 'Pendiente inspección'),
         ('to_repair', 'Pendiente mantenimiento'),
         ('to_wash', 'Pendiente lavado'), ('damaged', 'Averiado')],
        string="Estado")

    def write(self, vals):

        res = super(StockMove, self).write(vals)

        for rec in self:
            move_rent_states = self.search([('picking_id', '=', rec.picking_id.id)]).mapped('rent_state')
            if rec.picking_id.picking_type_code == 'incoming' and rec.picking_id.is_rental and rec.rent_state and all(move_rent_states):
                rec.picking_id.button_confirm()

        return res

    storage_rate = fields.Float(string="Tasa de estadia")


class TireState(models.Model):
    _name = 'tire.state'

    name = fields.Char(string="Titulo", required=True)
    scrap_state = fields.Boolean(string="Estado de desecho")
    active = fields.Boolean(string="Archivado", default=True)
