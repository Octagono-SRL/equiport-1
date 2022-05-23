from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    defined_fiscal_number = fields.Char(
        "Defined Fiscal Number",
        index=True,
        copy=False,
        help="Stored field equivalent of l10n_do_fiscal_number to maintain number",
    )

    def write(self, values):
        # Add code here
        for rec in self:
            if 'l10n_do_fiscal_number' in values and not rec.defined_fiscal_number:
                values['defined_fiscal_number'] = values.get('l10n_do_fiscal_number')

        res = super(AccountMove, self).write(values)

        for rec in self:
            if rec.l10n_do_fiscal_number != rec.defined_fiscal_number:
                rec.l10n_do_fiscal_number = rec.defined_fiscal_number

        return res

    @api.constrains('name', 'partner_id', 'company_id', 'posted_before', 'defined_fiscal_number', 'l10n_do_fiscal_number',
                    'l10n_latam_document_number')
    def _check_unique_vendor_fiscal_number(self):
        for rec in self.filtered(
                lambda x: x.name and x.name != '/' and x.is_purchase_document() and x.l10n_latam_use_documents):
            domain = [
                ('move_type', '=', rec.move_type),
                # by validating name we validate l10n_latam_document_type_id
                ('partner_id', '=', rec.partner_id.id),
                ('id', '!=', rec.id),
                ('l10n_do_fiscal_number', '=', rec.l10n_latam_document_number),
                ('l10n_do_fiscal_number', 'not in', [False, '']),
                # allow to have to equal if they are cancelled
                ('state', '!=', 'cancel'),
            ]
            if rec.search(domain):
                raise ValidationError('Las facturas de proveedor deben tener un numero unico de NCF por proveedor.\n Detalles:\n {0}'.format(rec.search(domain).mapped('name')))
