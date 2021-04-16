# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def default_get(self, fields_list):

        struct_f_id = self.env.ref('dominican_payroll.structure_permanent_employees').id
        struct_c_id = self.env.ref('dominican_payroll.christmas_salary_structure').id
        struct_ex_id = self.env.ref('dominican_payroll.structure_foreign_employees').id
        employee_rules = self.env['hr.salary.rule'].search([('struct_id', '=', struct_f_id)])
        double_rules = self.env['hr.salary.rule'].search([('struct_id', '=', struct_c_id)])
        foreign_rules = self.env['hr.salary.rule'].search([('struct_id', '=', struct_ex_id)])

        res = super(PayrollStructure, self).default_get(fields_list)
        res['rule_ids'] = []
        rules = []
        if employee_rules:
            rules.extend(employee_rules.ids)
        if foreign_rules:
            rules.extend(foreign_rules.ids)
        if double_rules:
            rules.extend(double_rules.ids)

        res['rule_ids'].append((6, 0, rules))

        return res

