# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = ['account.payment']

    is_rental_deposit = fields.Boolean(string="Deposito de renta")
    rental_order_id = fields.Many2one(comodel_name='sale.order', string="Orden de alquiler",
                                      domain=[('is_rental_order', '=', True)])
