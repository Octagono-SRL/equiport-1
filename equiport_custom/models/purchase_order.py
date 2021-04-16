# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    allowed_cancel = fields.Boolean(string="Cancelación aprobada", track_visibility='onchange')
    allowed_confirm = fields.Boolean(string="Confirmación aprobada", track_visibility='onchange')
    request_approval = fields.Boolean(string="Solicitó aprobación", track_visibility='onchange')
    approval_needed = fields.Boolean(string="Aprobación Requerida", compute='_check_approval_need')
    requested_cancel = fields.Boolean(string="Solicitó cancelación", track_visibility='onchange')
    cancel_reason = fields.Selection([('test', 'Prueba'), ('test2', 'Prueba2')], track_visibility='onchange' , string="Razón de Cancelación")

    @api.depends('amount_total', 'company_id.active_op_approval')
    def _check_approval_need(self):
        for rec in self:
            company_id = rec.company_id
            op_approval = company_id.active_op_approval
            if op_approval:
                if company_id.op_ini_level <= rec.amount_total:
                    rec.approval_needed = True
                else:
                    rec.approval_needed = False
            else:
                rec.approval_needed = False

    def generate_report_file(self, order_id):
        report = self.env.ref('purchase.action_report_purchase_order', False)
        pdf = report._render_qweb_pdf(order_id)[0]
        pdf = base64.b64encode(pdf)
        return pdf

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

    def get_responsible(self, partner_only=False):
        company_id = self.company_id
        op_approval = company_id.active_op_approval
        responsible = False
        if op_approval:
            if company_id.op_ini_level <= self.amount_total < company_id.op_mid_level:
                responsible = company_id.op_ini_user_id.partner_id
            elif company_id.op_mid_level <= self.amount_total < company_id.op_top_level:
                responsible = company_id.op_mid_user_id.partner_id
            elif company_id.op_top_level <= self.amount_total:
                responsible = company_id.op_top_user_id.partner_id

            partners = responsible
            partners = list(set(partners))
            for partner in partners:
                if not partner.email:
                    raise ValidationError(
                        'El cliente o usuario {partner} no tiene correo electronico asignado.'.format(
                            partner=partner.name)
                    )
            if partner_only:
                return responsible
            else:
                return str([p.id for p in partners]).replace('[', '').replace(']', '')

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
            template_id = ir_model_data.get_object_reference('equiport_custom', 'email_template_request_purchase_order_confirm')[1]
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

        ctx['model_description'] = 'Solicitud de aprobación de cancelación'

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
        if self.env.context.get('mark_request_cancel'):
            self.write({'requested_cancel': True})

        if self.env.context.get('mark_request_approval'):
            self.write({'request_approval': True})
            kwargs['attachment_ids'] = self.env.context.get('attachment_ids')

        res = super(PurchaseOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)
        # TODO find a better way to no create extra attachment
        attachment_id = self.env['ir.attachment'].search([('res_model', '=', 'mail.compose.message'), ('name', '=', f"SA_{self.name}.pdf")])

        if attachment_id:
            attachment_id.unlink()

        return res

    def allow_cancel(self):
        self.allowed_cancel = True

    def allow_confirm(self):
        self.allowed_confirm = True

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


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values,
                                                      po):
        res = super(PurchaseOrderLine, self)._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, company_id, values,
                                                      po)
        if res['name']:
            res['name'] += '\n Uso: ' + values.get('order_use')
        else:
            res['name'] = 'Uso: ' + values.get('order_use')

        return res


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def _prepare_tender_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        description = values.get('product_description_variants')

        if description:
            description += '\n Uso: ' + values.get('order_use')
        else:
            description = 'Uso: ' + values.get('order_use')

        values.update({
            'product_description_variants': description,
        })

        res = super(PurchaseRequisition, self)._prepare_tender_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)

        return res