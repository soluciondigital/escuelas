# Copyright 2018 Hugo Rodrigues
# License BSD-3-Clause
# pylint: disable=missing-docstring
{
    "name": "ipstack Connector",
    "summary": "Dev module to integrate with ipstack",
    "support": "support@hugorodrigues.net",
    "version": "11.0.1.0.0",
    "category": "Tools",
    "website": "https://hugorodrigues.net",
    "author": "Hugo Rodrigues",
    "license": "Other OSI approved licence",
    "application": False,
    "installable": True,
    "depends": [
        "base",
        "base_setup"
        ],
    "data": [
        "data/ir_config_parameter.xml",
        "views/res_config_settings_view.xml"
    ],
    "demo": ["demo/demo.xml"],
    "images": ["static/images/mail_screenshot.png"]
}
