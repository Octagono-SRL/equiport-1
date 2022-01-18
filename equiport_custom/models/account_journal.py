from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    use_partner_currency = fields.Boolean(string="Usar la moneda de los contactos")
