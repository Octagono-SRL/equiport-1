# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    opportunity_id = fields.Many2one(comodel_name='crm.lead', string="Oportunidad")