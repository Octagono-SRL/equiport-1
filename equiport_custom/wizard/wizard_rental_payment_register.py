# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RentalPaymentRegister(models.TransientModel):
    _name = 'rental.payment.register'
    _description = 'Wizard para registro de depositos en alquileres'

    # == Business fields ==
    payment_date = fields.Date(string="Fecha de pago", required=True,
                               default=fields.Date.context_today)
    amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,
                             compute='_compute_amount', string="Monto")
    # amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,
    #                          string="Monto")
    communication = fields.Text(string="Detalles de pago", store=True, readonly=False,
                                compute='_compute_communication')
    # group_payment = fields.Boolean(string="Group Payments", store=True, readonly=False,
    #     compute='_compute_group_payment',
    #     help="Only one payment will be created by partner (bank)/ currency.")
    currency_id = fields.Many2one('res.currency', string='Moneda', store=True, readonly=False,
                                  compute='_compute_currency_id',
                                  help="Moneda del pago.")
    journal_id = fields.Many2one('account.journal', store=True, readonly=False, string="Diario",
                                 compute='_compute_journal_id',
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")
    partner_bank_id = fields.Many2one('res.partner.bank', string="Cuenta bancaria del destinatario",
                                      readonly=False, store=True,
                                      compute='_compute_partner_bank_id',
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('partner_id', '=', partner_id)]")
    company_currency_id = fields.Many2one('res.currency', string="Moneda de la compa??ia",
                                          related='company_id.currency_id')

    # == Fields given through the context ==
    order_id = fields.Many2one('sale.order', 'Orden de origen')
    line_ids = fields.Many2many('sale.order.line', 'account_payment_register_rental_order_line_rel', 'wizard_id',
                                'line_id',
                                string="Elememtos de Renta", readonly=True, copy=False, )
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Tipo de pago', store=True, copy=False,
        compute='_compute_from_lines')
    # p_type = fields.Char(string="Tipo")
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], store=True, copy=False,
        compute='_compute_from_lines')
    source_amount = fields.Monetary(
        string="Cantidad a pagar (Moneda de la compa??ia)", store=True, copy=False,
        currency_field='company_currency_id',
        compute='_compute_from_lines')
    source_amount_currency = fields.Monetary(
        string="Cantidad a pagar (Moneda extranjera)", store=True, copy=False,
        currency_field='source_currency_id',
        compute='_compute_from_lines')
    source_currency_id = fields.Many2one('res.currency',
                                         string='Moneda de origen', store=True, copy=False,
                                         compute='_compute_from_lines',
                                         help="Moneda del pago.")
    # can_edit_wizard = fields.Boolean(store=True, copy=False,
    #     compute='_compute_from_lines',
    #     help="Technical field used to indicate the user can edit the wizard content such as the amount.")
    # can_group_payments = fields.Boolean(store=True, copy=False,
    #     compute='_compute_from_lines',
    #     help="Technical field used to indicate the user can see the 'group_payments' box.")
    company_id = fields.Many2one('res.company', store=True, copy=False)
    partner_id = fields.Many2one('res.partner',
                                 string="Cliente", store=True, copy=False, ondelete='restrict')

    # == Payment methods fields ==
    payment_method_id = fields.Many2one('account.payment.method', string='Metodo de pago',
                                        readonly=False, store=True,
                                        compute='_compute_payment_method_id',
                                        domain="[('id', 'in', available_payment_method_ids)]",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    available_payment_method_ids = fields.Many2many('account.payment.method',
                                                    compute='_compute_payment_method_fields')
    hide_payment_method = fields.Boolean(
        compute='_compute_payment_method_fields',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")

    # == Payment difference fields ==
    # payment_difference = fields.Monetary(
    #     compute='_compute_payment_difference')
    # payment_difference_handling = fields.Selection([
    #     ('open', 'Keep open'),
    #     ('reconcile', 'Mark as fully paid'),
    # ], default='open', string="Payment Difference Handling")
    # writeoff_account_id = fields.Many2one('account.account', string="Difference Account", copy=False,
    #                                       domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    # writeoff_label = fields.Char(string='Journal Item Label', default='Write-Off',
    #                              help='Change label of the counterpart that will hold the payment difference')

    # == Display purpose fields ==
    show_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank',
        help="Technical field used to know whether the field `partner_bank_id` needs to be displayed or not in the payments form views")
    require_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank',
        help="Technical field used to know whether the field `partner_bank_id` needs to be required or not in the payments form views")
    country_code = fields.Char(related='company_id.country_id.code', readonly=True)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_batch_communication(self, batch_result):
        ''' Helper to compute the communication based on the batch.
        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A string representing a communication to be set on payment.
        '''
        return 'Renta: ' + ','.join(label for label in batch_result['lines'].mapped('product_id.name') if label)

    @api.model
    def _get_line_batch_key(self, line):
        ''' Turn the line passed as parameter to a dictionary defining on which way the lines
        will be grouped together.
        :return: A python dictionary.
        '''

        account_id = False

        if self._context.get('payment_type') == 'inbound':
            account_id = self.env.ref('equiport_custom.rental_in_deposit_account')
        elif self._context.get('payment_type') == 'outbound':
            account_id = self.env.ref('equiport_custom.rental_out_deposit_account')

        if account_id:
            account = account_id.id
        else:
            account = False
        return {
            'partner_id': line.order_partner_id.id,
            'account_id': account,
            'currency_id': (line.order_id.currency_id or line.order_id.company_id.currency_id).id,
            'partner_bank_id': False,
            'partner_type': 'supplier',
            'payment_type': self._context.get('payment_type') if self._context.get(
                'payment_type') != False else self.payment_type,
        }

    def _get_batches(self):
        ''' Group the account.move.line linked to the wizard together.
        :return: A list of batches, each one containing:
            * key_values:   The key as a dictionary used to group the journal items together.
            * moves:        An account.move recordset.
        '''
        self.ensure_one()

        lines = self.line_ids._origin

        if len(lines.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if not lines:
            raise UserError(
                _("You can't open the register payment wizard without at least one receivable/payable line."))

        batches = {}
        for line in lines:
            batch_key = self._get_line_batch_key(line)

            serialized_key = '-'.join(str(v) for v in batch_key.values())
            batches.setdefault(serialized_key, {
                'key_values': batch_key,
                'lines': self.env['sale.order.line'],
            })
            batches[serialized_key]['lines'] += line
        return list(batches.values())

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        ''' Extract values from the batch passed as parameter (see '_get_batches')
        to be mounted in the wizard view.
        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A dictionary containing valid fields
        '''
        key_values = batch_result['key_values']
        lines = batch_result['lines']
        company = lines[0].company_id

        source_amount = abs(sum(lines.mapped('price_subtotal')))
        if key_values['currency_id'] == company.currency_id.id:
            source_amount_currency = source_amount
        else:
            source_amount_currency = abs(sum(lines.mapped('price_total')))

        return {
            'company_id': company.id,
            'partner_id': key_values['partner_id'],
            'partner_type': key_values['partner_type'],
            'payment_type': key_values['payment_type'],
            'source_currency_id': key_values['currency_id'],
            'source_amount': source_amount,
            'source_amount_currency': source_amount_currency,
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('line_ids')
    def _compute_from_lines(self):
        ''' Load initial values from the sale.order passed through the context. '''
        for wizard in self:
            batches = wizard._get_batches()
            batch_result = batches[0]
            wizard_values_from_batch = wizard._get_wizard_values_from_batch(batch_result)

            if len(batches) == 1:
                # == Single batch to be mounted on the view ==
                wizard.update(wizard_values_from_batch)

                # wizard.can_edit_wizard = True
                # wizard.can_group_payments = len(batch_result['lines']) != 1
            else:
                # == Multiple batches: The wizard is not editable  ==
                wizard.update({
                    'company_id': batches[0]['lines'][0].company_id.id,
                    'partner_id': False,
                    'partner_type': wizard_values_from_batch['partner_type'],
                    'payment_type': wizard_values_from_batch['payment_type'],
                    'source_currency_id': False,
                    'source_amount': False,
                    'source_amount_currency': False,
                })

                # wizard.can_edit_wizard = False
                # wizard.can_group_payments = any(len(batch_result['lines']) != 1 for batch_result in batches)

    @api.depends('line_ids')
    def _compute_communication(self):
        # The communication can't be computed in '_compute_from_lines' because
        # it's a compute editable field and then, should be computed in a separated method.
        for wizard in self:
            batches = self._get_batches()
            if wizard._get_batch_communication(batches[0]):
                wizard.communication = wizard._get_batch_communication(batches[0])
            else:
                wizard.communication = False

    # @api.depends('can_edit_wizard')
    # def _compute_group_payment(self):
    #     for wizard in self:
    #         if wizard.can_edit_wizard:
    #             batches = wizard._get_batches()
    #             wizard.group_payment = len(batches[0]['lines'].move_id) == 1
    #         else:
    #             wizard.group_payment = False

    @api.depends('company_id')
    def _compute_journal_id(self):
        for wizard in self:
            if not wizard.journal_id:
                domain = [
                    ('type', 'in', ('bank', 'cash')),
                    ('company_id', '=', wizard.company_id.id),
                ]
                journal = None
                if wizard.source_currency_id:
                    journal = self.env['account.journal'].search(
                        domain + [('currency_id', '=', wizard.source_currency_id.id)], limit=1)
                if not journal:
                    journal = self.env['account.journal'].search(domain, limit=1)
                wizard.journal_id = journal

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.journal_id.currency_id or wizard.source_currency_id or wizard.company_id.currency_id

    @api.depends('partner_id')
    def _compute_partner_bank_id(self):
        ''' The default partner_bank_id will be the first available on the partner. '''
        for wizard in self:
            available_partner_bank_accounts = wizard.partner_id.bank_ids
            if available_partner_bank_accounts:
                wizard.partner_bank_id = available_partner_bank_accounts[0]._origin
            else:
                wizard.partner_bank_id = False

    @api.depends('journal_id')
    def _compute_payment_method_id(self):
        for wizard in self:
            batches = wizard._get_batches()
            payment_type = batches[0]['key_values']['payment_type']

            if payment_type == 'inbound':
                available_payment_methods = wizard.journal_id.inbound_payment_method_ids
            else:
                available_payment_methods = wizard.journal_id.outbound_payment_method_ids

            # Select the first available one by default.
            if available_payment_methods:
                wizard.payment_method_id = available_payment_methods[0]._origin
            else:
                wizard.payment_method_id = False

    @api.depends('journal_id.inbound_payment_method_ids',
                 'journal_id.outbound_payment_method_ids')
    def _compute_payment_method_fields(self):
        for wizard in self:
            if wizard._context['payment_type'] == 'inbound':
                wizard.available_payment_method_ids = wizard.journal_id.inbound_payment_method_ids
            else:
                wizard.available_payment_method_ids = wizard.journal_id.outbound_payment_method_ids

            wizard.hide_payment_method = len(
                wizard.available_payment_method_ids) == 1 and wizard.available_payment_method_ids.code == 'manual'

    @api.depends('journal_id.inbound_payment_method_ids',
                 'journal_id.outbound_payment_method_ids')
    def _compute_payment_method_id(self):
        for wizard in self:
            payment_type = self._context.get('payment_type') if self._context.get(
                'payment_type') != False else wizard.payment_type
            if payment_type == 'inbound':
                available_payment_methods = wizard.journal_id.inbound_payment_method_ids
            else:
                available_payment_methods = wizard.journal_id.outbound_payment_method_ids

            # Select the first available one by default.
            if available_payment_methods:
                wizard.payment_method_id = available_payment_methods[0]._origin
            else:
                wizard.payment_method_id = False

    @api.depends('payment_method_id')
    def _compute_show_require_partner_bank(self):
        """ Computes if the destination bank account must be displayed in the payment form view. By default, it
        won't be displayed but some modules might change that, depending on the payment type."""
        for wizard in self:
            wizard.show_partner_bank_account = wizard.payment_method_id.code in self.env[
                'account.payment']._get_method_codes_using_bank_account()
            wizard.require_partner_bank_account = wizard.payment_method_id.code in self.env[
                'account.payment']._get_method_codes_needing_bank_account()

    @api.depends('company_id', 'currency_id', 'payment_date')
    def _compute_amount(self):
        for wizard in self:
            payment_type = self._context.get('payment_type') if self._context.get(
                'payment_type') != False else wizard.payment_type
            if payment_type == 'inbound':
                # pass
                if wizard.source_currency_id == wizard.currency_id:
                    # Same currency.
                    wizard.amount = wizard.source_amount_currency
                elif wizard.currency_id == wizard.company_id.currency_id:
                    # Payment expressed on the company's currency.
                    wizard.amount = wizard.source_amount
                else:
                    # Foreign currency on payment different than the one set on the journal entries.
                    amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount, wizard.currency_id, wizard.company_id, wizard.payment_date)
                    wizard.amount = amount_payment_currency
            elif payment_type == 'outbound':
                deposit = self.env['account.payment'].search(
                    [('is_rental_deposit', '=', True), ('rental_order_id', '=', self._context.get('active_ids')[0]),
                     ('payment_type', '=', 'inbound')])
                if deposit:
                    wizard.amount = deposit[0].amount

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)

        if 'line_ids' in fields_list and 'line_ids' not in res:

            # Retrieve moves to pay from the context.

            if self._context.get('active_model') == 'sale.order':
                lines = self.env['sale.order'].browse(self._context.get('active_ids', [])).order_line
            elif self._context.get('active_model') == 'sale.order.line':
                lines = self.env['sale.order.line'].browse(self._context.get('active_ids', []))
            else:
                raise UserError(_(
                    "The register payment wizard should only be called on sale.order or sale.order.line records."
                ))

            # Keep lines having a residual amount to pay.
            available_lines = self.env['sale.order.line']
            for line in lines:
                if line.order_id.state != 'sale':
                    raise UserError(_("You can only register deposit for sale entries."))

                # if line.account_internal_type not in ('receivable', 'payable'):
                #     continue
                # if line.currency_id:
                #     if line.currency_id.is_zero(line.amount_residual_currency):
                #         continue
                # else:
                if line.company_id.currency_id.is_zero(line.price_total):
                    continue
                available_lines |= line

            # Check.
            if not available_lines:
                raise UserError(
                    _("You can't register a payment because there is nothing left to pay on the selected journal items."))
            if len(lines.company_id) > 1:
                raise UserError(_("You can't create payments for entries belonging to different companies."))
            # if len(set(available_lines.mapped('account_internal_type'))) > 1:
            #     raise UserError(_("You can't register payments for journal items being either all inbound, either all outbound."))

            res['line_ids'] = [(6, 0, available_lines.ids)]
            res['order_id'] = self._context.get('active_ids')[0]
            # res['payment_type'] = self._context.get('payment_type')

        return res

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self):
        # if self.amount > self.order_id.amount_total:
        #     raise UserError("El monto no puede superar el total de la cotizaci??n")

        if self._context.get('payment_type') == 'inbound':
            # account_id = self.env.ref('equiport_custom.rental_in_deposit_account')
            account_id = self.env.ref('equiport_custom.rental_out_deposit_account')
        elif self._context.get('payment_type') == 'outbound':
            account_id = self.env.ref('equiport_custom.rental_out_deposit_account')
            deposit = self.env['account.payment'].search(
                [('is_rental_deposit', '=', True), ('rental_order_id', '=', self._context.get('active_ids')[0]),
                 ('payment_type', '=', 'inbound')])
            if deposit:
                self.amount = deposit[0].amount

        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self._context.get('payment_type') if self._context.get(
                'payment_type') != False else self.payment_type,
            'partner_type': 'supplier',
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'is_rental_deposit': True,
            'rental_order_id': self.order_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_id': self.payment_method_id.id,
            'destination_account_id': account_id.id
        }

        return payment_vals

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        to_reconcile = []
        payment_vals = self._create_payment_vals_from_wizard()
        payment_vals_list = [payment_vals]
        to_reconcile.append(batches[0]['lines'])
        payments = self.env['account.payment'].create(payment_vals_list)

        # region different currency
        # If payments are made using a currency different than the source one, ensure the balance match exactly in
        # order to fully paid the source journal items.
        # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
        # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
        # if edit_mode:
        # payments.partner_type = 'customer'
        # for payment, lines in zip(payments, to_reconcile):
        #     # Batches are made using the same currency so making 'lines.currency_id' is ok.
        #     if payment.currency_id != lines.currency_id:
        #         liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
        #         source_balance = abs(sum(lines.mapped('amount_residual')))
        #         payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
        #         source_balance_converted = abs(source_balance) * payment_rate
        #
        #         # Translate the balance into the payment currency is order to be able to compare them.
        #         # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
        #         # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
        #         # match.
        #         payment_balance = abs(sum(counterpart_lines.mapped('balance')))
        #         payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
        #         if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
        #             continue
        #
        #         delta_balance = source_balance - payment_balance
        #
        #         # Balance are already the same.
        #         if self.company_currency_id.is_zero(delta_balance):
        #             continue
        #
        #         # Fix the balance but make sure to peek the liquidity and counterpart lines first.
        #         debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
        #         credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')
        #
        #         payment.move_id.write({'line_ids': [
        #             (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
        #             (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
        #         ]})
        # endregion

        payments.action_post()

        return payments

    def action_create_payments(self):
        payments = self._create_payments()

        if self._context.get('dont_redirect_to_payments'):
            return True

        if self._context.get('deposit_status'):
            self.order_id.deposit_status = self._context.get('deposit_status')

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
        # self.order_id._get_payment_notification(payments)
        return action
