# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name': 'Base TaxJar',
    'version': '11.0.1.0.0',
    'category': 'Account',
    'summary': 'TaxJar SmartCalc API integration',
    'author': 'Eficent, '
              'Odoo Community Association (OCA)',
    "website": "https://www.eficent.com/",
    'depends': [
        'account',
        'sale_stock_sourcing_address',
    ],
    'external_dependencies': {'python': ['taxjar']},
    'data': [
        'security/ir.model.access.csv',
        'data/account_tax_group.xml',
        'views/base_account_taxjar_views.xml',
        'views/account_fiscal_position_views.xml',
        'views/product_taxjar_category_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}