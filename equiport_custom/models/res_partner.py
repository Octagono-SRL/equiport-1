# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_type = fields.Selection(selection=[('local', 'Local'), ('international', 'Internacional')],
                                    string="Tipo de contacto")

    vat_type = fields.Selection(selection=[('vat_base', 'Cédula'), ('vat_exterior', 'Pasaporte'), ('vat_nif', 'RNC')],
                                default='vat_nif',
                                string="Tipo de Documento")

    @api.constrains('vat_type', 'vat')
    def _check_existing_vat(self):
        for rec in self:
            search_vat = self.search(
                [('vat', '=', rec.vat), ('vat_type', '=', rec.vat_type), ('vat', 'not in', [False, '']),
                 ('id', 'not in', rec.parent_id.child_ids.ids),
                 ('id', '!=', rec.id), ('id', '!=', rec.parent_id.id), ('id', 'not in', rec.child_ids.ids)])
            if search_vat and len(search_vat) == 1:
                raise ValidationError(
                    "Ya existe un contacto con este numero de identificacion: {0}".format(search_vat.name))
            elif search_vat and len(search_vat) > 1:
                raise ValidationError(
                    "Ya existe contactos con este numero de identificacion: {0}".format(search_vat.mapped('name')))

    # Gate In/Out
    lot_unit_count = fields.Integer(compute="_compute_lot_unit_count", string="Cantidad de unidades")
    lot_unit_ids = fields.One2many(comodel_name='stock.production.lot', inverse_name='owner_partner_id',
                                   string="Unidades")

    @api.depends('lot_unit_ids')
    def _compute_lot_unit_count(self):
        for rec in self:
            rec.lot_unit_count = len(rec.lot_unit_ids)

    # Alquileres
    leasing_contract = fields.Binary(string="Contrato de arrendamiento")
    commercial_register = fields.Binary(string="Registro mercantil")

    allowed_rental = fields.Boolean(default=False)

    # Credito
    allowed_credit = fields.Boolean(string="Permitir crédito", default=False, tracking=True)
    credit_warning = fields.Float(string="Alerta en (%)", default=75, tracking=True)
    over_credit = fields.Boolean(string="Permitir extra crédito", tracking=True)
    date_last_credit = fields.Date(string="Ultima fecha de modificacion de credito", tracking=True,
                                   default=fields.Date.today())

    @api.onchange('credit_limit')
    def update_date_last_credit(self):
        self.update({
            'date_last_credit': fields.Date.today()
        })

    @api.onchange('property_product_pricelist')
    def set_credit_zero(self):
        self.update({
            'credit_limit': 0
        })

    @api.constrains("vat_type", "vat")
    def nif_length_constrain(self):
        for rec in self:
            if rec.vat_type == 'vat_base' and rec.vat and len(rec.vat) != 11:
                raise ValidationError("Verifique la longitud de la Cédula. Deben ser 11 digitos")
            elif rec.vat_type == 'vat_nif' and rec.vat and len(rec.vat) != 9:
                raise ValidationError("Verifique la longitud del RNC. Deben ser 9 digitos")

    def allow_rental(self):
        self.allowed_rental = True

    def block_rental(self):
        self.allowed_rental = False

    def allow_credit(self):
        self.allowed_credit = True

    def block_credit(self):
        self.allowed_credit = False
