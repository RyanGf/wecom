# -*- coding: utf-8 -*-

import requests
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WeComAppCallbackService(models.Model):
    """
    接收事件服务器配置
    https://work.weixin.qq.com/api/doc/90000/90135/90930
    """

    _name = "wecom.app_callback_service"
    _description = "Wecom Application receive event service"

    # 关联到wecom.apps模型，表示这个回调服务属于哪个企业微信应用。
    app_id = fields.Many2one(
        "wecom.apps",
        string="Application",
        copy=False,
        ondelete="cascade",
        default=lambda self: self.env["wecom.apps"].id,
        # domain="[('company_id', '=', company_id)]",
        required=True,
    )
    # 回调服务的名称
    name = fields.Char(string="Service Name", required=True, translate=True)
    # 回调服务的唯一代码
    code = fields.Char(
        string="Service Code",
        copy=False,
        required=True,
    )
    # 计算字段，存储回调服务的完整URL
    callback_url = fields.Char(
        string="URL",
        store=True,
        readonly=True,
        compute="_compute_callback_url",
        copy=False,
    )  # 回调服务地址
    callback_url_token = fields.Char(string="Token", copy=False)  # Token用于计算签名
    callback_aeskey = fields.Char(string="AES Key", copy=False)  # 用于消息内容加密 / 用于消息内容加密的AES密钥
    # 回调服务的描述
    description = fields.Text(string="Description", translate=True, copy=True)
    # 表示该回调服务是否激活
    active = fields.Boolean("Active", default=False)

    last_validated = fields.Datetime("Last Validated", readonly=True)

    # 回调服务代码是唯一的
    _sql_constraints = [
        (
            "app_code_uniq",
            "unique (app_id,code)",
            _("The code of each application must be unique !"),
        )
    ]

    @api.depends("app_id", "code")
    def _compute_callback_url(self):
        """
        根据应用ID和代码生成默认的回调URL
        默认回调地址
        :return:"""

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        callback_url = ""
        for server in self:
            if server.app_id.company_id and server.code:
                server.callback_url = f"{base_url}/wecom_callback/{server.app_id.company_id.id}/{server.code}"
            else:
                server.callback_url = ""

    @api.onchange("app_id", "code")
    def _onchange_callback_url(self):
        """
        当应用ID或代码改变时，更新回调URL。
        当应用发生变化时，更新回调服务地址
        :return:
        """
        self._compute_callback_url()

    def generate_contact_service(self):
        """
        生成通讯录回调服务的URL。
        生成通讯录回调服务
        :return:
        {base_url}/wecom_callback/{company_id}/{code}
        """
        self.ensure_one()
        if not self.app_id:
            raise ValidationError(_("Please bind contact app!"))
        return self.callback_url

    def validate_callback_config(self):
        """验证回调配置的有效性"""
        self.ensure_one()
        if not (self.callback_url and self.callback_url_token and self.callback_aeskey):
            raise ValidationError(_("Callback URL, Token, and AES Key must be set."))

        try:
            # 这里应该调用企业微信的API来验证回调配置
            # 以下是一个示例，实际实现需要根据企业微信的API文档来编写
            response = requests.post(
                "https://qyapi.weixin.qq.com/cgi-bin/callback/check",
                json={
                    "url": self.callback_url,
                    "token": self.callback_url_token,
                    "aeskey": self.callback_aeskey,
                },
                timeout=10
            )
            result = response.json()
            if result.get("errcode") == 0:
                self.last_validated = fields.Datetime.now()
                return True
            else:
                raise ValidationError(_(f"Validation failed: {result.get('errmsg')}"))
        except Exception as e:
            raise ValidationError(_(f"Error during validation: {str(e)}"))

    @api.model
    def create(self, vals):
        record = super(WeComAppCallbackService, self).create(vals)
        record.validate_callback_config()
        return record

    def write(self, vals):
        result = super(WeComAppCallbackService, self).write(vals)
        if 'callback_url' in vals or 'callback_url_token' in vals or 'callback_aeskey' in vals:
            for record in self:
                record.validate_callback_config()
        return result
