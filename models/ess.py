# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools ,_
from odoo.exceptions import except_orm, ValidationError,UserError
from odoo.exceptions import  AccessError, UserError, RedirectWarning,Warning
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta , date
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.exceptions
import re 

class MrpProductionQueries(models.Model):
    _inherit = 'mrp.production'

    # def action_view_mo_delivery(self):
    #     """ This function returns an action that display picking related to
    #     manufacturing order orders. It can either be a in a list or in a form
    #     view, if there is only one picking to show.
    #     """
    #     self.ensure_one()
    #     action = self.env.ref('stock.action_picking_tree_all').read()[0]
    #     pickings = self.mapped('picking_ids')
    #     if len(pickings) > 1:
    #         action['domain'] = [('id', 'in', pickings.ids)]
    #         action['context'] = [{'default_group_id':self.procurement_group_id.id}]
    #     elif pickings:
    #         action['domain'] = [('id', 'in', pickings.ids)]
    #         action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form'),(self.env.ref('stock.vpicktree').id, 'tree')]
    #         action['res_id'] = pickings.id
    #         action['context'] = [{'default_group_id':self.procurement_group_id.id}]
    #     return action

    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([
                ('group_id', '=', order.procurement_group_id.id),
            ])
            order.delivery_count = len(order.picking_ids)

    @api.multi
    def new_picking(self):
        self.ensure_one()
        ctx = {
            'default_mrpid_check': True,
            # 'default_group_id': self.procurement_group_id.id,
            'default_mrpid': self.id,
            'default_origin':self.name,
            'default_location_id':12,
            'default_location_dest_id':16,
            'default_picking_type_id':6,
        }
        return {
            'name': _('Picking'),
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('stock.view_picking_form').id,
            'view_mode': 'form',
            'view_type': 'form',
            'limit': 80,
            'context': ctx
        }

    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search(['|',
                ('group_id', '=', order.procurement_group_id.id),('origin', '=', order.name)
            ])
            order.delivery_count = len(order.picking_ids)
        
    # cancel_count = fields.Integer('Count',default=0)

    # @api.model_cr
    # def init(self):
    #     # self._table = sale_report
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
    #         %s
    #         FROM ( %s )
    #         %s
    #         )""" % (self._table, self._select(), self._from(), self._group_by()))
    @api.model_cr
    def cancel_workorders(self):
        for rec in self:
            cos = self.env['mrp.workorder'].search([('production_id','=',rec.id),('final_lot_id','!=',False)])
            for l in cos:
                coz = self.env['stock.production.lot'].search([('id','=',l.final_lot_id.id)])
                coz.unlink()
            self.env.cr.execute("""update mrp_workorder set state = 'cancel' where production_id = %s """ % self.id)
            self.env.cr.execute("""delete from mrp_workorder where production_id = %s """ % self.id)
            self.write({
                                'state':'confirmed',
                            })
        
        # self.env.cr.execute("""delete from stock_move_line 
        #                                     where production_id=%s and lot_id is null
        #                                     and product_id in (select product_id from stock_move_line 
        #                                                         where production_id=%s
        #                                                         group by product_id having count(*)>1 )""" % (self.id,self.id))
        
            for l in rec.move_raw_ids:
                com = self.env['stock.move.line'].search([('move_id','=',l.id)])
                for line in com:
                    line.unlink()        # self.cancel_count = 1
        # return select_str

    # @api.model_cr
    # def delete_workorders(self):
    #     self.env.cr.execute("""delete from mrp_workorder where production_id = %s """ % self.id)
    #     self.write({
    #                         'state':'confirmed',
    #                     })
    #     self.cancel_count = 0

    # @api.model_cr
    # def delete_stockmove(self):
    #     for rec in self:
    #         for l in rec.move_raw_ids:
    #             if l.needs_lots == True:
    #                 self.env.cr.execute("""delete from stock_move_line 
# where production_id=%s and lot_id is null
#  and product_id in (select product_id from stock_move_line 
#                     where production_id=%s
#                     group by product_id having count(*)>1 ) """ % (self.id,l.product_id.id))
#         # self.write({
#         #                     'state':'confirmed',
#         #                 })
#         # self.cancel_count = 0
#         # return select_str


class stockpickingcus(models.Model):
    _inherit = 'stock.picking'

    mrpid = fields.Many2one('mrp.production',string="mrp id")
    mrpid_check = fields.Boolean(string="mrp check",default=False)
#     group_id = fields.Many2one(
#         'procurement.group', 'Procurement Group')


#     @api.onchange('move_lines')
#     def group_id_get(self):
#         for rec in self:
#             if self.mrpid_check == True:
#                 for x in rec.move_lines:
#                     x.group_id = rec.mrpid.procurement_group_id.id
#             else:
#                 rec.group_id = rec.move_lines.group_id.id

    # @api.model
    # def create(self, vals):
    #     # TDE FIXME: clean that brol
    #     defaults = self.default_get(['name', 'picking_type_id'])
    #     if vals.get('name', '/') == '/' and defaults.get('name', '/') == '/' and vals.get('picking_type_id', defaults.get('picking_type_id')):
    #         vals['name'] = self.env['stock.picking.type'].browse(vals.get('picking_type_id', defaults.get('picking_type_id'))).sequence_id.next_by_id()

    #     # TDE FIXME: what ?
    #     # As the on_change in one2many list is WIP, we will overwrite the locations on the stock moves here
    #     # As it is a create the format will be a list of (0, 0, dict)
    #     if vals.get('move_lines') and vals.get('location_id') and vals.get('location_dest_id'):
    #         for move in vals['move_lines']:
    #             if len(move) == 3 and move[0] == 0:
    #                 move[2]['location_id'] = vals['location_id']
    #                 move[2]['location_dest_id'] = vals['location_dest_id']
    #     res = super(stockpickingcus, self).create(vals)
    #     res._autoconfirm_picking()
    #     if vals['mrpid_check'] == True:
    #         self.write({
    #             'group_id': self.mrpid.procurement_group_id.id
    #         })
    #     return res