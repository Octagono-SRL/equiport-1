# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockOrderPoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'
    order_use = fields.Char(string="Uso")


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _run_buy(self, procurements):
        for procurement, rule in procurements:
            procurement.values['order_use'] = procurement.values['orderpoint_id'].order_use

        res = super(StockRule, self)._run_buy(procurements)

        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_drive = fields.Char(string="Conductor")
    vat_drive = fields.Char(string="Identificación conductor")
    partner_truck = fields.Char(string="Camión")
    access_granted = fields.Boolean(string="Acceso permitido", tracking=True)
    access_requested = fields.Boolean(string="Acceso Solicitado", tracking=True)

    is_rental = fields.Boolean(string="Proviene de una orden de alquiler", default=False)

    def button_validate(self):
        sale_id = self.sale_id
        if self.picking_type_code == 'outgoing' and sale_id and sale_id.invoice_ids:
            for inv in sale_id.invoice_ids.filtered(lambda i: i.state == 'posted'):
                if inv.payment_state not in ['in_payment', 'paid']:
                    raise ValidationError(f"Posee facturas sin pago, no puede validar este despacho. "
                                          f"Documento de referencia **{inv.name}**.")

        res = super(StockPicking, self).button_validate()
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

    def button_confirm(self):
        self.state = 'done'

    def request_access(self):
        sale_id = self.sale_id
        if self.picking_type_code == 'outgoing' and sale_id:
            if sale_id.partner_id.allowed_credit:
                raise ValidationError(f"El documento de origen no ha sido facturado. "
                                      f"Documento de referencia **{sale_id.name}**.")
            else:
                if len(sale_id.invoice_ids) < 1:
                    raise ValidationError(f"El documento de origen no ha sido facturado. "
                                          f"Documento de referencia **{sale_id.name}**.")
                else:
                    checks = []
                    for inv in sale_id.invoice_ids:
                        if inv.state != 'posted':
                            checks.append(True)
                        else:
                            checks.append(False)
                    if all(checks):
                        raise ValidationError(f"El documento de origen no tiene facturas confirmadas. "
                                              f"Documento de referencia **{sale_id.name}**.")

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
            template_id = ir_model_data.get_object_reference('equiport_custom', 'email_template_request_picking_access')[1]
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

        res = super(StockPicking, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)
        # TODO find a better way to no create extra attachment
        attachment_id = self.env['ir.attachment'].search([('res_model', '=', 'mail.compose.message'), ('name', '=', f"SA_{self.name}.pdf")])

        if attachment_id:
            attachment_id.unlink()

        return res


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_gate_stock = fields.Boolean(string="Almacen Gate In / Gate Out")


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_gate_location = fields.Boolean(string="Ubicacion Gate In / Gate Out")


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    rent_ok = fields.Boolean(related='product_id.rent_ok')

    # Campos relacionados actividad Alquiler
    rent_state = fields.Selection(
        [('available', 'Disponible'), ('to_check', 'Pendiente inspección'), ('to_repair', 'Pendiente mantenimiento'),
         ('to_wash', 'Pendiente lavado')],
        string="Estado", default="available")


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    rent_state = fields.Selection(
        [('available', 'Disponible'), ('to_check', 'Pendiente inspección'), ('to_repair', 'Pendiente mantenimiento'),
         ('to_wash', 'Pendiente lavado')],
        string="Estado")


class StockMove(models.Model):
    _inherit = 'stock.move'

    rent_state = fields.Selection(
        [('available', 'Disponible'), ('to_check', 'Pendiente inspección'), ('to_repair', 'Pendiente mantenimiento'),
         ('to_wash', 'Pendiente lavado')],
        string="Estado")