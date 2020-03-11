"""
Controller to track users
"""

import logging
from werkzeug.exceptions import NotFound
from odoo import http, fields
from odoo.http import request


LOGGER = logging.getLogger(__name__)

class VisitorTracker(http.Controller):
    """Controller used to track users"""

    def _do_track(self, website_token, source=None, path=None):
        """
        Create the tracker register

        :param string website_token: token to identify the website
        :param string source: origin of the visit
        :param string path: final visit location
        :return: http response to the request
        :rtype: httpresponse
        """
        website_obj = request.env["website.analytics"].sudo()
        visitor_obj = request.env["website.analytics.visitor"].sudo()
        visitor_obj = visitor_obj.with_context(raise_on_fail=False)
        visit_obj = request.env["website.analytics.visit"].sudo()
        page_obj = request.env["website.analytics.visit.page"].sudo()

        source = source if source is not None else request.httprequest.referrer
        source = source if source else ""

        path = path if path is not None else request.httprequest.path or ""

        visitor = request.session.get("tracker_visitor_id", False)
        if isinstance(visitor, int):
            visitor = visitor_obj.browse(visitor)
            if not visitor.exists():
                visitor = False

        website = website_obj.search([("analytics_token", "=", website_token)],
                                     limit=1)
        do_not_track = request.httprequest.headers.get('DNT', 0)
        user_agent = request.httprequest.environ.get("HTTP_USER_AGENT", "")
        try:
            do_not_track = int(do_not_track) == 1
        except ValueError:
            do_not_track = False
        if not website or (website.respect_dnt and do_not_track):
            LOGGER.info("Invalid website (%s) or DNT enabled", website_token)
            return request.not_found(), False, False

        if source.startswith(website.url):
            source = source.replace(website.url, "")
            source = "/%s" % source if source[0] != "/" else source
        if path.startswith(website.url):
            path = path.replace(website.url, "")
            path = "/%s" % path if path[0] != "/" else path

        new_cookies = {}
        response_headers = website.get_response_headers()
        if not visitor:
            # Find a existing visitor via cookies
            visitor = request.httprequest.cookies.get("tracker_visitor_id",
                                                      False)
            if visitor:
                visitor = visitor_obj.browse(int(visitor))
                if not visitor.exists():
                    visitor = visitor_obj.create({"website_id": website.id})
                    new_cookies["tracker_visitor_id"] = str(visitor.id)
            else:
                # Create a new visitor
                visitor = visitor_obj.create({"website_id": website.id})
                new_cookies["tracker_visitor_id"] = str(visitor.id)
            request.session["tracker_visitor_id"] = visitor.id
        visitor.write({
            "ip_address": request.httprequest.remote_addr or "",
            "user_id": request.uid,
            "visit_date": fields.Datetime.now()
            })

        visit = request.session.get("tracker_visit_id", False)
        if not visit:
            visit = visit_obj.create({"visitor_id": visitor.id,
                                      "user_agent": user_agent})
            request.session["tracker_visit_id"] = visit.id
        else:
            visit = visit_obj.browse(visit)
            if not visit.exists():
                visit = visit_obj.create({"visitor_id": visitor.id,
                                          "user_agent": user_agent})
                request.session["tracker_visit_id"] = visit.id

        page_obj.create({"visit_id": visit.id, "source": source, "path": path})

        return website.get_response_content(), response_headers, new_cookies


    @http.route(["/website/visitor/tracker/<string:website_token>"],
                type="http", auth="public")
    def tracker(self, website_token):
        """Tracker route"""
        response, headers, cookies = self._do_track(website_token)
        if isinstance(response, NotFound):
            return response
        return request.make_response(response, headers, cookies=cookies)

    @http.route(["/website/visitor/tracker"], type="json",
                auth="public", methods=["PUT"])
    def tracker_json(self):
        """Tracker REST API"""
        data = request.jsonrequest
        for key in ["website"]:
            assert key in data, "Missing required attribute %s" % key
        response, headers, cookies = self._do_track(data.get("website"),
                                                    data.get("source", None),
                                                    data.get("path", None))

        return {
            "data": response,
            "headers": headers,
            "cookies": cookies
        }
