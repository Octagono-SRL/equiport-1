# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    repair_quotation_count = fields.Integer(
        compute="_compute_repair_count", string="Número de cotizaciones de reparación")
    repair_amount_total = fields.Monetary(
        compute='_compute_repair_count', string="Suma de ordenes de reparación",
        help="Total sin impuesto de ordenes confirmadas", currency_field='company_currency')
    repair_order_count = fields.Integer(
        compute='_compute_repair_count', string="Número de ordenes de reparación")
    repair_order_ids = fields.One2many(
        "repair.order", "opportunity_id", string="Ordenes de reparación")

    def unlink(self):
        if not self.env.user.has_group('equiport_custom.allowed_to_delete_leads'):
            raise ValidationError("No tiene permisos para realizar esta acción.")
        res = super(CrmLead, self).unlink()
        return res

    def _compute_repair_count(self):
        for lead in self:
            total = 0.0
            company_currency = lead.company_currency or self.env.company.currency_id
            repair_orders = lead.repair_order_ids.filtered(lambda l: l.state == 'confirmed')
            for order in repair_orders:
                total += order.currency_id._convert(
                    order.amount_untaxed, company_currency, order.company_id, order.create_date or fields.Date.today())
            lead.repair_quotation_count = len(lead.repair_order_ids.filtered(lambda l: l.state in ["draft", "confirmed"]))
            lead.repair_order_count = len(repair_orders)
            lead.repair_amount_total = total

    def action_repair_quotations_new(self):
        if not self.partner_id:
            raise UserError(_("Please select or create a customer before creating a quote."))
        return self.action_new_repair_quotation()

    def _get_action_repair_context(self):
        return {
            "search_default_opportunity_id": self.id,
            "default_opportunity_id": self.id,
            "search_default_partner_id": self.partner_id.id,
            "default_partner_id": self.partner_id.id,
            "default_team_id": self.team_id.id,
            "default_campaign_id": self.campaign_id.id,
            "default_medium_id": self.medium_id.id,
            "default_origin": self.name,
            "default_source_id": self.source_id.id,
            "default_company_id": self.company_id.id or self.env.company.id,
        }

    def action_new_repair_quotation(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Ordenes de reparación"),
            "res_model": "repair.order",
            "view_mode": "form",
            "views": [(self.env.ref("repair.view_repair_order_form").id, "form")],
            "context": self._get_action_repair_context(),
        }

    def action_view_repair_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("repair.action_repair_order_tree")
        action.update({
            'context': self._get_action_repair_context(),
            'domain': [("opportunity_id", "=", self.id)]
        })

        action['domain'].append(("state", "in", ["draft", "confirmed"]))
        orders = self.repair_order_ids.filtered(lambda l: l.state in ("draft", "confirmed"))

        if len(orders) == 1:
            action.update({
                'views': [(self.env.ref("repair.view_repair_order_form").id, "form")],
                'res_id': orders.id,
            })
        return action
