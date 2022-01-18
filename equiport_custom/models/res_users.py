from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_stock_location_ids = fields.Many2many(string="Ubicaciones permitidas", comodel_name='stock.location', relation='user_allowed_stock_location_rel')
    allowed_stock_warehouse_ids = fields.Many2many(string="Almacenes permitidos", comodel_name='stock.warehouse', relation='user_allowed_stock_warehouse_rel')
