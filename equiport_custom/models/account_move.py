# -*- coding: utf-8 -*-
import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = ['account.move']

    # region Partner Currency Selection
    @api.onchange('partner_id', 'journal_id')
    def set_partner_currency(self):
        if self.journal_id and self.partner_id:
            if self.journal_id.use_partner_currency:
                if self.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                    if self.partner_id.property_product_pricelist.currency_id:
                        self.currency_id = self.partner_id.property_product_pricelist.currency_id
                else:
                    if self.partner_id.property_purchase_currency_id:
                        self.currency_id = self.partner_id.property_purchase_currency_id

    # endregion

    # region Taxes detail
    positive_amount_tax = fields.Monetary(string='Itbis Acum.', store=True, readonly=True,
                                          compute='_compute_sign_amount_tax')
    negative_amount_tax = fields.Monetary(string='Itbis Ret.', store=True, readonly=True,
                                          compute='_compute_sign_amount_tax')

    @api.depends(
        'amount_tax',
        'amount_by_group',
        'l10n_latam_tax_ids.amount_currency',
        'amount_total',
        'state',
        'currency_id',
        'fiscal_position_id')
    def _compute_sign_amount_tax(self):
        for rec in self:
            positive = 0
            negative = 0
            tax_lines = rec.l10n_latam_tax_ids.filtered(lambda i: i.tax_line_id.tax_group_id.name == "ITBIS")
            if rec.is_inbound(True):
                for line in tax_lines:
                    positive += rec.company_currency_id._convert(line.credit, rec.currency_id, rec.company_id, rec.date)
                    negative += rec.company_currency_id._convert(line.debit, rec.currency_id, rec.company_id, rec.date)
            elif rec.move_type == 'entry' or rec.is_outbound():
                for line in tax_lines:
                    positive += rec.company_currency_id._convert(line.debit, rec.currency_id, rec.company_id, rec.date)
                    negative += rec.company_currency_id._convert(line.credit, rec.currency_id, rec.company_id, rec.date)

            rec.negative_amount_tax = negative
            rec.positive_amount_tax = positive

    # endregion

    # region Document Type Alerts

    document_type_alert = fields.Boolean(
        compute="_compute_document_type_alert")

    @api.depends('journal_id', 'l10n_latam_document_type_id', 'l10n_latam_document_type_id.alert_number')
    def _compute_document_type_alert(self):
        for invoice in self:
            if invoice.is_invoice():
                prefix_code = invoice.l10n_latam_document_type_id.doc_code_prefix
                alert_number = invoice.l10n_latam_document_type_id.alert_number
                if invoice.journal_id.l10n_latam_use_documents and invoice.l10n_latam_document_type_id and \
                        invoice.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                    sequence_number = False
                    if invoice.l10n_do_fiscal_number:
                        sequence_number = False
                        if len(invoice.l10n_do_fiscal_number.split(prefix_code)) > 1:
                            sequence_number = int(invoice.l10n_do_fiscal_number.split(prefix_code)[1])
                    if sequence_number:
                        if sequence_number >= alert_number:
                            invoice.document_type_alert = True
                        else:
                            invoice.document_type_alert = False
                    else:
                        invoice.document_type_alert = False
                else:
                    invoice.document_type_alert = False
            else:
                invoice.document_type_alert = False

    # endregion

    # region Gate Service
    is_gate_service = fields.Boolean(string="Servicio Gate In / Gate Out")

    def action_post(self):
        for inv in self.filtered(lambda m: m.move_type == 'out_refund'):
            if self.user_has_groups("!equiport_custom.group_general_manager,!equiport_custom.group_commercial_manager,!equiport_custom.group_account_manager,!equiport_custom.group_admin_manager"):
                raise ValidationError("No tiene permitido validar este documento, contacte con alguno de los gerentes encargados.")

        for invoice in self.filtered(lambda s: s.is_invoice()):
            prefix_code = invoice.l10n_latam_document_type_id.doc_code_prefix
            last_number = invoice.l10n_latam_document_type_id.last_number
            if invoice.journal_id.l10n_latam_use_documents and invoice.l10n_latam_document_type_id and \
                    invoice.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                sequence_number = False
                if invoice.l10n_do_fiscal_number:
                    sequence_number = False
                    if len(invoice.l10n_do_fiscal_number.split(prefix_code)) > 1:
                        sequence_number = int(invoice.l10n_do_fiscal_number.split(prefix_code)[1])
                if sequence_number:
                    if sequence_number >= last_number:
                        raise ValidationError(
                            "Los comprobantes de este tipo estan agotados. Comuniquese con administración. La confirmacion de facturas de este tipo esta bloqueada")

            # TODO Desabilido Proceso Gate In/Out
            # if invoice.is_gate_service:
            #
            #     storage_rate_service = self.env.ref('equiport_custom.storage_rate_product')
            #
            #     # Borrando lineas a actualizar
            #
            #     storage_rate_lines = invoice.invoice_line_ids.filtered(lambda l: l.product_id == storage_rate_service)
            #     storage_rate_lines.unlink()
            #
            #     # XXXXXXXXXXXXXXXXXXXXXXXX
            #
            #     invoice_lines = []
            #     for inv_line in invoice.invoice_line_ids.filtered(
            #             lambda il: not il.product_id.is_gate_service and il.display_type == False):
            #         if inv_line.storage_rate > 0:
            #             name_string = ""
            #             total_days = 0
            #             for serial in inv_line.reserved_lot_ids:
            #                 start = serial.gate_in_date
            #                 end = serial.gate_out_date or datetime.datetime.now()
            #                 diff = end - start
            #
            #                 name_string += f'{serial.name} - {diff.days} días'
            #                 total_days += diff.days
            #
            #             val = (0, 0, {
            #                 'product_id': storage_rate_service.id,
            #                 'name': f'{inv_line.product_id.name}\n'
            #                         f'seriares: {name_string}',
            #                 'quantity': total_days,
            #                 'price_unit': inv_line.storage_rate,
            #             })
            #             invoice_lines.append(val)
            #
            #     invoice.update({'invoice_line_ids': invoice_lines})

        res = super(AccountMove, self).action_post()

        return res

    # endregion

    # region Invoice flow origin

    flow_origin = fields.Char(string='Generado en', compute='compute_flow_origin', store=True, tracking=True)

    @api.depends('invoice_origin', 'name')
    def compute_flow_origin(self):
        for rec in self:
            if rec.invoice_origin and rec.move_type == 'out_invoice':
                obj_list = list(map(lambda e: e.strip(), rec.invoice_origin.split(',')))
                model_list = []
                SaleOrder = self.env['sale.order']
                SaleSubscription = self.env['sale.subscription']
                RepairOrder = self.env['repair.order']
                if len(obj_list) == 1:
                    obj = obj_list[0]
                    domain = [('name', '=', obj), ('company_id', '=', rec.company_id.id)]
                    sale_order = SaleOrder.search(domain)
                    repair_order = RepairOrder.search(domain)
                    sale_subscription = SaleSubscription.search(
                        [('code', '=', obj), ('company_id', '=', rec.company_id.id)])

                    if sale_order:
                        if sale_order.is_rental_order:
                            rec.flow_origin = "Alquiler"
                        elif sale_order.is_fsm:
                            rec.flow_origin = "Rescate"
                        else:
                            rec.flow_origin = "Ventas"

                    elif repair_order:
                        if repair_order.is_fleet_origin:
                            rec.flow_origin = "Flota"
                        else:
                            rec.flow_origin = "Reparaciones"
                    elif sale_subscription:
                        if sale_subscription.rental_order_id:
                            rec.flow_origin = "Alquiler recurrente"
                        else:
                            rec.flow_origin = "Subscripción"
                    else:
                        rec.flow_origin = "Sin origen"
                else:
                    for obj in obj_list:
                        domain = [('name', '=', obj), ('company_id', '=', rec.company_id.id)]
                        sale_order = SaleOrder.search(domain)
                        repair_order = RepairOrder.search(domain)
                        sale_subscription = SaleSubscription.search(domain)

                        if sale_order:
                            model_list.append(sale_order._name)
                        elif repair_order:
                            model_list.append(repair_order._name)
                        elif sale_subscription:
                            model_list.append(sale_subscription._name)

                    o_list = [True for e in model_list if e == 'sale.order']
                    r_list = [True for e in model_list if e == 'repair.order']
                    s_list = [True for e in model_list if e == 'sale.subscription']
                    if all(o_list) and (len(o_list) == len(model_list)):
                        rec.flow_origin = "Documentos combinados: Ventas"
                    elif all(r_list) and (len(r_list) == len(model_list)):
                        rec.flow_origin = "Documentos combinados: Reparaciones"
                    elif all(s_list) and (len(s_list) == len(model_list)):
                        rec.flow_origin = "Documentos combinados: Subscripciones"
                    else:
                        rec.flow_origin = "Documentos combinados"
            else:
                rec.flow_origin = "Sin origen"

    @api.constrains('invoice_origin')
    def _check_user_group_to_save(self):
        for rec in self:
            if not rec.invoice_origin and self.user_has_groups('!equiport_custom.create_customer_invoices'):
                if rec.move_type == 'out_invoice':
                    raise ValidationError(
                        "No puede crear facturas sin origen, contacte con gerencia y solicite poder realizar esta acción")

    # endregion


