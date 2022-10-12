# -*- coding: utf-8 -*-
import datetime
import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import xlsxwriter
import base64
from odoo.tools.config import config


# import string

class ReportPartnerAccount(models.TransientModel):
    _name = 'report.partner.account'
    _description = _("Modelo para visualizar el estado de cuentas de los clientes")

    name = fields.Char(string=_('Title'), compute='_compute_rec_name')
    date_from = fields.Date(string=_('From'))
    date_to = fields.Date(string=_('To'), default=fields.Date.today())

    @api.depends('partner_id')
    def _compute_rec_name(self):
        for rec in self:
            rec.name = rec.partner_id.name

    partner_id = fields.Many2one(comodel_name='res.partner', string=_('Customer'), readonly=True)
    credit_limit = fields.Float(string=_("Credit Limit"))
    company_id = fields.Many2one(comodel_name='res.company', default=lambda s: s.env.company)
    currency_id = fields.Many2one(comodel_name='res.currency')
    line_ids = fields.One2many(comodel_name='report.partner.account.line', inverse_name='report_partner_id')
    amount_total = fields.Monetary(string=_('Total'), store=True, readonly=True,
                                   compute='_compute_amount')
    amount_residual = fields.Monetary(string=_('Total Owed'), store=True, readonly=True,
                                      compute='_compute_amount')

    report = fields.Binary(string='Reporte')
    report_name = fields.Char(string='Nombre del Reporte')

    @api.depends('line_ids', 'partner_id')
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('amount_total'))
            rec.amount_residual = sum(rec.line_ids.mapped('amount_residual'))

    def action_document_print(self):
        if len(self.line_ids) > 0:
            return self.env.ref('partner_account_state.report_action_partner_account_state').report_action(self)
        else:
            raise UserError(_("There is not information to process the PDF"))

    def generate_report_file(self, state):
        report = self.env.ref('partner_account_state.report_action_partner_account_state', False)
        pdf = report._render_qweb_pdf(state)[0]
        pdf = base64.b64encode(pdf)
        return pdf

    def get_email_context(self):
        report_binary = self.generate_report_file(self.id)
        attachment_name = "EC_" + self.name
        attachments = self.env['ir.attachment']
        attachment_pdf = self.env['ir.attachment'].create({
            'name': attachment_name + '.pdf',
            'type': 'binary',
            'datas': report_binary,
            'res_model': self.partner_id._name,
            'res_id': self.partner_id.id,
            'mimetype': 'application/pdf'
        })
        attachments += attachment_pdf
        report_xls = self.generate_xlsx_report(get_file=True)
        attachment_xlsx = self.env['ir.attachment'].create({
            'name': report_xls['report_name'],
            'type': 'binary',
            'datas': report_xls['report'],
            'res_model': self.partner_id._name,
            'res_id': self.partner_id.id,
            'mimetype': 'application/pdf'
        })
        attachments += attachment_xlsx
        ir_model_data = self.env['ir.model.data']

        try:
            template_id = \
                ir_model_data.get_object_reference('partner_account_state',
                                                   'email_template_send_partner_account_state')[
                    1]
        except ValueError:
            template_id = False

        ctx = dict(self.env.context or {})

        if template_id:
            self.env['mail.template'].browse(template_id).update({
                'attachment_ids': [(6, 0, attachments.ids)]
            })
        ctx.update({
            'default_model': 'res.partner',
            'active_model': 'res.partner',
            'active_id': self.partner_id.id,
            'default_res_id': self.partner_id.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_light",
            'attachment_ids': attachments.ids,
            'force_email': True,
        })
        return ctx

    def action_send_mail(self):
        ir_model_data = self.env['ir.model.data']
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()

        ctx = self.get_email_context()
        ctx['model_description'] = 'Envio de Estado de Cuenta'
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
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

    @staticmethod
    def split_list(alist, wanted_parts=1):
        length = len(alist)
        return [alist[i * length // wanted_parts: (i + 1) * length // wanted_parts] for i in range(wanted_parts)]

    def split_list_len(self, alist, fix_len=1):
        length = len(alist)
        qty = math.ceil(length / fix_len)
        return self.split_list(alist, qty)

    def generate_xlsx_report(self, get_file=False):
        this = self[0]

        mfl_date = "{0}{1}{2}".format(self.date_to.year, self.date_to.month, self.date_to.day)
        root_path = config.get('data_dir') if config.get('data_dir', False) else '/temp'
        file_path = '{root}/Estado de Cuenta-{date}.xlsx'.format(root=root_path, date=mfl_date)

        workbook = xlsxwriter.Workbook(file_path, {'strings_to_numbers': True})
        worksheet = workbook.add_worksheet()

        # Add a number format for cells with money.
        money = workbook.add_format({'num_format': '$#,##0'})

        # Headers del Excel
        file_header = ['Número de Documento', 'Fecha de Documento', 'NCF', 'Plazo de pago', 'Plazo de pago (Dias)', 'Días Transc.', 'Total',
                       'Pendiente']
        bold = workbook.add_format({'font_size': 14,
                                    'bold': 1,
                                    'bg_color': '#FFF9BA'})

        self.ensure_one()

        # List the alphabet
        # Esto es para graduar las lineas del excel
        # alphabet = ["%s%d" % (l, 1) for l in string.ascii_uppercase]
        date_from = self.date_from if self.date_from else 'N/A'
        date_to = self.date_to

        # Campos de fechas en reporte
        worksheet.write(2, 5, 'Desde:', bold)
        worksheet.write(2, 6, str(date_from))
        worksheet.write(3, 5, 'A la fecha:', bold)
        worksheet.write(3, 6, str(date_to))

        worksheet.write(1, 1, 'Datos del Cliente', bold)

        # Nombre de cliente
        worksheet.write(2, 1, 'Cliente:', bold)
        worksheet.write(2, 2, self.partner_id.name)

        # RNC
        worksheet.write(2, 3, 'RNC:', bold)
        worksheet.write(2, 4, self.partner_id.vat)

        # Dirección
        worksheet.write(3, 1, 'Dirección:', bold)
        worksheet.write(3, 2, '{0}, {1}, {2}'.format(self.partner_id.street, self.partner_id.city,
                                                     self.partner_id.country_id.name))

        for col, header in enumerate(file_header):
            worksheet.write(5, col + 1, str(header), bold)

        lines = self.line_ids

        pos = 0
        for i, line in enumerate(lines):
            pos += 1
            worksheet.write(i + 6, 1, str(line.move_id.name))
            worksheet.write(i + 6, 2, str(line.invoice_date))
            worksheet.write(i + 6, 3, str(line.l10n_do_fiscal_number))
            worksheet.write(i + 6, 4, str(line.invoice_payment_term_id.name))
            worksheet.write(i + 6, 5, str(line.invoice_payment_term_days))
            worksheet.write(i + 6, 6, str(line.trans_days))
            worksheet.write(i + 6, 7, str(line.amount_total), money)
            worksheet.write(i + 6, 8, str(line.amount_residual), money)

        amount_total = sum(lines.mapped('amount_total'))
        amount_residual = sum(lines.mapped('amount_residual'))

        worksheet.write(pos + 6, 6, 'Total Adeudado', bold)
        worksheet.write(pos + 6, 7, amount_total, money)
        worksheet.write(pos + 7, 6, 'Total Pendiente', bold)
        worksheet.write(pos + 7, 8, sum(lines.mapped('amount_residual')), money)
        pos = 0

        workbook.close()

        if get_file:
            return {
                'report_name': file_path.replace('{0}/'.format(root_path), ''),
                'report': base64.b64encode(
                    open(file_path, 'rb').read())
            }
        else:
            this.write({
                'report_name': file_path.replace('{0}/'.format(root_path), ''),
                'report': base64.b64encode(
                    open(file_path, 'rb').read())
            })


class ReportPartnerAccountLine(models.TransientModel):
    _name = 'report.partner.account.line'
    _description = _("Modelo para visualizar las lineas del estado de cuentas de los clientes")
    _order = 'trans_days DESC'

    report_partner_id = fields.Many2one(comodel_name='report.partner.account')
    partner_id = fields.Many2one(related='report_partner_id.partner_id', string=_('Customer'))
    move_id = fields.Many2one(string=_("Document Number"), comodel_name='account.move')
    move_line_id = fields.Many2one(string=_("Account Move Line"), comodel_name='account.move.line')
    invoice_date = fields.Date(compute='compute_date_details', string=_("Document Date"))
    # invoice_date = fields.Date(related='move_id.invoice_date', string=_("Document Date"))
    move_date = fields.Date(related='move_id.date')
    invoice_payment_term_id = fields.Many2one(comodel_name='account.payment.term', compute='compute_date_details',
                                              string=_('Payment Terms'))
    invoice_payment_term_days = fields.Integer(compute='compute_date_details',
                                               string=_('Payment Terms (Days)'))
    # invoice_payment_term_id = fields.Many2one(related='move_id.invoice_payment_term_id')
    trans_days = fields.Integer(compute="_compute_trans_days", string=_("Aging"), store=True)
    # l10n_do_fiscal_number = fields.Char(related='move_id.l10n_do_fiscal_number', string=_("NCF"))
    l10n_do_fiscal_number = fields.Char(compute='compute_ncf_label', string=_("NCF"))
    # amount_total = fields.Monetary(compute='compute_all_amount' related='move_id.amount_total', string=_("Total"))
    amount_total = fields.Monetary(compute='compute_all_amount', string=_("Total"))
    amount_residual = fields.Monetary(compute='compute_all_amount', string=_("Amount Residual"))
    # amount_residual = fields.Monetary(related='move_id.amount_residual', string=_("Amount Residual"))
    currency_id = fields.Many2one(comodel_name='res.currency', compute='compute_currency', string=_("Currency"))
    # currency_id = fields.Many2one(related='move_id.currency_id', string=_("Currency"))
    company_id = fields.Many2one(comodel_name='res.company', default=lambda s: s.env.company)

    @api.depends('move_id', 'move_line_id')
    def compute_all_amount(self):
        # today = fields.Date.context_today(self)
        for rec in self:
            if rec.move_id.is_invoice():
                rec.amount_total = rec.move_id.amount_total
                rec.amount_residual = rec.move_id.amount_residual
            elif not rec.move_id.is_invoice() and rec.move_line_id:
                if rec.currency_id != rec.company_id.currency_id:
                    rec.amount_total = rec.move_line_id.amount_currency
                    rec.amount_residual = rec.move_line_id.amount_residual_currency
                else:
                    rec.amount_total = rec.move_line_id.balance
                    rec.amount_residual = rec.move_line_id.amount_residual
            else:
                rec.amount_total = 0
                rec.amount_residual = 0

    @api.depends('move_id', 'move_line_id')
    def compute_currency(self):
        # today = fields.Date.context_today(self)
        for rec in self:
            if rec.move_id.is_invoice():
                rec.currency_id = rec.move_id.currency_id
            elif not rec.move_id.is_invoice() and rec.move_line_id:
                rec.currency_id = rec.move_line_id.currency_id

    @api.depends('move_id', 'move_line_id')
    def compute_ncf_label(self):
        # today = fields.Date.context_today(self)
        for rec in self:
            if rec.move_id.is_invoice():
                rec.l10n_do_fiscal_number = rec.move_id.l10n_do_fiscal_number
            elif not rec.move_id.is_invoice() and rec.move_line_id:
                rec.l10n_do_fiscal_number = rec.move_line_id.name

    @api.depends('move_id', 'move_line_id')
    def compute_date_details(self):
        # today = fields.Date.context_today(self)
        for rec in self:
            if rec.move_id.is_invoice():
                rec.invoice_date = rec.move_id.invoice_date
                rec.invoice_payment_term_id = rec.move_id.invoice_payment_term_id
                term_line = rec.move_id.invoice_payment_term_id.line_ids.filtered(lambda ptl: ptl.value == 'balance')
                rec.invoice_payment_term_days = term_line[0].days if term_line else 0
            elif not rec.move_id.is_invoice() and rec.move_line_id:
                check_date = rec.move_line_id.date_maturity if rec.move_line_id.date_maturity else rec.move_line_id.date
                term = rec.move_id.invoice_payment_term_id if rec.move_id.invoice_payment_term_id else rec.partner_id.property_payment_term_id
                term_line = term.line_ids.filtered(lambda ptl: ptl.value == 'balance')
                rec.invoice_date = check_date
                rec.invoice_payment_term_id = term
                rec.invoice_payment_term_days = term_line[0].days if term_line else 0

    @api.depends('move_id', 'invoice_date', 'invoice_payment_term_id')
    def _compute_trans_days(self):
        for rec in self:
            rec.trans_days = (datetime.date.today() - (rec.invoice_date or rec.move_date)).days