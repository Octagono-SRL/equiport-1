# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, api, fields
from odoo.exceptions import ValidationError

AVAILABLE_PRIORITIES = [
    ('0', 'Baja'),
    ('1', 'Media'),
    ('2', 'Alta'),
    ('3', 'Muy alta'),
]


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    priority = fields.Selection(
        AVAILABLE_PRIORITIES, string='Prioridad', index=True,
        default=AVAILABLE_PRIORITIES[0][0])

    # region Aprobacion de reposition
    allowed_confirm = fields.Boolean(string="Reposicion aprobada", tracking=True)
    allowed_confirm_sign = fields.Binary(copy=False)
    allowed_confirm_signed_by = fields.Char('Reposicion firmada por',
                                           help='Nombre de la persona que firmo la aprobacion de reposicion.',
                                           copy=False)
    allowed_confirm_date_sign = fields.Datetime(string="Fecha de aprobacion")
    is_confirm_group = fields.Boolean(string="Grupo de aprobacion", compute="_check_confirm_group")

    is_readonly_user = fields.Boolean(compute='_compute_readonly_flag', store=False)
    x_css = fields.Html(
        string='CSS',
        sanitize=False,
        compute='_compute_readonly_flag',
        store=False,
    )

    def _compute_readonly_flag(self):
        for rec in self:
            rec.x_css = False
            rec.is_readonly_user = False
            if self.env.user.has_group('equiport_custom.purchase_requisition_account_user_readonly'):
                rec.is_readonly_user = True
                rec.x_css = '<style>.o_form_button_edit, .o_form_button_create, .oe_subtotal_footer {display: none !important;}</style>'
                rec.x_css += """<script>
                                            var action = document.querySelector(".o_cp_action_menus")?.lastChild
                                            if(action){
                                                action.style.display='none'
                                            }
                                            </script>"""
            else:
                rec.is_readonly_user = False
                rec.x_css = False


    @api.depends('state')
    def _check_confirm_group(self):
        for rec in self:
            if self.env.user in self.env.company.user_pro_allow_confirm or self.env.user.user_has_groups('equiport_custom.group_operations_manager'):
                rec.is_confirm_group = True
            else:
                rec.is_confirm_group = False

    def allow_requisition(self):
        if not self.allowed_confirm_sign:
            raise ValidationError(
                "El documento debe ser firmado, dirijase a la pestaña de firmas.")
        self.allowed_confirm_date_sign = datetime.now()
        self.allowed_confirm_signed_by = self.env.user.display_name
        self.allowed_confirm = True
    # endregion

    def action_in_progress(self):
        if not self.allowed_confirm:
            raise ValidationError("El documento debe ser aprobado por el personal asignado antes de continuar.")
        res = super(PurchaseRequisition, self).action_in_progress()
        return res

    def _prepare_tender_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        description = values.get('product_description_variants')

        if description:
            description += '\n Uso: ' + values.get('order_use')
        else:
            description = 'Uso: ' + values.get('order_use')

        values.update({
            'product_description_variants': description,
        })

        res = super(PurchaseRequisition, self)._prepare_tender_values(product_id, product_qty, product_uom, location_id,
                                                                      name, origin, company_id, values)

        res['priority'] = values.get('priority')

        return res

    def generate_order_comparison(self):

        # Busqueda de las vistas del modelo
        tree_view_id = self.env.ref('equiport_custom.report_order_comparison_tree_view').id

        # Definicion de variables de entorno para el modelo
        model_report_view = self.env['report.order.comparison']

        # Limpiando registros existentes en la tabla visual
        rec_search = model_report_view.search([])
        if len(rec_search) > 0:
            rec_search.unlink()

        # Recolectando y procesando informacion
        model_orders = self.env['purchase.order']
        data = model_orders.search([
            ('origin', '=', self.name)
        ])

        if data:
            partners = list(set(data.mapped('partner_id')))
            products = list(set(data.mapped('order_line').mapped('product_id')))

            for par in partners:
                for prod in products:
                    info = data.order_line.filtered(lambda l: l.product_id == prod and l.partner_id == par)

                    if not info:
                        break

                    model_report_view.create({
                        'partner_id': par.id,
                        'order_id': info.order_id.id,
                        'product_id': prod.id,
                        'price_unit': info.price_unit,
                        'product_qty': info.product_uom_qty,
                        'discount': info.discount,
                        'date_approve': info.order_id.date_approve,
                        'subtotal': info.price_subtotal,
                    })

            action = {'type': 'ir.actions.act_window',
                      'views': [(tree_view_id, 'tree')],
                      'view_mode': 'tree',
                      'name': 'Reporte comparativo',
                      'res_model': 'report.order.comparison',
                      'context': {},
                      }

            return action

        else:
            raise ValidationError("El reporte no puede ser generado. No existen ordenes de compras.")