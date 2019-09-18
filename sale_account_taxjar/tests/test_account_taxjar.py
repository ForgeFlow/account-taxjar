# Copyright 2018-2019 Eficent Business and IT Consulting Services S.L.
# - (https://www.eficent.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import logging
from os.path import dirname, join
from odoo.tests import SingleTransactionCase
from .utils import scrub_string

from vcr import VCR

logging.getLogger("vcr").setLevel(logging.WARNING)

recorder = VCR(
    record_mode='once',
    cassette_library_dir=join(dirname(__file__), 'fixtures/cassettes'),
    path_transformer=VCR.ensure_suffix('.yaml'),
    filter_headers=['Authorization'],
    decode_compressed_response=True,
)


class TestAccountTaxjar(SingleTransactionCase):

    @classmethod
    def setUpClass(self):
        super(TestAccountTaxjar, self).setUpClass()
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        # Update Company address
        self.state_CO = self.env.ref('base.state_us_6')
        self.company = self.env.ref('base.main_company')
        self.company_res_partner = self.env.ref('base.main_company').partner_id
        self.company_res_partner.update(
            {
                'country_id': self.state_CO.country_id.id,
                'state_id': self.state_CO.id,
                'zip': '80538',
                'city': 'Loveland',
                'street': '626 W 66th St',
            }
        )
        # Create an account to handle taxes
        self.account_type = self.env['account.account.type'].create({
            'name': 'Test',
            'type': 'payable',
        })
        self.account = self.env['account.account'].create({
            'name': 'Test Sale Tax account',
            'code': 'TEST',
            'user_type_id': self.account_type.id,
            'reconcile': True,
        })
        # Create TaxJar Configuration
        self.taxjar = self.env['base.account.taxjar'].create({
            'name': 'TaxJar',
            'taxjar_api_url': 'https://api.sandbox.taxjar.com',
            'taxjar_api_token': 'token_pride',
            'taxable_account_id': self.account.id
        })

        self.customer = self.env['res.partner'].create({
            'name': 'City of Henderson',
            'street': '720-726 S Gunnison Ave',
            'city': 'Buena Vista',
            'zip': '81211',
            'state_id': self.state_CO.id,
            'country_id': self.state_CO.country_id.id,
        })

        self.product_template = self.env['product.template'].create({
            'name': 'Computer',
        })
        self.product_product = self.env['product.product'].create({
            'name': 'Awesome Computer',
            'product_tmpl_id': self.product_template.id,
            'invoice_policy': 'order'
        })

        self.service_template = self.env['product.template'].create({
            'name': 'Service',
        })
        self.service_product = self.env['product.product'].create({
            'name': 'Awesome Service',
            'type': 'service',
            'product_tmpl_id': self.service_template.id,
            'invoice_policy': 'order'
        })

    def _create_invoice_from_sale(self, sale):
        payment = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'all'
        })
        sale_context = {
            'active_id': sale.id,
            'active_ids': sale.ids,
            'active_model': 'sale.order',
            'open_invoices': True,
        }
        res = payment.with_context(sale_context).create_invoices()
        return self.env['account.invoice'].browse(res['res_id'])

    @recorder.use_cassette()
    def test_01_sync_taxjar_tax_code(self):
        self.taxjar.sync_taxjar_tax_code()
        taxjar_tax_codes = self.env['product.taxjar.category'].search(
            [('taxjar_id', '=', self.taxjar.id)])
        self.assertEqual(len(taxjar_tax_codes), 29)

    @recorder.use_cassette()
    def test_02_sync_taxjar_nexus_region(self):
        self.taxjar.sync_taxjar_nexus_region()
        taxjar_nexus_region = self.env['account.fiscal.position'].search(
            [('taxjar_id', '=', self.taxjar.id)])
        self.assertEqual(len(taxjar_nexus_region), 6)

    def test_03_sale_order_validate_on_update_taxjar_taxes(self):
        self.product_template.tax_code_id = self.env[
            'product.taxjar.category'].search([('code', '=', '31000')],
                                              limit=1).id
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_invoice_id': self.customer.id,
            'partner_shipping_id': self.customer.id,
            'warehouse_id': self.browse_ref('stock.warehouse0').id,
            'order_line': [(0, 0, {'name': self.product_product.name,
                                   'product_id': self.product_product.id,
                                   'product_uom_qty': 1,
                                   'product_uom': self.uom_unit.id,
                                   'price_unit': 200.0,
                                   })]})
        # Get fiscal_position_id
        so.onchange_partner_shipping_id()
        self.assertEqual(so.fiscal_position_id.is_nexus, True)
        # Confirm our standard sale order
        so.action_confirm()
        with recorder.use_cassette(
                path='test_03_sale_order_validate_on_update_taxjar_taxes',
                before_record_response=scrub_string(
                    'OLD_ACCOUNT_LINE_ID',
                    str(so.order_line.id))
        ):
            so.prepare_taxes()
            self.assertEqual(so.amount_total, 215.8)

    def test_04_sale_order_validate_on_update_zero_taxes(self):
        self.service_template.tax_code_id = self.env[
            'product.taxjar.category'].search([('code', '=', '19000')],
                                              limit=1).id
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_invoice_id': self.customer.id,
            'partner_shipping_id': self.customer.id,
            'warehouse_id': self.browse_ref('stock.warehouse0').id,
            'order_line': [(0, 0, {'name': self.service_product.name,
                                   'product_id': self.service_product.id,
                                   'product_uom_qty': 1,
                                   'product_uom': self.uom_unit.id,
                                   'price_unit': 50.0,
                                   })]})
        # Get fiscal_position_id
        so.onchange_partner_shipping_id()
        self.assertEqual(so.fiscal_position_id.is_nexus, True)
        with recorder.use_cassette(
                path='test_04_sale_order_validate_on_update_zero_taxes',
                before_record_response=scrub_string(
                    'OLD_ACCOUNT_LINE_ID',
                    str(so.order_line.id))
        ):
            so.prepare_taxes()
            # Confirm our standard sale order
            so.action_confirm()
            self.assertEqual(so.amount_total, 50)