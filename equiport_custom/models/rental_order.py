# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    access_granted = fields.Boolean(string="Acceso permitido", tracking=True)
    access_requested = fields.Boolean(string="Acceso Solicitado", tracking=True)

    def get_responsible(self):
        partners = self.env['res.partner']
        for user in self.company_id.user_rental_access:
            if user.partner_id.email:
                partners += user.partner_id
            else:
                raise ValidationError(f"El usuario {user.name} no cuenta con un correo electrónico en su contacto.")
        if partners:
            return str(partners.ids).replace('[', '').replace(']', '')
        else:
            raise ValidationError("No se encontró personal asignado para autorizar esta operación.")

    def generate_report_file(self, rental_id):
        report = self.env.ref('sale.action_report_saleorder', False)
        pdf = report._render_qweb_pdf(rental_id)[0]
        pdf = base64.b64encode(pdf)
        return pdf

    def grant_access(self):
        self.access_granted = True

    def request_access(self):

        report_binary = self.generate_report_file(self.id)
        attachment_name = "SA_rental_" + self.name
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
            template_id = ir_model_data.get_object_reference('equiport_custom', 'email_template_request_rental_pickup')[1]
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
        if self.env.context.get('mark_requested_access'):
            self.write({'access_requested': True})
            kwargs['attachment_ids'] = self.env.context.get('attachment_ids')

        res = super(SaleOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)
        # TODO find a better way to no create extra attachment
        attachment_id = self.env['ir.attachment'].search([('res_model', '=', 'mail.compose.message'), ('name', '=', f"SA_rental_{self.name}.pdf")])

        if attachment_id:
            attachment_id.unlink()

        return res

    @api.model
    def create(self, vals):
        if 'is_rental_order' in vals:
            if vals['is_rental_order']:
                partner_id = self.env['res.partner'].browse(vals['partner_id'])
                if not partner_id.allowed_rental:
                    if not partner_id.commercial_register or not partner_id.leasing_contract:
                        raise ValidationError("El contacto no tiene los documentos necesarios para continuar.")

        return super(SaleOrder, self).create(vals)

    def write(self, values):
        if self.is_rental_order:
            if 'partner_id' in values:
                partner_id = self.env['res.partner'].browse(values['partner_id'])
                if not partner_id.allowed_rental:
                    if not partner_id.commercial_register or not partner_id.leasing_contract:
                        raise ValidationError("El contacto no tiene los documentos necesarios para continuar.")

        res = super(SaleOrder, self).write(values)

        return res

    def _get_order_notification(self):
        self.ensure_one()
        order = self.id
        if order:
            action = self.env.ref('sale_renting.rental_order_action')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'The following replenishment order has been generated',
                    'message': '%s',
                    # 'links': [{
                    #     'label': order.display_name,
                    #     'url': f'#action={action.id}&id={order.id}&model=sale.order',
                    # }],
                    'sticky': False,
                    'type': 'success',  # warning and error for now
                }
            }
        return False

    @api.onchange('partner_id')
    def check_rent_documents(self):
        if self.is_rental_order:
            if self.partner_id and not self.partner_id.allowed_rental:
                if not self.partner_id.commercial_register and not self.partner_id.leasing_contract:
                    return {'value': {}, 'warning': {'title': 'Contacto sin documentos',
                                                     'message': 'El contacto seleccionado no posee los siguientes documentos: '
                                                                '\n**Contrato de arrendamiento**\n'
                                                                '**Registro mercantil**'}}
                elif not self.partner_id.commercial_register:
                    return {'value': {}, 'warning': {'title': 'Contacto sin documentos',
                                                     'message': 'El contacto seleccionado no posee los siguientes documentos: '
                                                                '\n**Registro mercantil**'}}
                elif not self.partner_id.leasing_contract:
                    return {'value': {}, 'warning': {'title': 'Contacto sin documentos',
                                                     'message': 'El contacto seleccionado no posee los siguientes documentos: '
                                                                '\n**Contrato de arrendamiento**'}}

    def open_pickup(self):
        if not self.access_granted:
            self = self.with_company(self.company_id)
            deposit_product = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
            partner = self.partner_id
            if partner.allowed_credit:
                user_id = self.env['res.users'].search([
                    ('partner_id', '=', partner.id)], limit=1)
                if user_id and not user_id.has_group('base.group_portal') or not \
                        user_id:

                    confirm_sale_order = self.search([('partner_id', '=', partner.id),
                                                      ('state', '=', 'sale'),
                                                      ('id', '!=', self.id)])
                    amount_total = 0.0
                    for sale in confirm_sale_order.filtered(lambda s: len(s.invoice_ids) < 1 or s.invoice_ids.filtered(
                            lambda inv: inv.payment_state not in ['in_payment', 'paid'])):
                        amount_total += sale.amount_total
                    if amount_total + self.amount_total > partner.credit_limit:
                        if not partner.over_credit:
                            msg = 'El crédito disponible' \
                                  ' Monto = %s \nVerifique "%s" Cuentas o Limites de ' \
                                  'Crédito.' % (partner.credit_limit,
                                                self.partner_id.name)
                            raise UserError('No se puede despachar '
                                            'Orden. \n' + msg)
            elif deposit_product:
                deposit_product = self.env['product.product'].browse(int(deposit_product))
                verification_list = [(inv.payment_state in ['paid', 'in_payment']) for inv in self.invoice_ids if
                            inv.invoice_line_ids.filtered(lambda l: l.product_id == deposit_product)]
                if not any(verification_list):
                    raise ValidationError("No se puede despachar sin depósito o pago registrado.")

            if len(self.invoice_ids) >= 0:
                if not self.invoice_ids.filtered(lambda inv: inv.payment_state in ['paid', 'in_payment']):
                    raise ValidationError("No se puede despachar sin depósito o pago registrado.")

        res = super(SaleOrder, self).open_pickup()
        return res
