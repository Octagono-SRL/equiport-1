from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def reverse_moves(self):
        if self.refund_method in ['cancel', 'modify']:
            if self.user_has_groups(
                    "!equiport_custom.group_general_manager,!equiport_custom.group_commercial_manager,!equiport_custom.group_account_manager,!equiport_custom.group_admin_manager"):
                raise ValidationError(
                    "No tiene permitido proceder con esta opción, contacte con alguno de los gerentes encargados.")
        res = super(AccountMoveReversal, self).reverse_moves()
        return res
