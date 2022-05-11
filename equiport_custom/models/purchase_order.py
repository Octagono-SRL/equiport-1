# -*- coding: utf-8 -*-
import base64
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # region Service Picking
    receivable_service = fields.Boolean(string="Recibir servicios", compute='_compute_receivable_service')
    service_picking_ids = fields.One2many(comodel_name='stock.service.picking', inverse_name='purchase_order_id',
                                          string="Conduces de servicio")
    service_receipt_count = fields.Integer(
        compute='_compute_service_picking_count', string="Número de conduces")

    def action_view_service_receipt(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("equiport_custom.stock_service_picking_act_window")

        pickings = self.mapped('service_picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('equiport_custom.stock_service_picking_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        return action

    @api.depends('service_picking_ids')
    def _compute_service_picking_count(self):
        for rec in self:
            rec.service_receipt_count = len(rec.service_picking_ids)

    @api.depends('order_line', 'state')
    def _compute_receivable_service(self):
        for rec in self:
            services = rec.order_line.filtered(lambda
                                                   l: l.product_id.type == 'service' and l.product_uom_qty != l.qty_received and l.receivable_service)

            if services and len(services) > 0:
                rec.receivable_service = True
            else:
                rec.receivable_service = False

    # endregion

    # region Solicitud de Cancelacion
    allowed_cancel = fields.Boolean(string="Cancelación aprobada", tracking=True)
    allowed_cancel_sign = fields.Binary(copy=False)
    allowed_cancel_signed_by = fields.Char('Cancelación firmada por',
                                           help='Nombre de la persona que firmo la aprobacion de cancelacion.',
                                           copy=False)
    allowed_cancel_date_sign = fields.Datetime(string="Fecha de cancelación")
    is_cancel_group = fields.Boolean(string="Grupo de cancelacion", compute="_check_cancel_group")
    requested_cancel = fields.Boolean(string="Solicitó cancelación", tracking=True)
    cancel_reason = fields.Selection([
        ('supplier_no_fulfill', 'El suplidor no cumplió con una o varias de las especificaciones del pedido'),
        ('no_need', 'Los materiales ya no son necesarios'),
        ('order_has_errors', 'Se realizó una orden con error identificado luego de la impresión'),
        ('change_info', 'Cambios en la informacion de la orden'),
    ], tracking=True, string="Razón de Cancelación")

    @api.depends('requested_cancel')
    def _check_cancel_group(self):
        for rec in self:
            if self.env.user in self.env.company.user_po_allow_cancel:
                rec.is_cancel_group = True
            else:
                rec.is_cancel_group = False

    def request_cancel(self):

        view_id = self.env.ref('equiport_custom.purchase_order_cancel_wizard_view_form')
        context = {
            'cancel_reason': self.cancel_reason or '',
            'order_id': self.id,
            'user_id': self.env.user.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.purchase.order.cancel',
            'views': [(view_id.id, 'form')],
            'view_id': view_id.id,
            'target': 'new',
            'context': context,
        }

    def get_responsible_cancel(self):
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

    def allow_cancel(self):
        if not self.allowed_cancel_sign:
            raise ValidationError(
                "El documento debe ser firmado, dirijase a la sección de aprobación de cancelación en la pestaña de firmas.")
        self.with_context(self._context, approved_cancel=True).write({
            'allowed_cancel_date_sign': datetime.datetime.now(),
            'allowed_cancel_signed_by': self.env.user.display_name,
            'allowed_cancel': True
        })

    def sign_cancel_with_user(self):
        env_user = self.env.user
        if not env_user.sign_signature:
            raise ValidationError("Su usuario no cuenta con una firma digital registrada")
        self.write({
            'allowed_cancel_sign': env_user.sign_signature
        })

    # endregion

    # region Aprovacion escalonada con firmas
    allowed_confirm = fields.Boolean(string="Confirmación aprobada", tracking=True)

    op_ini_user_id = fields.Many2one(related='company_id.op_ini_user_id')
    op_mid_user_id = fields.Many2one(related='company_id.op_mid_user_id')
    op_top_user_id = fields.Many2one(related='company_id.op_top_user_id')

    is_ini_user = fields.Boolean(compute='_compute_logged_user', string="Es usuario 1")
    is_mid_user = fields.Boolean(compute='_compute_logged_user', string="Es usuario 2")
    is_top_user = fields.Boolean(compute='_compute_logged_user', string="Es usuario 3")

    @api.depends('op_ini_user_id', 'op_mid_user_id', 'op_top_user_id')
    def _compute_logged_user(self):
        for rec in self:
            actual_user = self.env.user
            if rec.op_ini_user_id == actual_user:
                rec.is_ini_user = True
            else:
                rec.is_ini_user = False

            if rec.op_mid_user_id == actual_user:
                rec.is_mid_user = True
            else:
                rec.is_mid_user = False

            if rec.op_top_user_id == actual_user:
                rec.is_top_user = True
            else:
                rec.is_top_user = False

    allowed_confirm_sign_one = fields.Binary(copy=False)
    allowed_confirm_sign_two = fields.Binary(copy=False)
    allowed_confirm_sign_three = fields.Binary(copy=False)
    allowed_confirm_sign_level = fields.Binary(copy=False)
    allowed_confirm_sign_level_date = fields.Datetime(string="Fecha de aprobación final")
    allowed_confirm_sign_level_by = fields.Char(copy=False, string="Aprovacion final")
    allowed_confirm_signed_by = fields.Char('Aprobacion firmada por',
                                            help='Nombre de la persona que firmo la aprobacion de monto.', copy=False)
    allowed_confirm_date_sign_one = fields.Datetime(string="Fecha de aprobación primer nivel")
    allowed_confirm_date_sign_two = fields.Datetime(string="Fecha de aprobación segundo nivel")
    allowed_confirm_date_sign_three = fields.Datetime(string="Fecha de aprobación tercer nivel")
    is_approval_group = fields.Boolean(string="Grupo de aprobacion", compute="_check_approval_group")
    approval_level = fields.Selection(
        selection=[('one', 'Primer nivel'), ('two', 'Segundo nivel'), ('three', 'Tercer nivel')],
        compute='_check_approval_need', string="Nivel de aprobación")
    actual_approval_level = fields.Selection(
        selection=[('one', 'Primer nivel'), ('two', 'Segundo nivel'), ('three', 'Tercer nivel'),
                   ('complete', 'Totalmente aprobado')], compute='_check_approval_need', store=True,
        string="Nivel de aprobación actual")
    request_approval = fields.Boolean(string="Solicitó aprobación", tracking=True)
    approval_needed = fields.Boolean(string="Aprobación Requerida", compute='_check_approval_need')

    @api.depends('approval_needed')
    def _check_approval_group(self):
        approval_list = [self.env.company.op_ini_user_id, self.env.company.op_mid_user_id,
                         self.env.company.op_top_user_id]
        for rec in self:
            if self.env.user in approval_list:
                rec.is_approval_group = True
            else:
                rec.is_approval_group = False

    def get_currency_amount(self, amount):
        company_id = self.company_id
        company_currency_id = company_id.currency_id
        return company_currency_id._convert(amount, self.currency_id, self.company_id, self.date_order)

    @api.depends('amount_total', 'company_id.active_op_approval', 'allowed_confirm')
    def _check_approval_need(self):
        for rec in self:
            company_id = rec.company_id
            op_approval = company_id.active_op_approval

            if rec.amount_total <= 0:
                rec.approval_level = False

            if op_approval:
                if rec.get_currency_amount(company_id.op_ini_level) <= rec.amount_total:
                    rec.approval_needed = True
                    rec.approval_level = 'one'
                if rec.get_currency_amount(company_id.op_mid_level) <= rec.amount_total:
                    rec.approval_level = 'two'
                    rec.approval_needed = True
                if rec.get_currency_amount(company_id.op_top_level) <= rec.amount_total:
                    rec.approval_level = 'three'
                    rec.approval_needed = True

                # CODIGO CONFIGURANDO ENVIO POR DE CORREO POR NIVEL

                if rec.approval_level == 'one':
                    if rec.allowed_confirm_sign_one:
                        rec.actual_approval_level = 'complete'
                    else:
                        rec.actual_approval_level = 'one'
                elif rec.approval_level == 'two':
                    if rec.allowed_confirm_sign_one and rec.allowed_confirm_sign_two:
                        rec.actual_approval_level = 'complete'
                    elif rec.allowed_confirm_sign_one and not rec.allowed_confirm_sign_two:
                        rec.actual_approval_level = 'two'
                    else:
                        rec.actual_approval_level = 'one'
                elif rec.approval_level == 'three':
                    if rec.allowed_confirm_sign_one and rec.allowed_confirm_sign_two and rec.allowed_confirm_sign_three:
                        rec.actual_approval_level = 'complete'
                    elif rec.allowed_confirm_sign_one and not rec.allowed_confirm_sign_two and not rec.allowed_confirm_sign_three:
                        rec.actual_approval_level = 'two'
                    elif rec.allowed_confirm_sign_one and rec.allowed_confirm_sign_two and not rec.allowed_confirm_sign_three:
                        rec.actual_approval_level = 'three'
                    else:
                        rec.actual_approval_level = 'one'
            else:
                rec.approval_needed = False
                rec.approval_level = False

    def request_confirm(self):

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
                ir_model_data.get_object_reference('equiport_custom', 'email_template_request_purchase_order_confirm')[
                    1]
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
            'default_model': 'purchase.order',
            'active_model': 'purchase.order',
            'active_id': self.id,
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'mark_request_approval': True,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'attachment_ids': [attachment_id.id],
            'force_email': True,
        })

        ctx['model_description'] = 'Solicitud de aprobación de monto'

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

    def get_responsible(self):
        company_id = self.company_id
        op_approval = company_id.active_op_approval
        responsible = self.env['res.partner']
        if op_approval:
            if self.get_currency_amount(company_id.op_ini_level) <= self.amount_total:
                responsible += company_id.op_ini_user_id.partner_id
            if self.get_currency_amount(company_id.op_mid_level) <= self.amount_total:
                responsible += company_id.op_mid_user_id.partner_id
            if self.get_currency_amount(company_id.op_top_level) <= self.amount_total:
                responsible += company_id.op_top_user_id.partner_id

            partners = responsible
            partners = list(set(partners))
            for partner in partners:
                if not partner.email:
                    raise ValidationError(
                        'El cliente o usuario {partner} no tiene correo electronico asignado.'.format(
                            partner=partner.name)
                    )

            return str([p.id for p in partners]).replace('[', '').replace(']', '')

    def sign_with_user_sign(self):
        env_user = self.env.user
        if not env_user.sign_signature:
            raise ValidationError("Su usuario no cuenta con una firma digital registrada")
        if env_user == self.op_ini_user_id:
            self.write({
                'allowed_confirm_sign_one': env_user.sign_signature
            })
        elif env_user == self.op_mid_user_id:
            self.write({
                'allowed_confirm_sign_two': env_user.sign_signature
            })
        elif env_user == self.op_top_user_id:
            self.write({
                'allowed_confirm_sign_three': env_user.sign_signature
            })

    def allow_confirm(self):
        if self.approval_level:
            responsible = False
            if self.approval_level == 'one':
                responsible = self.company_id.op_ini_user_id
                if not self.allowed_confirm_sign_one:
                    raise ValidationError(
                        "El documento debe ser firmado, dirijase a la sección de aprobación de monto en la pestaña de firmas.")
                self.allowed_confirm_sign_level = self.allowed_confirm_sign_one
                self.allowed_confirm_sign_level_by = responsible.name
                self.allowed_confirm_sign_level_date = self.allowed_confirm_date_sign_one
            elif self.approval_level == 'two':
                responsible = self.company_id.op_mid_user_id
                if not self.allowed_confirm_sign_one or not self.allowed_confirm_sign_two:
                    raise ValidationError(
                        "El documento debe ser firmado por los usuarios de primer y segundo nivel de aprobacion, dirijase a la sección de aprobación de monto en la pestaña de firmas.")
                self.allowed_confirm_sign_level = self.allowed_confirm_sign_two
                self.allowed_confirm_sign_level_by = responsible.name
                self.allowed_confirm_sign_level_date = self.allowed_confirm_date_sign_two
            elif self.approval_level == 'three':
                responsible = self.company_id.op_top_user_id
                if not self.allowed_confirm_sign_one or not self.allowed_confirm_sign_two or not self.allowed_confirm_sign_three:
                    raise ValidationError(
                        "El documento debe ser firmado por los usuarios de primer, segundo y tercer nivel de aprobacion, dirijase a la sección de aprobación de monto en la pestaña de firmas.")
                self.allowed_confirm_sign_level = self.allowed_confirm_sign_three
                self.allowed_confirm_sign_level_by = responsible.name
                self.allowed_confirm_sign_level_date = self.allowed_confirm_date_sign_three
            # if self.env.user != responsible:
            #     raise ValidationError(
            #         "El usuario encargado de la aprobacion final es {0}.".format(responsible.display_name))

        self.write({
            'allowed_confirm': True,
            'state': 'draft'
        })

    # endregion

    def generate_report_file(self, order_id):
        report = self.env.ref('purchase.action_report_purchase_order', False)
        pdf = report._render_qweb_pdf(order_id)[0]
        pdf = base64.b64encode(pdf)
        return pdf

    # region Herencia funciones Base

    def write(self, vals):
        # region SIGN PROCESS
        sign_list = ['allowed_confirm_sign_one', 'allowed_confirm_sign_two', 'allowed_confirm_sign_three']
        if any([sign in vals for sign in sign_list]):
            activity_type_id = self.env.ref('equiport_custom.mail_activity_purchase_order_approval')
            if 'allowed_confirm_sign_one' in vals:
                vals['allowed_confirm_date_sign_one'] = datetime.datetime.now()
                activity_id = self.activity_ids.filtered(
                    lambda act: act.user_id == self.op_ini_user_id and act.activity_type_id == activity_type_id)
                if activity_id:
                    activity_id.action_done()
                if self.allowed_confirm_signed_by:
                    vals['allowed_confirm_signed_by'] = "{0}, {1}".format(self.allowed_confirm_signed_by,
                                                                          self.op_ini_user_id.display_name)
                else:
                    vals['allowed_confirm_signed_by'] = self.op_ini_user_id.display_name

            if 'allowed_confirm_sign_two' in vals:
                vals['allowed_confirm_date_sign_two'] = datetime.datetime.now()
                activity_id = self.activity_ids.filtered(
                    lambda act: act.user_id == self.op_mid_user_id and act.activity_type_id == activity_type_id)
                if activity_id:
                    activity_id.action_done()
                if self.allowed_confirm_signed_by:
                    vals['allowed_confirm_signed_by'] = "{0}, {1}".format(self.allowed_confirm_signed_by,
                                                                          self.op_mid_user_id.display_name)
                else:
                    vals['allowed_confirm_signed_by'] = self.op_mid_user_id.display_name

            if 'allowed_confirm_sign_three' in vals:
                vals['allowed_confirm_date_sign_three'] = datetime.datetime.now()
                activity_id = self.activity_ids.filtered(
                    lambda act: act.user_id == self.op_top_user_id and act.activity_type_id == activity_type_id)
                if activity_id:
                    activity_id.action_done()
                if self.allowed_confirm_signed_by:
                    vals['allowed_confirm_signed_by'] = "{0}, {1}".format(self.allowed_confirm_signed_by,
                                                                          self.op_top_user_id.display_name)
                else:
                    vals['allowed_confirm_signed_by'] = self.op_top_user_id.display_name

        # endregion

        reset = False
        if self.request_approval and self.allowed_confirm and self.state in ['sent', 'to approve', 'draft']:
            reset = True
            vals.update({
                'request_approval': False,
                'allowed_confirm': False,
            })
        mark_request_cancel = self._context.get('mark_request_cancel', False) or self._context.get('params', {}).get(
            'mark_request_cancel', False) or self._context.get('approved_cancel', False) or \
                              self._context.get('params', {}).get('approved_cancel', False)
        if 'allowed_cancel_sign' in vals:
            mark_request_cancel = True

        if not mark_request_cancel and (
                (self.state == 'purchase' and vals.get('state', False) not in ['cancel', 'done']) or (
                self.state == 'done' and vals.get('state', False) not in ['purchase'])
        ):
            fields_list = [
                'partner_id',
                'partner_ref',
                'requisition_id',
                'currency_id',
                'notes',
                'date_order',
                'date_planned',
                'order_line',
                'payment_term_id',
                'fiscal_position_id',
                'user_id',
                'incoterm_id',
                'picking_type_id'
            ]
            for field in fields_list:
                if field in vals:
                    raise UserError(
                        'No puedes editar una orden confirmada. Cancele la orden; Solicite aprobación de ser requerido')

            reset = False
        if self.state == 'to approve' and vals.get('state', False) in ['purchase']:
            reset = False

        res = super(PurchaseOrder, self).write(vals)
        if reset:
            body = """
            </br>
            <p>Debido a cambio en la informacion de la orden se ha reiniciado el proceso de autorizacion de la orden.</p>
            </br>
            </br>
            </br>
            <h2><b>Información aprobacion previa:</b></h2>
            <ul>
                %s
                %s
                %s
                %s
                %s
            </ul>
            """ % (
                ('<li><b>Fecha de aprobación primer nivel:</b> {0}</li>'.format(
                    self.allowed_confirm_date_sign_one) if self.allowed_confirm_date_sign_one else ''),
                ('<li><b>Fecha de aprobación segundo nivel:</b> {0}</li>'.format(
                    self.allowed_confirm_date_sign_two) if self.allowed_confirm_date_sign_two else ''),
                ('<li><b>Fecha de aprobación tercer nivel:</b> {0}</li>'.format(
                    self.allowed_confirm_date_sign_three) if self.allowed_confirm_date_sign_three else ''),
                ('<li><b>Aprobación firmada por:</b> {0}</li>'.format(
                    self.allowed_confirm_signed_by) if self.allowed_confirm_signed_by else ''),
                ('<li><b>Orden aprobada para:</b> {0}</li>'.format(
                    self.user_id.name) if self.user_id else ''),
            )
            self.message_post(
                body=body,
                message_type='notification'
            )
        return res

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_request_cancel'):
            self.write({
                'requested_cancel': True,
                'cancel_reason': self.env.context.get('cancel_reason', '')
            })

        if self.env.context.get('mark_request_approval'):
            if not self.request_approval:
                users = self.env['res.users']
                company_id = self.company_id
                op_approval = company_id.active_op_approval
                if op_approval:
                    if self.get_currency_amount(company_id.op_ini_level) <= self.amount_total:
                        users += company_id.op_ini_user_id
                    if self.get_currency_amount(company_id.op_mid_level) <= self.amount_total:
                        users += company_id.op_mid_user_id
                    if self.get_currency_amount(company_id.op_top_level) <= self.amount_total:
                        users += company_id.op_top_user_id
                for u in list(set(users)):
                    self.activity_schedule(
                        'equiport_custom.mail_activity_purchase_order_approval', self.date_order.date(),
                        summary="Documento a la espera de aprobación",
                        user_id=u.id)
            self.write({
                'request_approval': True,
                'state': 'to approve'
            })
            kwargs['attachment_ids'] = self.env.context.get('attachment_ids')

        res = super(PurchaseOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)
        # TODO find a better way to no create extra attachment
        attachment_id = self.env['ir.attachment'].search(
            [('res_model', '=', 'mail.compose.message'), ('name', '=', f"SA_{self.name}.pdf")])

        if attachment_id:
            attachment_id.unlink()

        return res

    def button_confirm(self):
        company_id = self.company_id
        op_approval = company_id.active_op_approval
        if op_approval and not self.allowed_confirm:
            if self.get_currency_amount(company_id.op_ini_level) <= self.amount_total:
                raise ValidationError("No es posible confirmar. Solicite una aprobación por el monto actual.")

        res = super(PurchaseOrder, self).button_confirm()

        return res

    def button_cancel(self):
        if not self.allowed_cancel:
            raise ValidationError("""No es posible cancelar. Solicite aprobación de cancelación para orden.""")

        body = """
                    </br>
                    <p>Debido a la cancelacion de la orden de la orden se ha reiniciado el proceso de autorizacion cancelacion de la orden.</p>
                    </br>
                    </br>
                    </br>
                    <h2><b>Información cancelacion previa:</b></h2>
                    <ul>
                        %s
                        %s
                        %s
                    </ul>
                    """ % (
            ('<li><b>Fecha de aprobación:</b> {0}</li>'.format(
                self.allowed_cancel_date_sign) if self.allowed_cancel_date_sign else ''),
            ('<li><b>Razon de cancelacion:</b> {0}</li>'.format(
                self.cancel_reason) if self.cancel_reason else ''),
            ('<li><b>Aprobación firmada por:</b> {0}</li>'.format(
                self.allowed_cancel_signed_by) if self.allowed_cancel_signed_by else ''),
        )

        self.message_post(
            body=body,
            message_type='notification'
        )

        self.write({
            'requested_cancel': False,
            'allowed_cancel': False
        })
        res = super(PurchaseOrder, self).button_cancel()
        return res

    # endregion


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    receivable_service = fields.Boolean(string="Se puede recibir", compute='_compute_service_qty_received')
    service_picking_line_ids = fields.One2many(comodel_name='stock.service.move', inverse_name='purchase_order_line_id',
                                               string="Movimientos de servicio")

    @api.depends('qty_received', 'service_picking_line_ids')
    def _compute_service_qty_received(self):
        for rec in self:
            # rec.service_picking_line_ids.unlink()
            picking_qty = sum(
                rec.service_picking_line_ids.filtered(lambda spl: spl.state != 'cancel').mapped('product_uom_qty'))
            if (rec.product_uom_qty - picking_qty) > 0:
                rec.receivable_service = True
            else:
                rec.receivable_service = False

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values,
                                                      po):
        res = super(PurchaseOrderLine, self)._prepare_purchase_order_line_from_procurement(product_id, product_qty,
                                                                                           product_uom, company_id,
                                                                                           values,
                                                                                           po)
        if res['name']:
            res['name'] += '\n Uso: ' + values.get('order_use')
        else:
            res['name'] = 'Uso: ' + values.get('order_use')

        return res
