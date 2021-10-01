# -*- coding: utf-8 -*-
import base64
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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
        self.allowed_cancel_date_sign = datetime.datetime.now()
        self.allowed_cancel_signed_by = self.env.user.display_name
        self.allowed_cancel = True

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
        compute='_check_approval_need')
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

    @api.depends('amount_total', 'company_id.active_op_approval')
    def _check_approval_need(self):
        for rec in self:
            company_id = rec.company_id
            op_approval = company_id.active_op_approval
            if op_approval:
                if company_id.op_ini_level <= rec.amount_total:
                    rec.approval_needed = True
                    rec.approval_level = 'one'
                if company_id.op_mid_level <= rec.amount_total:
                    rec.approval_level = 'two'
                if company_id.op_top_level <= rec.amount_total:
                    rec.approval_level = 'three'
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
            if company_id.op_ini_level <= self.amount_total:
                responsible += company_id.op_ini_user_id.partner_id
            if company_id.op_mid_level <= self.amount_total:
                responsible += company_id.op_mid_user_id.partner_id
            if company_id.op_top_level <= self.amount_total:
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
            if self.env.user != responsible:
                raise ValidationError(
                    "El usuario encargado de la aprobacion final es {0}.".format(responsible.display_name))

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
        sign_list = ['allowed_confirm_sign_one', 'allowed_confirm_sign_two', 'allowed_confirm_sign_three']
        if any([sign in vals for sign in sign_list]):
            if 'allowed_confirm_sign_one' in vals:
                vals['allowed_confirm_date_sign_one'] = datetime.datetime.now()
                if self.allowed_confirm_signed_by:
                   vals['allowed_confirm_signed_by'] = "{0}, {1}".format(self.allowed_confirm_signed_by, self.op_ini_user_id.display_name)
                else:
                    vals['allowed_confirm_signed_by'] = self.op_ini_user_id.display_name

            if 'allowed_confirm_sign_two' in vals:
                vals['allowed_confirm_date_sign_two'] = datetime.datetime.now()
                if self.allowed_confirm_signed_by:
                   vals['allowed_confirm_signed_by'] = "{0}, {1}".format(self.allowed_confirm_signed_by, self.op_mid_user_id.display_name)
                else:
                    vals['allowed_confirm_signed_by'] = self.op_mid_user_id.display_name

            if 'allowed_confirm_sign_three' in vals:
                vals['allowed_confirm_date_sign_three'] = datetime.datetime.now()
                if self.allowed_confirm_signed_by:
                   vals['allowed_confirm_signed_by'] = "{0}, {1}".format(self.allowed_confirm_signed_by, self.op_top_user_id.display_name)
                else:
                    vals['allowed_confirm_signed_by'] = self.op_top_user_id.display_name

        res = super(PurchaseOrder, self).write(vals)
        return res

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_request_cancel'):
            self.write({'requested_cancel': True})

        if self.env.context.get('mark_request_approval'):
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
            if company_id.op_ini_level <= self.amount_total:
                raise ValidationError("No es posible confirmar. Solicite una aprobación por el monto actual.")

        res = super(PurchaseOrder, self).button_confirm()

        return res

    def button_cancel(self):
        if not self.allowed_cancel:
            raise ValidationError("""No es posible cancelar. Solicite aprobación de cancelación para orden.""")
        res = super(PurchaseOrder, self).button_cancel()
        return res

    # endregion


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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

