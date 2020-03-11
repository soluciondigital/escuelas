"""Used to set track visitors"""

import random
import string
import logging
import base64
import json

import requests

LOGGER = logging.getLogger(__name__)

try:
    import user_agents
except ImportError:
    LOGGER.warning("Unable to import user_agents. Browser and OS detection "
                   "not available, please install user_agents")
    user_agents = False

from odoo import models, api, fields, _, exceptions
from odoo.tools import config

from odoo.addons.ipstack_connector.models.ipstack import IpstackError

RESPONSE_IMAGE = "/9j/4AAQSkZJRgABAQEAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAv/aAAgBAQAAAAFf/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oACAEBAAAAEH//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EH//2Q=="


class WebsiteAnalytics(models.Model):
    """
    Extend Odoo website module
    """

    @staticmethod
    def _generate_token():
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(16))

    _name = "website.analytics"
    _inherit = ["mail.thread"]
    _description = "Website Analytics"

    _sql_constraints = [
        ("unique_analytics_token", "UNIQUE(analytics_token)",
         "Analytics token must be unique")]

    name = fields.Char(required=True)

    active = fields.Boolean(default=True)

    url = fields.Char(string="Address")

    respect_dnt = fields.Boolean(string="Respect Do Not Track", default=True)

    analytics_token = fields.Char(required=True, index=True, readonly=True,
                                  help="Used to identify "
                                       "the analytics request",
                                  default=lambda self: self._generate_token())

    code_type = fields.Selection(selection=[
        ("js", "Javascript"),
        ("img", "Image")],
                                  default="js", required=True)

    code = fields.Text(compute="_compute_code", string="Connector code",
                       store=True)

    visitor_ids = fields.One2many(comodel_name="website.analytics.visitor",
                                  inverse_name="website_id", string="Visitors")

    visitor_count = fields.Integer(compute="_compute_visitor_count",
                                   string="Nº of visitors")


    @api.depends("code_type", "analytics_token")
    def _compute_code(self):
        config_parameter_obj = self.env["ir.config_parameter"].sudo()
        base_url = config_parameter_obj.get_param("web.base.url")
        for website in self.filtered(lambda x: x.analytics_token):
            url = "%s/website/visitor/tracker/%s" % (base_url,
                                                     website.analytics_token)

            if website.code_type == "js":
                url = url.replace(website.analytics_token, "")
                code = """
                <script>
                    var xhttp = new XMLHttpRequest();
                    var data = JSON.stringify({"website": "%s", "path": document.location.href, "source": document.referrer});
                    xhttp.onreadystatechange = function() {
                        if (this.readyState == 4 && this.status == 200) {
                            response = JSON.parse(this.responseText);
                            cookies = response["result"]["cookies"]
                            for (var cookie_name in cookies) {
                                cookie_value = cookies[cookie_name];
                                document.cookie = cookie_name + "=" + cookie_value + ";";
                            }
                        }
                    };
                    xhttp.open("PUT", "%s", true);
                    xhttp.setRequestHeader("Content-Type", "application/json");
                    xhttp.send(data)
                </script>
                """ % (website.analytics_token, url)
            else:
                code = """<img src="%s" style="display: none;"></img>""" % url

            website.code = code


    @api.depends("visitor_ids")
    def _compute_visitor_count(self):
        for website in self:
            website.visitor_count = len(website.visitor_ids)

    @api.multi
    def action_code(self):
        self.ensure_one()
        return {
            "name": _("Website Analytics Code"),
            "view_mode": "form",
            "view_type": "form",
            "view_id": self.env.ref("website_analytics.website_analytics_form_connector_code").id,
            "res_model": self._name,
            "res_id": self.id,
            "type": "ir.actions.act_window",
            "target": "new"
            }

    @api.multi
    def get_response_headers(self):
        self.ensure_one()
        res = []
        if self.code_type == "img":
            res.append(("Content-Type", "image"))
        return res

    @api.multi
    def get_response_content(self):
        self.ensure_one()
        if self.code_type == "img":
            return base64.b64decode(RESPONSE_IMAGE)
        return ""


