from odoo import fields, models, api
from odoo.exceptions import ValidationError


class StockServicePicking(models.Model):
    _name = 'stock.service.picking'
    _description = 'Service transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    name = fields.Char(
        'Referencia', default='/',
        copy=False, index=True, readonly=True)
    origin = fields.Char(
        'Documento de origen', index=True,
        help="Reference of the document")
    purchase_order_id = fields.Many2one(comodel_name="purchase.order", string="Orden de compra", required=False, )
    note = fields.Text('Notas', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('assigned', 'Asignado'),
        ('done', 'Hecho'),
        ('cancel', 'Cancelado'),
    ], string='Estado',
        copy=False, index=True, readonly=True, store=True, tracking=True)
    date = fields.Datetime(
        'Fecha de creación',
        default=fields.Datetime.now, index=True, tracking=True,
        help="Creation Date, usually the time of the order")
    date_done = fields.Datetime('Fecha efectiva', copy=False, readonly=True,
                                help="Date at which the transfer has been processed or cancelled.")

    move_lines = fields.One2many('stock.service.move', 'service_picking_id', string="Stock Moves", copy=True)

    partner_id = fields.Many2one(
        'res.partner', 'Suplidor',
        check_company=True)
    company_id = fields.Many2one(
        'res.company', string='Compañia', related='purchase_order_id.company_id',
        readonly=True, store=True, index=True)
    user_id = fields.Many2one(
        'res.users', 'Responsable', tracking=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('stock.group_stock_user').id)],
        default=lambda self: self.env.user)

    is_locked = fields.Boolean(default=True, help='When the picking is not done this allows changing the '
                                                  'initial demand. When the picking is done this allows '
                                                  'changing the done quantities.')

    receipt_from = fields.Char(string="Entregó")
    receipt_by = fields.Char(string="Recibió")

    @api.model
    def create(self, vals):
        # To avoid consuming a sequence number when clicking on 'Create', we preprend it if the
        # the name starts with '/'.
        if 'user_id' in vals:
            if vals['user_id'] not in ['', False]:
                vals['state'] = 'assigned'
        vals['name'] = vals.get('name') or '/'
        if vals['name'].startswith('/'):
            vals['name'] = (self.env['ir.sequence'].next_by_code('stock.service.picking') or '/') + vals['name']
            vals['name'] = vals['name'][:-1] if vals['name'].endswith('/') and vals['name'] != '/' else vals['name']
        return super(StockServicePicking, self).create(vals)

    def write(self, values):
        # Add code here
        if 'user_id' in values:
            if values['user_id'] not in ['', False]:
                values['state'] = 'assigned'
        return super(StockServicePicking, self).write(values)

    def button_confirm(self):
        order_id = self.purchase_order_id
        if not order_id:
            return

        for line in self.move_lines:
            line.purchase_order_line_id.qty_received += line.qty_done

        if self.receipt_from and self.receipt_by:
            self.write({
                'state': 'done',
                'date_done': fields.Datetime.now()
            })
        else:
            raise ValidationError("Complete los detalles de recepción en el área de información extra.")

    def action_cancel(self):
        self.write({'is_locked': True, 'state': 'cancel'})

    def action_assign_to_me(self):
        self.write({'user_id': self.env.user.id})


class StockServiceMove(models.Model):
    _name = "stock.service.move"
    _description = "Stock Service Move"
    _order = 'sequence, id'

    name = fields.Char('Descripción', index=True, required=True)
    sequence = fields.Integer('Sequence', default=10)
    create_date = fields.Datetime('Fecha de creación', index=True, readonly=True)
    state = fields.Selection(related='service_picking_id.state', store=True)
    company_id = fields.Many2one(
        'res.company', 'Compañia',
        default=lambda self: self.env.company,
        index=True, required=True)
    service_picking_id = fields.Many2one(comodel_name="stock.service.picking", string="Conduce de servicio", ondelete='cascade')
    purchase_order_line_id = fields.Many2one(comodel_name="purchase.order.line", string="Linea de compra", required=False)
    product_id = fields.Many2one(
        'product.product', 'Producto',
        check_company=True,
        domain="[('type', 'in', ['service']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=True)
    description_picking = fields.Text('Descripción de conduce')
    qty_done = fields.Float('Hecho', default=0.0, digits='Product Unit of Measure', copy=False)
    product_uom_qty = fields.Float(
        'Demanda',
        digits='Product Unit of Measure',
        default=0.0, required=True)
    product_uom = fields.Many2one('uom.uom', 'Unidad de medida', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(string="Categoria", related='product_id.uom_id.category_id', store=True)
    # TDE FIXME: make it stored, otherwise group will not work
    product_tmpl_id = fields.Many2one(
        'product.template', 'Plantilla de producto',
        related='product_id.product_tmpl_id', readonly=False,
        help="Technical: used in views")

    @api.constrains('qty_done', 'product_uom_qty')
    def constraint_qty(self):
        for rec in self:
            if rec.qty_done > rec.product_uom_qty:
                raise ValidationError("La cantidad hecha no puede ser mayor a la planeada")
