from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_stock_location_ids = fields.Many2many(string="Ubicaciones permitidas", comodel_name='stock.location', relation='user_allowed_stock_location_rel')
    allowed_stock_warehouse_ids = fields.Many2many(string="Almacenes permitidos", comodel_name='stock.warehouse', relation='user_allowed_stock_warehouse_rel')

    def clear_user_groups(self):
        if self == self.env.ref('base.user_admin') or self == self.env.user:
            raise ValidationError("No puede realizar esta accion en el usuario logueado")
        elif self.has_group('base.group_system') or self.has_group('base.group_erp_manager'):
            raise ValidationError("No puede realizar esta accion en usuarios admin")
        else:
            self.update({
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
            })

