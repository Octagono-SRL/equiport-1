from odoo import fields, models, api


class WizardServicePicking(models.TransientModel):
    _name = 'wizard.service.picking'
    _description = 'Wizard Service Picking'

    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string="Orden de compra")
    order_service_flag_ids = fields.Many2many('product.product', 'order_service_flag_ids',
                                              compute='compute_service_order_ids')
    service_order_ids = fields.Many2many(comodel_name='product.product', relation='service_order_rel',
                                         domain="[('type', '=', 'service'), ('id', 'in', order_service_flag_ids)]",
                                         string="Servicios de orden")
    note = fields.Text('Notas')
    user_id = fields.Many2one(
        'res.users', 'Responsable',
        domain=lambda self: [('groups_id', 'in', self.env.ref('stock.group_stock_user').id)],
        default=lambda self: self.env.user)

    @api.depends('purchase_order_id')
    def compute_service_order_ids(self):
        for rec in self:
            if rec.purchase_order_id:
                rec.order_service_flag_ids = [(6, 0, rec.purchase_order_id.order_line.filtered(lambda l: l.product_uom_qty != l.qty_received).mapped('product_id').ids)]
            else:
                rec.order_service_flag_ids = []

    def action_create_service_picking(self):
        if self.purchase_order_id:
            order_id = self.purchase_order_id
            move_lines = []
            for line in order_id.order_line.filtered(
                    lambda l: l.product_id.type == 'service' and l.product_id in self.service_order_ids):
                move_lines.append((0, 0, {
                    'purchase_order_line_id': line.id,
                    'product_id': line.product_id.id,
                    'name': 'Recepción de servicio {0}'.format(line.product_id.name),
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'description_picking': line.name,
                    'create_date': fields.Datetime.now(),
                }))
            picking = self.env['stock.service.picking'].create({
                'name': '/',
                'partner_id': order_id.partner_id.id,
                'move_lines': move_lines,
                'purchase_order_id': order_id.id,
                'origin': order_id.name,
                'note': self.note,
                'user_id': self.user_id.id if self.user_id else False,
                'date': fields.Datetime.now(),
                'state': 'draft',
            })
            order_id.service_picking_ids += picking
