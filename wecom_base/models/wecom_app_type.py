# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class WeComAppType(models.Model):
    """
    企业微信应用类型管理
    用于定义和管理企业微信应用的主要类型
    """
    _name = "wecom.app.type"
    _description = "Wecom Application Type"
    _order = "sequence, id"

    name = fields.Char(
        string="Name",
        translate=True,
        copy=False,
        required=True,
        help="应用类型的名称，支持多语言"
    )

    code = fields.Char(
        string="Code",
        copy=False,
        required=True,
        help="应用类型的唯一标识代码"
    )

    subtype_ids = fields.One2many(
        "wecom.app.subtype",
        "parent_id",
        string="Application Subtypes",
        help="与此应用类型关联的子类型列表"
    )

    sequence = fields.Integer(
        default=10,
        copy=True,
        help="用于确定应用类型的显示顺序，较小的值排在前面"
    )

    active = fields.Boolean(
        default=True,
        help="设置应用类型是否可用。未激活的类型将不会显示在列表中。"
    )

    description = fields.Text(
        string="Description",
        translate=True,
        help="应用类型的详细描述"
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique (code)",
            _("Code must be unique across all application types!"),
        )
    ]

    @api.constrains('code')
    def _check_code(self):
        """
        检查code的有效性
        """
        for record in self:
            if not record.code.isalnum():
                raise ValidationError(_("Code must contain only letters and numbers."))

    @api.model
    def name_create(self, name):
        """
        重写name_create方法，允许快速创建时自动分配一个唯一的code
        """
        default_code = self.env['ir.sequence'].next_by_code('wecom.app.type.code')
        return self.create({'name': name, 'code': default_code}).name_get()[0]

    def name_get(self):
        """
        自定义记录的显示名称，包括代码
        """
        result = []
        for record in self:
            result.append((record.id, f"[{record.code}] {record.name}"))
        return result

    @api.model
    def create(self, vals):
        """
        重写创建方法，确保code全部大写
        """
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        return super(WeComAppType, self).create(vals)

    def write(self, vals):
        """
        重写写入方法，确保code全部大写
        """
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        return super(WeComAppType, self).write(vals)