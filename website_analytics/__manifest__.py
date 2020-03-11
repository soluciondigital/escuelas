# Copyright 2018 Hugo Rodrigues
# License BSD-3-Clause
# pylint: disable=missing-docstring
{
    "name": "Website Analytics",
    "summary": "A (simple) website analytic tool",
    "version": "12.0.1.0.1",
    "category": "Website Analytics",
    "website": "https://hugorodrigues.net",
    "author": "Hugo Rodrigues",
    "license": "Other OSI approved licence",
    "application": True,
    "installable": True,
    "depends": [
        "base",
        "mail",
        "ipstack_connector"
        ],
    "data": [
        "data/ir_module_category.xml",
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "views/actions.xml",
        "views/website_analytics_view.xml",
        "reports/visitor_report_view.xml",
        "views/menus.xml",
        ],
    "demo": ["demo/demo.xml"],
    "images": ["static/images/main_screenshot.png"]
}
