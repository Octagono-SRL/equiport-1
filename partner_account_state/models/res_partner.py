from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_view_account_state(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'name': _('Generate Account State'),
            'res_model': 'wizard.generate.account.state',
            'context': {
                'active_id': self.id
            }
        }
