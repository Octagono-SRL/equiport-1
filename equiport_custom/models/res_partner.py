# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_type = fields.Selection(selection=[('local', 'Local'), ('international', 'Internacional')],
                                    string="Tipo de contacto")

    vat_type = fields.Selection(selection=[('vat_base', 'Cédula'), ('vat_exterior', 'Pasaporte'), ('vat_nif', 'RNC')],
                                default='vat_nif',
                                string="Tipo de Documento")

    leasing_contract = fields.Binary(string="Contrato de arrendamiento")
    commercial_register = fields.Binary(string="Registro mercantil")



