"""General Settings"""

from odoo import models, api, fields

class ResConfigSettings(models.TransientModel):
    """
    Abstact ipstack module
    """
    _inherit = "res.config.settings"

    ipstack_url = fields.Char()
    ipstack_key = fields.Char()

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        api_url = params.get_param("ipstack.url",
                                   "https://api.ipstack.com/")
        api_key = params.get_param("ipstack.key",
                                   "Get from https://api.ipstack.com/")
        res.update(
            ipstack_url=api_url,
            ipstack_key=api_key,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param("ipstack.url", self.ipstack_url)
        params.set_param("ipstack.key", self.ipstack_key)
