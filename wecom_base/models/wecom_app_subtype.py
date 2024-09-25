# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class WeComAppSubtype(models.Model):
    """
    企业微信应用子类型管理
    用于定义和管理企业微信应用的子类型，支持层级结构
    """
    _name = "wecom.app.subtype"
    _description = "Wecom Application Subtype"
    _order = "parent_id,sequence,id"

    name = fields.Char(
        string="Name",
        translate=True,
        copy=False,
        required=True,
        help="应用子类型的名称，支持多语言"
    )

    parent_id = fields.Many2one(
        "wecom.app.type",
        ondelete="cascade",
        string="Parent Type",
        index=True,
        copy=False,
        required=True,
        help="关联的父类型，用于建立层级结构"
    )

    code = fields.Char(
        string="Code",
        copy=False,
        required=True,
        help="应用子类型的唯一标识代码"
    )

    sequence = fields.Integer(
        default=10,
        help="用于确定子类型的显示顺序，较小的值排在前面"
    )

    active = fields.Boolean(
        default=True,
        help="设置子类型是否可用。未激活的子类型将不会显示在列表中。"
    )

    full_name = fields.Char(
        string="Full Name",
        compute='_compute_full_name',
        store=True,
        help="显示完整的层级路径"
    )

    child_ids = fields.One2many(
        'wecom.app.subtype',
        'parent_id',
        string="Child Subtypes",
        help="该子类型的下级子类型"
    )

    _sql_constraints = [
        ("code_uniq", "unique (code)", _("Code must be unique across all subtypes!"))
    ]

    @api.depends('name', 'parent_id.name')
    def _compute_full_name(self):
        """
        计算并设置子类型的完整名称，包括所有上级类型
        """
        for subtype in self:
            if subtype.parent_id:
                subtype.full_name = f"{subtype.parent_id.name} / {subtype.name}"
            else:
                subtype.full_name = subtype.name

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """
        检查是否存在循环引用
        """
        if not self._check_recursion():
            raise ValidationError(_("Error! You cannot create recursive hierarchies."))

    @api.model
    def name_create(self, name):
        """
        重写name_create方法，允许快速创建时自动分配一个唯一的code
        """
        default_code = self.env['ir.sequence'].next_by_code('wecom.app.subtype.code')
        return self.create({'name': name, 'code': default_code}).name_get()[0]

    def name_get(self):
        """
        自定义记录的显示名称，使用完整路径
        """
        result = []
        for record in self:
            result.append((record.id, record.full_name))
        return result
