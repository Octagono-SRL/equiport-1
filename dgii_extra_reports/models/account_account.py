from odoo import fields, models, api


class AccountAccount(models.Model):
    _name = 'account.account'

    is_dividend = fields.Boolean(string="Cuenta de dividendos")
