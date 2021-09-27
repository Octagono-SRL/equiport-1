from odoo import models, api, fields, _
from odoo.exceptions import UserError


class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    last_number = fields.Integer(string="Último número")
    alert_number = fields.Integer(string="Número de alerta")

    def action_set_numbers(self):

        return {
            'name': "Configuración",
            'res_model': 'wizard.alert.document.type',
            'view_mode': 'form',
            'context': {
                'active_id': self.id,
                'default_document_type_id': self.id,
                'default_last_number': self.last_number,
                'default_alert_number': self.alert_number,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }



