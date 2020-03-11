"""Reports regarding visitors"""

from psycopg2 import extensions

from odoo import models, api, fields, tools


class VisitorReport(models.Model):
    _name = "report.website.analytics.visitor"
    _auto = False


    website_id = fields.Many2one(comodel_name="website.analytics",
                                 readonly=True)
    visit_date = fields.Date(readonly=True)

    visits = fields.Integer(readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        CREATE OR REPLACE VIEW %s AS
            SELECT
                row_number() over() AS id,
                COUNT(wav.id) AS visits,
                wav.create_date::date AS visit_date,
                wav.website_id
            FROM website_analytics_visitor AS wav
            GROUP BY wav.website_id, wav.create_date::date
            ORDER BY wav.create_date::date ASC
        """
        self.env.cr.execute(query, (extensions.AsIs(self._table),))


class VisitReport(models.Model):
    _name = "report.website.analytics.page"
    _auto = False


    website_id = fields.Many2one(comodel_name="website.analytics",
                                 readonly=True)

    page = fields.Char(readonly=True)

    visits = fields.Integer(readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        CREATE OR REPLACE VIEW %s AS
            SELECT
                row_number() over() AS id,
                wavv.website_id,
                wavp.path AS page,
                COUNT(wavp.path) AS visits
            FROM website_analytics_visit_page AS wavp
            JOIN website_analytics_visit AS wav ON wav.id = wavp.visit_id
            JOIN website_analytics_visitor AS wavv ON wavv.id = wav.visitor_id
            GROUP BY wavv.website_id, wavp.path
        """
        self.env.cr.execute(query, (extensions.AsIs(self._table),))
