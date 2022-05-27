from odoo import fields, models, tools, api
import logging

_logger = logging.getLogger(__name__)


class RentalReport(models.Model):
    _name = "custom.rental.report"
    _description = "Custom Rental Analysis Report"
    _auto = False

    # date = fields.Date('Fecha', readonly=True)
    order_id = fields.Many2one('sale.order', 'Pedido #', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', 'Linea de Pedido #', readonly=True)
    product_id = fields.Many2one('product.product', 'Producto', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unidad de medida', readonly=True)
    quantity = fields.Float('Cantidad entregada diaria', readonly=True)
    qty_delivered = fields.Float('Cantidad recogida', readonly=True)
    qty_returned = fields.Float('Cantidad retornada diariamente', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Cliente', readonly=True)
    user_id = fields.Many2one('res.users', 'Vendedor', readonly=True)
    company_id = fields.Many2one('res.company', 'Compañia', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Plantilla de produto', readonly=True)
    categ_id = fields.Many2one('product.category', 'Categoria de producto ', readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Cotzacion enviada'),
        ('sale', 'Pedido de venta'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado'),
    ], string='Estado de Orden', readonly=True)
    price = fields.Float('Precio', readonly=True)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    rental_subscription_id = fields.Many2one(comodel_name='sale.subscription', string="Suscripción")
    rental_template_id = fields.Many2one(comodel_name='sale.subscription.template', string="Plantilla de suscripción")
    recurring_rule_type = fields.Selection(string='Recuerrencia',
                                           help="Factura automatica en el intervalo indicado",
                                           related="rental_template_id.recurring_rule_type", readonly=True)
    recurring_interval = fields.Integer(string='Repetir', help="Repetir cada (Dia/Semana/Mes/Año)",
                                        related="rental_template_id.recurring_interval", readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    currency_rate = fields.Float('Tasa de Registro', digits=0, readonly=True)
    pickup_date = fields.Datetime('Fecha de entrega (DATE)', readonly=True, compute='_compute_pickup_dates')
    pickup_date_text = fields.Char('Fecha de entrega', readonly=True, compute='_compute_pickup_dates')
    return_date = fields.Datetime('Fecha de retorno (Estimada/Efectiva) (DATE)', readonly=True, compute='_compute_return_dates')
    return_date_text = fields.Char('Fecha de retorno (Estimada/Efectiva)', readonly=True,
                                   compute='_compute_return_dates')

    # pickup_date_text = fields.Char('Fecha de entrega', readonly=True, default=lambda s: s._compute_pickup_dates())
    # return_date_text = fields.Char('Fecha de retorno', readonly=True, default=lambda s: s._compute_return_dates())

    def _compute_return_dates(self):
        for rec in self:
            # date_info = ''
            alternative_date = None
            move_lines = rec.sale_order_line_id.move_ids.filtered(lambda m: m.product_id == rec.product_id).mapped(
                'move_line_ids')
            for sml in move_lines.filtered(lambda ml: ml.lot_id == rec.lot_id):
                # _logger.info(f"{sml.date} RETURN")
                if sml.location_id == self.env.company.rental_loc_id:
                    if sml.date:
                        # date_info = sml.date.strftime('%d de %B de %Y')
                        alternative_date = sml.date

                        # "{2}/{1}/{0}".format(sml.date.year, sml.date.month, sml.date.day)
                    else:
                        # date_info = ''
                        alternative_date = False
            rec.return_date = alternative_date
            # rec.return_date_text = date_info

    def _compute_pickup_dates(self):
        for rec in self:
            # date_info = ''
            alternative_date = None
            move_lines = rec.sale_order_line_id.move_ids.filtered(lambda m: m.product_id == rec.product_id).mapped(
                'move_line_ids')
            for sml in move_lines.filtered(lambda ml: ml.lot_id == rec.lot_id):
                # _logger.info(f"{sml.date} PICKUP")
                if sml.location_dest_id == self.env.company.rental_loc_id:
                    if sml.date:
                        # date_info = sml.date.strftime('%d de %B de %Y')
                        alternative_date = sml.date
                            # "{2}/{1}/{0}".format(sml.date.year, sml.date.month, sml.date.day)
                    else:
                        # date_info = ''
                        alternative_date = None
            rec.pickup_date = alternative_date
            # rec.pickup_date_text = date_info

    rental_status = fields.Selection([
        ('draft', 'Cotizacion'),
        ('sent', 'Cotizacion enviada'),
        ('pickup', 'Confirmada'),
        ('return', 'Recogida'),
        ('returned', 'Devuelta'),
        ('cancel', 'Cancelado'),
    ], string="Estado de renta")
    lot_id = fields.Many2one('stock.production.lot', 'Serial Number', readonly=True)

    def _quantity(self):
        return """
            CASE
                WHEN res.stock_production_lot_id IS NOT NULL
                THEN 1.0
                ELSE product_uom_qty / (u.factor * u2.factor)
                END AS quantity,
            CASE
                WHEN res.stock_production_lot_id IS NULL
                THEN qty_delivered / (u.factor * u2.factor)
                WHEN returned.stock_production_lot_id IS NULL AND pickedup.stock_production_lot_id IS NULL
                THEN 0.0
                ELSE 1.0
                END AS qty_delivered,
            CASE
                WHEN res.stock_production_lot_id IS NULL
                THEN qty_returned / (u.factor * u2.factor)
                WHEN returned.stock_production_lot_id IS NOT NULL
                THEN 1.0
                ELSE 0.0
                END AS qty_returned
        """

    def _get_currency_rate(self):
        return """CASE COALESCE(so.currency_rate, 0) WHEN 0 THEN 1.0 ELSE 1/so.currency_rate END"""

    def _price(self):
        return """
            
            CASE
                WHEN res.stock_production_lot_id IS NOT NULL
                THEN (sol.price_subtotal / (date_part('day',sol.return_date - sol.pickup_date) + 1)) / (product_uom_qty / (u.factor * u2.factor))
                ELSE sol.price_subtotal / (date_part('day',sol.return_date - sol.pickup_date) + 1)
            END
        """

    def _select(self):
        return """
            sol.id,
            sol.order_id,
            sol.id AS sale_order_line_id,
            sol.product_id,
            %s,
            sol.product_uom,
            sol.order_partner_id AS partner_id,
            sol.salesman_id AS user_id,
            pt.categ_id,
            p.product_tmpl_id,
            %s AS price,
            sol.company_id,
            sol.state,
            sol.currency_id,
            res.stock_production_lot_id AS lot_id,
            so.rental_subscription_id,
            so.rental_template_id,
            so.warehouse_id,
            sol.pickup_date,
            sol.return_date,
            so.rental_status,
            %s AS currency_rate
        """ % (self._quantity(), self._price(), self._get_currency_rate())

    # so.name as pickup_date_text,
    # so.name as return_date_text,

    # generate_series(sol.pickup_date::date, sol.return_date::date, '1 day'::interval)::date date,

    def _from(self):
        return """
            sale_order_line AS sol
            join product_product AS p on p.id=sol.product_id
            join product_template AS pt on p.product_tmpl_id=pt.id
            join uom_uom AS u on u.id=sol.product_uom
            join uom_uom AS u2 on u2.id=pt.uom_id
            LEFT JOIN rental_reserved_lot_rel AS res ON res.sale_order_line_id=sol.id
                LEFT JOIN rental_pickedup_lot_rel AS pickedup ON pickedup.sale_order_line_id=sol.id
                    AND pickedup.stock_production_lot_id = res.stock_production_lot_id
                LEFT JOIN rental_returned_lot_rel AS returned ON returned.sale_order_line_id=sol.id
                    AND returned.stock_production_lot_id = res.stock_production_lot_id
            join sale_order AS so ON so.id=sol.order_id
            

        """

    def _query(self):
        return """
            (SELECT %s
            FROM %s
            WHERE sol.is_rental AND pt.unit_type IS NOT NULL)
        """ % (
            self._select(),
            self._from()
        )

    def init(self):
        # self._table = custom_rental_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
