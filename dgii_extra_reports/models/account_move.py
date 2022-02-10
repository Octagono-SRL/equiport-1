from odoo import fields, models, api


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

