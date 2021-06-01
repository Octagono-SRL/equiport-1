# # -*- coding: utf-8 -*-
#
# import logging
# import math
# import re
# import time
# import traceback
#
# from odoo import api, fields, models, tools, _
#
#
# class Currency(models.Model):
#     _inherit = ["res.currency"]
#
#     currency_rate = fields.Float('Tasa de Registro', compute='_get_currency_rate', digits=0, readonly=True, store=True)
#
#     def _get_currency_rate(self):
#         date = self._context.get('date') or fields.Date.today()
#         company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
#         # the subquery selects the last rate before 'date' for the given currency/company
#         currency_rates = self._get_rates(company, date)
#         for currency in self:
#             currency.currency_rate = 1 / (currency_rates.get(currency.id) or 1.0)