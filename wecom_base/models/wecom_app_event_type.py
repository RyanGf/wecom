# -*- coding: utf-8 -*-

import logging
from typing import Dict, Any, Optional
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from lxml import etree
from odoo.http import Response
import xmltodict

_logger = logging.getLogger(__name__)

class WeComAppEventType(models.Model):
    """
    企业微信应用事件类型管理
    用于定义和处理来自企业微信的各种事件
    """

    _name = "wecom.app.event_type"
    _description = "Wecom Application Event"
    _order = "id"

    # 事件名称
    name = fields.Char(
        string="Name",
        translate=True,
        copy=False,
        required=True,
        help="事件的显示名称"
    )

    # 关联的Odoo模型
    model_ids = fields.Many2many(
        "ir.model",
        string="Related Model",
        help="与此事件类型关联的Odoo模型"
    )

    # 消息类型，默认为"event"
    msg_type = fields.Char(
        string="Message Type",
        copy=False,
        required=True,
        default="event",
        help="消息的类型，通常为'event'"
    )

    # 事件代码
    event = fields.Char(
        string="Event Code",
        copy=False,
        required=True,
        help="企业微信定义的事件代码"
    )

    # 变更类型
    change_type = fields.Char(
        string="Change Type",
        copy=False,
        help="事件的变更类型，如果适用"
    )

    # Python代码
    code = fields.Text(
        string="Python Code",
        default="",
        help="处理此事件时要执行的Python代码"
    )

    # 命令
    command = fields.Char(
        string="Command",
        copy=False,
        help="与事件关联的命令，如果适用"
    )

    @api.model
    def handle_event(self, xml_tree: str, company_id: int) -> Response:
        """
        处理来自企业微信的回调事件
        :param xml_tree: XML格式的事件数据
        :param company_id: 公司ID
        :return: HTTP响应
        """
        try:
            # 解析XML数据
            xml_dict = xmltodict.parse(xml_tree)
            event_str = xml_dict['xml'].get('Event')
            changetype_str = xml_dict['xml'].get('ChangeType')

            _logger.info(
                _("Received callback notification from WeChat Work, event [%s], change type [%s]."),
                event_str, changetype_str
            )

            # 查找对应的事件处理器
            event = self.sudo().search([
                ('event', '=', event_str),
                ('change_type', '=', changetype_str)
            ], limit=1)

            if not event:
                _logger.warning(
                    _("Cannot find event handler for event [%s] change type [%s], ignoring."),
                    event_str, changetype_str
                )
                return Response("success", status=200)

            # 如果找到事件处理器并且有代码，则执行
            if event.code:
                event.with_context(xml_tree=xml_tree, company_id=company_id).sudo().run()

            return Response("success", status=200)

        except Exception as e:
            _logger.exception("Error processing WeChat Work event: %s", str(e))
            return Response("success", status=200)

    def run(self) -> None:
        """
        执行与事件相关的代码
        """
        self.ensure_one()
        xml_tree = self.env.context.get('xml_tree')
        company_id = self.env.context.get('company_id')

        if not self.code:
            _logger.warning(_("No code defined for event [%s]"), self.name)
            return

        try:
            # 使用safe_eval执行代码，提供必要的上下文
            safe_eval(
                self.code,
                {
                    'env': self.env,
                    'model': self.env[self.model_ids.model],
                    'xml_tree': xml_tree,
                    'company_id': company_id,
                    'command': self.command,
                    'log': lambda message, level='info': _logger.log(getattr(logging, level.upper()), message)
                },
                mode="exec",
                nocopy=True
            )
        except Exception as e:
            _logger.exception(_("Error executing code for event [%s]: %s"), self.name, str(e))
            raise UserError(_("Error executing event code: %s") % str(e))

    @api.constrains('code')
    def _check_code(self):
        """
        验证事件代码的语法
        """
        for record in self:
            if record.code:
                try:
                    compile(record.code, "<string>", "exec")
                except SyntaxError as e:
                    raise UserError(_("Invalid Python code in event [%s]: %s") % (record.name, str(e)))