class AccountMoveLine(models.Model):
    _inherit = ['account.move.line']

    reserved_lot_ids = fields.Many2many(compute='_get_stock_reserved_lot_ids', comodel_name='stock.production.lot',
                                        relation='invoice_reserved_lot_rel', domain="[('product_id','=',product_id)]",store=True,
                                        copy=False, string="Números de serie")
    # Gate Service
    storage_rate = fields.Float(string="Tasa de estadia")

    booking = fields.Char(string="Número de reserva", compute='compute_gate_info', store=True)
    stamp = fields.Char(string="Sello", compute='compute_gate_info', store=True)
    boat = fields.Char(string="Barco", compute='compute_gate_info', store=True)

    @api.depends('sale_line_ids', 'name', 'move_id.is_gate_service')
    def compute_gate_info(self):
        for rec in self:
            booking_string = ''
            stamp_string = ''
            boat_string = ''
            if rec.move_id.is_gate_service:
                for item in rec.reserved_lot_ids:
                    booking_string += f'{item.booking}/{item.name} \n'
                    stamp_string += f'{item.stamp}/{item.name}\n'
                    boat_string += f'{item.boat}/{item.name}\n'

            rec.booking = booking_string
            rec.stamp = stamp_string
            rec.boat = boat_string

    @api.depends('sale_line_ids', 'name', 'move_id.state', 'move_id.flow_origin')
    def _get_stock_reserved_lot_ids(self):
        for rec in self:
            rec.reserved_lot_ids = [(6, 0, rec.mapped('sale_line_ids.move_ids.lot_ids').ids)]
