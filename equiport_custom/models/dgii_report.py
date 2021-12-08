from odoo import api, fields, models


class DgiiReports(models.Model):
    _inherit = 'dgii.reports'

    def change_state(self):
        if self.state == 'sent':
            self.state = 'generated'
