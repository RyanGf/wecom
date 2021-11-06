# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.wxwork_api.api.corp_api import CorpApi, CORP_API_TYPE
from odoo.addons.wxwork_api.api.abstract_api import ApiException
from odoo.addons.wxwork_api.api.error_code import Errcode

from datetime import datetime, timedelta
import datetime
import hashlib

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"

    auth_agentid = fields.Char(
        "Auth agent Id",
        default="0000000",
        help="The web application ID of the authorizing party, which can be viewed in the specific web application",
    )
    auth_secret = fields.Char(
        "Auth Secret", default="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    corp_jsapi_ticket = fields.Char("Enterprise JS API Ticket",)

    agent_jsapi_ticket = fields.Char("Application JS API Ticket",)

    js_api_list = fields.Char("JS API Inertface List")

    ticket_interval_time = fields.Integer(
        "Pull interval time", default=1, required=True,
    )

    ticket_interval_type = fields.Selection(
        [("minutes", "Minutes"), ("hours", "Hours")],
        string="Pull Interval Unit",
        default="hours",
        required=True,
    )

    get_ticket_last_time = fields.Datetime("Last time to get the ticket",)

    def get_jsapi_ticket(self):
        """
        获取企业和应用 jsapi ticket
        """
        ir_config = self.env["ir.config_parameter"].sudo()
        debug = ir_config.get_param("wxwork.jsapi_debug")
        if debug:
            _logger.info(_("Start to pull enterprise WeChat Ticket of %s") % self.name)
        if self.corpid == False:
            raise UserError(_("Please fill in correctly Enterprise ID."))
        elif self.auth_secret == False:
            raise UserError(_("Please fill in the application 'secret' correctly."))
        else:
            if not self.get_ticket_last_time:
                self.get_corp_ticket()
                self.get_agent_ticket()
            else:
                self.compare_wxwork_ticket_time()
        if debug:
            _logger.info(_("End of pulling enterprise WeChat Ticket"))

    def get_corp_ticket(self):
        """
        拉取 企业 jsapi ticket
        """
        ir_config = self.env["ir.config_parameter"].sudo()
        debug = ir_config.get_param("wxwork.jsapi_debug")
        if debug:
            _logger.info(
                _("Start to pull enterprise WeChat Ticket of %s: Enterprise ticket")
                % self.name
            )
        wxapi = CorpApi(self.corpid, self.auth_secret)
        try:
            response = wxapi.httpCall(
                CORP_API_TYPE["GET_JSAPI_TICKET"],
                {"access_token": wxapi.getAccessToken(),},
            )
            if self.corp_jsapi_ticket != response["ticket"]:
                # self.corp_jsapi_ticket = response["ticket"]
                self.write(
                    {"corp_jsapi_ticket": response["ticket"],}
                )

            if debug:
                _logger.info(
                    _(
                        "Finish pulling enterprise WeChat Ticket of %s: Enterprise ticket"
                    )
                    % self.name
                )
        except ApiException as ex:
            if debug:
                _logger.warning(
                    _(
                        "Failed to pull enterprise WeChat Ticket : Enterprise ticket, Error code:%s, Error info:%s"
                    )
                    % (str(ex.errCode), Errcode.getErrcode(ex.errCode), ex.errMsg)
                )
            raise UserError(
                _("Error code: %s \nError description: %s \nError Details:\n%s")
                % (str(ex.errCode), Errcode.getErrcode(ex.errCode), ex.errMsg)
            )

    def get_agent_ticket(self):
        """
        拉取 应用 jsapi ticket
        """
        ir_config = self.env["ir.config_parameter"].sudo()
        debug = ir_config.get_param("wxwork.jsapi_debug")
        if debug:
            _logger.info(
                _("Start to pull enterprise WeChat Ticket of %s: Application ticket")
                % self.name
            )
        wxapi = CorpApi(self.corpid, self.auth_secret)
        try:
            response = wxapi.httpCall(
                CORP_API_TYPE["GET_TICKET"],
                {"access_token": wxapi.getAccessToken(), "type": "agent_config",},
            )
            if self.agent_jsapi_ticket != response["ticket"]:
                # self.agent_jsapi_ticket = response["ticket"]
                # self.get_ticket_last_time = datetime.datetime.now()
                self.write(
                    {
                        "agent_jsapi_ticket": response["ticket"],
                        "get_ticket_last_time": datetime.datetime.now(),
                    }
                )

            if debug:
                _logger.info(
                    _(
                        "Finish pulling enterprise WeChat Ticket of %s: Application ticket"
                    )
                    % self.name
                )
        except ApiException as ex:
            if debug:
                _logger.warning(
                    _(
                        "Failed to pull enterprise WeChat Ticket : Application ticket, Error code:%s, Error info:%s"
                    )
                    % (str(ex.errCode), Errcode.getErrcode(ex.errCode), ex.errMsg)
                )
            raise UserError(
                _("Error code: %s \nError description: %s \nError Details:\n%s")
                % (str(ex.errCode), Errcode.getErrcode(ex.errCode), ex.errMsg)
            )

    def compare_wxwork_ticket_time(self):
        overdue = False

        if self.ticket_interval_type:
            if self.ticket_interval_type == "hours":
                overdue = self.env["wxwork.tools"].cheeck_hours_overdue(
                    self.get_ticket_last_time, self.ticket_interval_time
                )
            elif self.ticket_interval_type == "minutes":
                overdue = self.env["wxwork.tools"].cheeck_minutes_overdue(
                    self.get_ticket_last_time, self.ticket_interval_time
                )

        if overdue:
            # 超时
            self.get_corp_ticket()
            self.get_agent_ticket()

    # -------------------------------------
    # 企业微信JS SDK
    # -------------------------------------

    # @api.model
    def get_wxwork_jsapi_param(self, args=None):
        """
        获取JSAPI的属性
        args:
            company_id: 公司id
            nonceStr: 生成签名的随机串
            timestamp: 生成签名的时间戳
            url: 当前网页的URL， 不包含#及其后面部分
        """
        ir_config = self.env["ir.config_parameter"].sudo()
        debug = ir_config.get_param("wxwork.jsapi_debug")
        print(args, type(args), args[0])
        # return {
        #     "parameters": [
        #         {
        #             "debug": not not (True if debug == "True" else False),
        #             "appId": self.corpid,
        #             "agentid": self.auth_agentid,
        #             "signature": self.generate_wxwork_jsapi_signature(args),
        #         }
        #     ]
        # }

    def generate_wxwork_jsapi_signature(self, args):
        """
        使用sha1加密算法，生成签名
        """
        # 生成签名前，刷新ticke
        res_config = self.env["res.config.settings"].sudo()
        res_config.get_jsapi_ticket()

        url = self.get_param("web.base.url")
        ticket = self.get_param("wxwork.corp_jsapi_ticket")
        str = ("jsapi_ticket=%s&noncestr=%s&timestamp=%s&url=%s") % (
            ticket,
            args[0],
            args[1],
            url + args[2],
        )
        # print(str)
        # sha = hashlib.sha1(str.encode("utf-8"))
        # encrypts = sha.hexdigest()
        encrypts = hashlib.sha1(str.encode("utf-8")).hexdigest()
        return encrypts

    def check_ticket(self):
        """
        检查ticket是否有效
        """
