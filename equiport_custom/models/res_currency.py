# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Currency(models.Model):
    _inherit = 'res.currency'

    currency_rate = fields.Float('Tasa de Registro', compute='_get_currency_rate', digits=(10, 2), readonly=True, store=True)

    @api.depends('rate', 'rate_ids.rate')
    def _get_currency_rate(self):
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = self._get_rates(company, date)
        for currency in self:
            currency.currency_rate = (1 / (currency_rates.get(currency.id) or 1.0))