# -*- coding: utf-8 -*-
import base64
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class RentalOrder(models.Model):
    _inherit = 'sale.order'

    access_granted = fields.Boolean(string="Acceso permitido", tracking=True)
    access_requested = fields.Boolean(string="Acceso Solicitado", tracking=True)
    deposit_status = fields.Selection([('added', 'Agregado'), ('returned', 'Devuelto')], string="Estado de deposito")
    payment_ids = fields.One2many('account.payment', 'rental_order_id', string="Depositos")
    rental_subscription_id = fields.Many2one(comodel_name='sale.subscription', string="Suscripción")
    rental_template_id = fields.Many2one(comodel_name='sale.subscription.template', string="Plantilla de suscripción")
    rental_sub_state = fields.Selection(related='rental_subscription_id.stage_id.category')
    is_inventory_user = fields.Boolean(compute='_compute_inventory_flag', store=False)
    x_css = fields.Html(
        string='CSS',
        sanitize=False,
        compute='_compute_inventory_flag',
        store=False,
    )

    def _compute_inventory_flag(self):
        for rec in self:
            rec.x_css = False
            rec.is_inventory_user = False
            # TODO Habilitar la parte de abajo una vez se termine el proceso de prueba
            # if self.env.user.has_group('equiport_custom.rental_stock_picking'):
            #     rec.is_inventory_user = True
            #     rec.x_css = '<style>.o_form_button_edit, .oe_subtotal_footer, .o_form_button_create, .btn-secondary, .o-discussion {display: none !important;}</style>'
            # else:
            #     rec.is_inventory_user = False
            #     rec.x_css = False

    def update_existing_rental_subscriptions(self):
        """
        Update subscriptions already linked to the order by updating or creating lines.

        :rtype: list(integer)
        :return: ids of modified subscriptions
        """
        for order in self:
            lines = self.order_line.filtered(lambda l: l.product_id.rent_ok)
            subscription = order.rental_subscription_id
            if lines:
                subscription.recurring_invoice_line_ids.unlink()
                # Asignando lineas de subcripcion
                # sub_lines = lines._prepare_subscription_line_data()
                recurring_lines = []
                for rent_line in lines:
                    # Actualizando descripciones
                    actual_desc = rent_line.name
                    if rent_line.product_id.type == 'product':
                        desc_list = actual_desc.split(rent_line.get_rental_order_line_description() or ' ')
                        if len(desc_list) == 2 and desc_list[1] == '':
                            rent_line.name = desc_list[0]

                    recurring_lines.append((0, False, {
                        'rental_order_line_id': rent_line.id,
                        'product_id': rent_line.product_id.id,
                        'name': rent_line.name,
                        'quantity': rent_line.product_uom_qty,
                        'uom_id': rent_line.product_uom.id,
                        'price_unit': rent_line.price_unit,
                        'discount': rent_line.discount if rent_line.order_id.subscription_management != 'upsell' else False,
                    }))

                subscription.sudo().write({
                    'recurring_invoice_line_ids': recurring_lines,
                })

                # Asignando fecha de subcripcion
                for line in lines:
                    use_time = line.return_date.time() if line.return_date else datetime.datetime.now().time()
                    next_date = datetime.datetime.combine(subscription.recurring_next_date, use_time)
                    line.write({
                        'return_date': next_date,
                    })
                    line.product_id_change()
                    # actualizando lineas de subscripcion
                    sub_line = subscription.recurring_invoice_line_ids.filtered(
                        lambda l: l.rental_order_line_id == line
                    )
                    if sub_line:
                        if line.new_rental_addition and (line.start_rent_price > 0) and not line.new_rental_added:
                            sub_line[0].price_unit = line.start_rent_price
                            line.new_rental_added = True
                        sub_line[0].name = line.name
                        sub_line[0].quantity = line.product_uom_qty

    def create_rental_subscriptions(self):

        """
        Create subscriptions based on the products' subscription template.

        Create subscriptions based on the templates found on order lines' products. Note that only
        lines not already linked to a subscription are processed; one subscription is created per
        distinct subscription template found.

        :rtype: list(integer)
        :return: ids of newly create subscriptions
        """
        res = []
        for order in self:
            lines = self.order_line.filtered(lambda l: l.product_id.rent_ok)
            # create a subscription for each template with all the necessary lines
            if lines:
                template = self.rental_template_id
                # for template in to_create:
                values = order._prepare_subscription_data(template)
                recurring_lines = []
                for rent_line in lines:
                    recurring_lines.append((0, False, {
                        'rental_order_line_id': rent_line.id,
                        'product_id': rent_line.product_id.id,
                        'name': rent_line.name,
                        'quantity': rent_line.product_uom_qty,
                        'uom_id': rent_line.product_uom.id,
                        'price_unit': rent_line.price_unit,
                        'discount': rent_line.discount if rent_line.order_id.subscription_management != 'upsell' else False,
                    }))

                values['recurring_invoice_line_ids'] = recurring_lines
                # values['recurring_invoice_line_ids'] = lines._prepare_subscription_line_data()
                subscription = self.env['sale.subscription'].sudo().create(values)
                subscription.onchange_date_start()
                subscription.rental_order_id = order.id
                order.rental_subscription_id = subscription.id
                res.append(subscription.id)
                lines.write({
                    'subscription_id': subscription.id
                })
                # Asignando fecha de subcripcion
                for line in lines:
                    use_time = line.return_date.time() if line.return_date else datetime.datetime.now().time()
                    next_date = datetime.datetime.combine(subscription.recurring_next_date, use_time)
                    line.write({
                        'return_date': next_date,
                    })
                    line.product_id_change()
                    # actualizando lineas de subscripcion
                    sub_line = subscription.recurring_invoice_line_ids.filtered(
                        lambda l: l.rental_order_line_id == line
                    )
                    if sub_line:
                        sub_line[0].name = line.name
                        sub_line[0].quantity = line.product_uom_qty

                subscription.message_post_with_view(
                    'mail.message_origin_link', values={'self': subscription, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id, author_id=self.env.user.partner_id.id
                )
                self.env['sale.subscription.log'].sudo().create({
                    'subscription_id': subscription.id,
                    'event_date': fields.Date.context_today(self),
                    'event_type': '0_creation',
                    'amount_signed': subscription.recurring_monthly,
                    'recurring_monthly': subscription.recurring_monthly,
                    'currency_id': subscription.currency_id.id,
                    'category': subscription.stage_category,
                    'user_id': order.user_id.id,
                    'team_id': order.team_id.id,
                })
        return res

    def action_confirm(self):
        if self.is_rental_order and self.rental_template_id:
            if not self.rental_subscription_id:
                self.create_rental_subscriptions()

        if self.is_rental_order:
            if not self.partner_id.allowed_rental:
                if not self.partner_id.commercial_register or not self.partner_id.leasing_contract:
                    raise ValidationError("El contacto no tiene los documentos necesarios para continuar.")
        res = super(RentalOrder, self).action_confirm()
        return res

    def action_cancel(self):
        if self.is_rental_order:
            if len(self.picking_ids) > 0:
                outgoing_ids = self.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
                for p_out in outgoing_ids:
                    if p_out.state == 'done':
                        raise ValidationError("No es posible cancelar un Alquiler con unidades entregadas")
                    else:
                        p_out.action_cancel()

                # incoming_ids = self.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')
            if self.rental_subscription_id:
                self.rental_subscription_id.set_close()
                self.rental_subscription_id = False
            if self.rental_subscription_id or self.subscription_count > 0:
                for line in self.order_line:
                    line.subscription_id = False
        res = super(RentalOrder, self).action_cancel()
        return res

    # def action_draft(self):
    #     if self.is_rental_order:
    #         for line in self.order_line:
    #             line.subscription_id = False
    #     res = super(RentalOrder, self).action_draft()
    #     return res

    def action_view_deposits(self):
        payments = self.payment_ids
        self.ensure_one()

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })

        return action

    def add_deposit(self):
        # self.deposit_status = 'added'

        return {
            'name': _('Register Payment'),
            'res_model': 'rental.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'sale.order',
                'active_ids': self.ids,
                'payment_type': 'inbound',
                'deposit_status': 'added',
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def remove_deposit(self):
        if self.rental_status not in ['returned', 'cancel']:
            raise ValidationError(
                "No puede devolverse el deposito hasta que se retorne la unidad. O cancelada la orden de alquiler.")
        if len(self.picking_ids) > 0:
            for picking in self.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming'):
                if picking.state != 'done':
                    raise ValidationError(
                        "No puede devolverse el deposito hasta confirmarse la entrega.")

        return {
            'name': _('Register Payment'),
            'res_model': 'rental.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'sale.order',
                'active_ids': self.ids,
                'payment_type': 'outbound',
                'deposit_status': 'returned',
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
        # self.deposit_status = 'returned'

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
            template_id = ir_model_data.get_object_reference('equiport_custom', 'email_template_request_rental_pickup')[
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

        res = super(RentalOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)
        # TODO find a better way to no create extra attachment
        attachment_id = self.env['ir.attachment'].search(
            [('res_model', '=', 'mail.compose.message'), ('name', '=', f"SA_rental_{self.name}.pdf")])

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

        return super(RentalOrder, self).create(vals)

    def write(self, values):
        if self.is_rental_order:
            if 'partner_id' in values:
                partner_id = self.env['res.partner'].browse(values['partner_id'])
                if not partner_id.allowed_rental:
                    if not partner_id.commercial_register or not partner_id.leasing_contract:
                        raise ValidationError("El contacto no tiene los documentos necesarios para continuar.")

        res = super(RentalOrder, self).write(values)

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
            if not self.rental_subscription_id:
                self.rental_template_id = self.env.ref('sale_subscription.monthly_subscription').id
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
        if not self.env.user.has_group('equiport_custom.rental_stock_picking'):
            raise ValidationError("El personal de despacho es el encargado de seleccionar las unidades a despachar")
        if not self.access_granted:
            self = self.with_company(self.company_id)
            deposit_product = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
            partner = self.partner_id
            deposit_status = self.deposit_status
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

            elif deposit_status != 'added' or len(self.invoice_ids) >= 0:

                if not self.payment_ids.filtered(
                        lambda pay: pay.is_rental_deposit and pay.payment_type == 'inbound' and pay.state == 'posted'):
                    raise ValidationError("No se puede despachar sin depósito o pago sin registrar.")
                elif len(self.invoice_ids) > 0:
                    deposit_product = self.env['product.product'].browse(int(deposit_product))
                    verification_list = [(inv.payment_state in ['paid', 'in_payment']) for inv in self.invoice_ids if
                                         inv.invoice_line_ids.filtered(lambda l: l.product_id == deposit_product)]

                    if len(verification_list) > 0 and not any(verification_list):
                        raise ValidationError("No se puede despachar con factura de depósito sin pagar.")

                    if not self.invoice_ids.filtered(lambda inv: inv.payment_state in ['paid', 'in_payment']):
                        raise ValidationError("No se puede despachar con facturas sin pagar.")

        res = super(RentalOrder, self).open_pickup()
        return res


class RentalOrderLine(models.Model):
    _inherit = ['sale.order.line']

    new_rental_addition = fields.Boolean(string="Adición a renta", compute='_check_rental_lines', copy=False)
    new_rental_added = fields.Boolean(string="Agregado", copy=False)
    start_rent_price = fields.Float(string="Cargo inicial")

    @api.onchange('name')
    def set_domain_for_rental_product(self):
        res = {}
        domain = [('sale_ok', '=', True), '|', ('company_id', '=', False),
                  ('company_id', '=', self.order_id.company_id)]
        rent_domain = [('rent_ok', '=', True), '|', ('company_id', '=', False),
                       ('company_id', '=', self.order_id.company_id)]
        if self.order_id.is_rental_order:
            res['domain'] = {'product_id': rent_domain}
        else:
            res['domain'] = {'product_id': domain}
        return res

    @api.depends('product_id', 'create_date')
    def _check_rental_lines(self):
        for rec in self:
            if rec.order_id.is_rental_order and rec.order_id.rental_subscription_id:

                if rec.create_date:
                    if rec.order_id.create_date <= rec.create_date <= rec.order_id.rental_subscription_id.create_date:
                        rec.new_rental_addition = False
                    else:
                        rec.new_rental_addition = True
                else:
                    rec.new_rental_addition = False
            else:
                rec.new_rental_addition = False
