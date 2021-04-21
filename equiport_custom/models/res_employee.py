# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    tool_ids = fields.One2many(comodel_name='product.template', inverse_name='assign_user_id')