class WebsiteAnalyticsVisitor(models.Model):
    """
    Keep track of website visitors.
    The id of the visitor will be stored inside the session and as a cookie
    to prevent duplicated visitors
    """
    _name = "website.analytics.visitor"
    _inherit = ["ipstack.connector"]

    user_id = fields.Many2one(comodel_name="res.users", string="User")
    ip_address = fields.Char(string="IP Address", readonly=True)
    country_id = fields.Many2one(compute="_compute_country",
                                 comodel_name="res.country", string="Country",
                                 store=True)
    website_id = fields.Many2one(comodel_name="website.analytics",
                                 string="Website", required=True,
                                 ondelete="cascade")

    visit_ids = fields.One2many(comodel_name="website.analytics.visit",
                                inverse_name="visitor_id", string="Visits")

    visit_count = fields.Integer(compute="_compute_visit_count",
                                 string="Nº of visits")

    visit_date = fields.Datetime(string="Last visit")

    @api.depends("ip_address")
    def _compute_country(self):
        """Compute visitor country based on his IP"""
        countries = self.map_country(set([x.ip_address for x in self]))
        for user in self:
            try:
                country = countries.get(user.ip_address, False)
                if country:
                    user.country_id = country.id
            except IpstackError as errn:
                if self.env.context.get("raise_on_fail", True):
                    raise
                LOGGER.error(errn)

    @api.depends("visit_ids")
    def _compute_visit_count(self):
        for visitor in self:
            visitor.visit_count = len(visitor.visit_ids)

    @api.multi
    def name_get(self):
        res = []
        for visitor in self:
            if visitor.user_id:
                name = visitor.user_id.name
            else:
                name = self.env.ref("base.public_user").name
            if visitor.country_id:
                name += " (%s)" % visitor.country_id.name
            res.append((visitor.id, name))
        return res


class WebsiteAnalyticsVisit(models.Model):
    """
    Each visit that a visitor does.
    A visit ID is stored on a cookie. When the cookie expired, another
    visit is counted.
    """
    _name = "website.analytics.visit"

    visitor_id = fields.Many2one(comodel_name="website.analytics.visitor",
                                 required=True, string="Visitor",
                                 ondelete="cascade")

    user_agent = fields.Char()
    browser_id = fields.Many2one(comodel_name="website.analytics.browser",
                                 compute="_compute_extract_ua",
                                 string="Browser", store=True)
    os_id = fields.Many2one(comodel_name="website.analytics.os",
                            compute="_compute_extract_ua",
                            string="Operating System", store=True)

    page_ids = fields.One2many(comodel_name="website.analytics.visit.page",
                               inverse_name="visit_id", string="Pages")

    page_count = fields.Integer(compute="_compute_page_count",
                                string="Nº of pages")

    @api.depends("user_agent")
    def _compute_extract_ua(self):
        """
        Extract visitor browser and operating system based on the user_agent
        """
        if not user_agents:
            return
        browser_obj = self.env["website.analytics.browser"].sudo()
        so_obj = self.env["website.analytics.os"].sudo()
        for visit in self:
            user_agent = user_agents.parse(visit.user_agent)
            ua_browser = user_agent.browser
            ua_os = user_agent.os
            browser = browser_obj.search([("name", "=", ua_browser.family),
                                          ("version", "=",
                                           ua_browser.version_string)],
                                         limit=1)
            if not browser:
                browser = browser_obj.create({"name": ua_browser.family,
                                              "version": ua_browser.version_string
                                             })
            visitor_os = so_obj.search([("name", "=", ua_os.family),
                                        ("version", "=", ua_os.version_string)],
                                       limit=1)
            if not visitor_os:
                visitor_os = so_obj.create({"name": ua_os.family,
                                            "version": ua_os.version_string
                                           })
            visit.browser_id = browser.id
            visit.os_id = visitor_os.id

    @api.depends("page_ids")
    def _compute_page_count(self):
        for visit in self:
            visit.page_count = len(visit.page_ids)

    @api.multi
    def name_get(self):
        res = []
        for visit in self:
            date_utc = fields.Datetime.from_string(visit.create_date)
            date = fields.Datetime.context_timestamp(visit, date_utc)
            name = "%s (%s)" % (visit.visitor_id.display_name,
                                fields.Datetime.to_string(date))
            res.append((visit.id, name))
        return res


class WebsiteAnalyticsVisitPage(models.Model):
    """
    Used to set track visited pages
    """
    _name = "website.analytics.visit.page"

    visit_id = fields.Many2one(comodel_name="website.analytics.visit",
                               required=True, string="Visit",
                               ondelete="cascade")

    path = fields.Char()
    source = fields.Char()


class WebsiteAnalyticsBrowsers(models.Model):
    """
    Used to map browsers
    """
    _name = "website.analytics.browser"

    name = fields.Char(required=True)
    version = fields.Char()


class WebsiteAnalyticsOS(models.Model):
    """
    Used to map operating systems
    """
    _name = "website.analytics.os"

    name = fields.Char(required=True)
    version = fields.Char()
