# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = ['account.account']

    to_deposit = fields.Boolean(string="Para deposito")