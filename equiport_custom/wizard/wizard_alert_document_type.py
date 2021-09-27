from odoo import fields, models, api


class WizardAlertDocumentType(models.TransientModel):
    _name = 'wizard.alert.document.type'
    _description = 'Wizard to set the alert\'s values for the l10n document type'

    last_number = fields.Integer(string="Último número")
    alert_number = fields.Integer(string="Número de alerta")
    document_type_id = fields.Many2one(comodel_name='l10n_latam.document.type', string="Tipo de comprobante")

    def safe_settings(self):
        self.document_type_id.write({
            'last_number': self.last_number,
            'alert_number': self.alert_number
        })
