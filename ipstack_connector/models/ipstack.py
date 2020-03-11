"""Used to set track visitors"""

import json
import logging
import requests

from odoo import models, api, exceptions, _


LOGGER = logging.getLogger(__name__)

class IpstackError(exceptions.except_orm):
    """Custom exception for ipstack"""

    def __init__(self, error):
        message = _("{info}\n\nError Code: {code}\nError Type: {type}")
        message = message.format_map(error)
        super(IpstackError, self).__init__(_("ipstack error"), message)


class Ipstack(models.AbstractModel):
    """
    Abstact ipstack module
    """
    _name = "ipstack.connector"

    @api.model
    def get_data(self, ip_address):
        """Get data from webservice"""
        if isinstance(ip_address, str):
            ip_address = set([ip_address])
        elif isinstance(ip_address, list):
            ip_address = set(ip_address)
        ip_address = set([x for x in ip_address if x]) # Remove invalid IP
        if len(ip_address) > 50:  # Prevents too_many_ips error
            groups = [ip_address[x:x+50] for x in range(0, len(ip_address), 50)]
            res = []
            for group in groups:
                res.extend(self.get_data(group))
            return res
        elif not ip_address:
            return self.get_data("127.0.0.1")
        params_obj = self.env["ir.config_parameter"].sudo()
        api_url = params_obj.get_param("ipstack.url",
                                       "https://api.ipstack.com/")
        if api_url[-1:] == "/":
            api_url = api_url[:-1]
        url_data = {
            "api_url": api_url,
            "api_key": params_obj.get_param("ipstack.key", False),
            "ip_addr": ",".join(ip_address)
            }
        url = "{api_url}/{ip_addr}?access_key={api_key}"
        url = url.format_map(url_data)
        req = requests.get(url)
        res = json.loads(req.text)
        if "error" in res:
            error = res["error"]
            # If batch is not supported, fallback to one request per IP
            if error["type"] == "batch_not_supported_on_plan":
                LOGGER.warning("Batch requests not supported on your plan")
                res = []
                for ip_addr in ip_address:
                    res.extend(self.get_data(ip_addr))
            else:
                raise IpstackError(error)
        if not isinstance(res, list):
            res = [res]
        return res

    @api.model
    def map_country(self, ip_address):
        """Maps an IP to a country"""
        country_obj = self.env["res.country"].sudo()
        api_result = self.get_data(ip_address)
        res = {}
        for ip_addr in api_result:
            if "country_code" not in ip_addr:
                raise IpstackError(_("Invalid response from webservice"))
            country_code = ip_addr["country_code"]
            country = country_obj.search([('code', '=', country_code)], limit=1)
            res[ip_addr["ip"]] = country
        return res
