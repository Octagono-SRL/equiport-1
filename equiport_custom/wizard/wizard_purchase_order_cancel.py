# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PurchaseOrderCancel(models.TransientModel):
    _name = 'wizard.purchase.order.cancel'
    _description = "Modelo para cancelar las ordenes de compra"

    reason = fields.Selection([
        ('supplier_no_fulfill', 'El suplidor no cumplió con una o varias de las especificaciones del pedido'),
        ('no_need', 'Los materiales ya no son necesarios'),
        ('order_has_errors', 'Se realizó una orden con error identificado luego de la impresión'),
        ('change_info', 'Cambios en la informacion de la orden'),
    ], string="Razón de cancelacion", default=lambda s: s._context.get('cancel_reason'))
    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string="Orden de compra",
                                        default=lambda s: s._context.get('order_id'))
    user_id = fields.Many2one(comodel_name='res.users', string="Solicitante de permiso",
                              default=lambda s: s._context.get('user_id'))

    def send_cancel_request(self):
        report_binary = self.purchase_order_id.generate_report_file(self.purchase_order_id.id)
        attachment_name = "SC_" + self.purchase_order_id.name
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
            template_id = ir_model_data.get_object_reference('equiport_custom', 'email_template_request_purchase_order_cancel')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'active_model': 'purchase.order',
            'active_id': self.purchase_order_id.id,
            'default_res_id': self.purchase_order_id.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'mark_request_cancel': True,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
        })

        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        ctx['model_description'] = 'Solicitud de aprobación de cancelación'

        if template_id:
            self.env['mail.template'].browse(template_id).update({
                'attachment_ids': [(6, 0, [attachment_id.id])]
            })

        self.purchase_order_id.cancel_reason = self.reason

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

        # print(self.user_id, self.purchase_order_id)
        # pass
