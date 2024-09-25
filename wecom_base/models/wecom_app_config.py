# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

# 定义字段类型选项
FIELD_TYPES = [(key, key) for key in sorted(fields.Field.by_type)]

class WeComAppConfig(models.Model):
    _name = "wecom.app_config"
    _description = "Wecom Application Configuration"
    _table = "wecom_app_config"
    _order = "id"

    # 关联到企业微信应用
    app_id = fields.Many2one(
        "wecom.apps",
        string="Application",
        copy=False,
        ondelete="cascade",
        required=True,
    )
    # 关联到公司
    company_id = fields.Many2one(related="app_id.company_id", store=True)
    # 配置项名称
    name = fields.Char(string="Name", translate=True, required=True, copy=True)
    # 配置项键
    key = fields.Char(required=True)
    # 配置项类型
    ttype = fields.Selection(selection=FIELD_TYPES, string="Field Type", required=True, copy=True)
    # 配置项值
    value = fields.Text(required=True)
    # 配置项描述
    description = fields.Html(string="Description", translate=True, copy=True)

    # SQL约束，确保每个应用的配置键是唯一的
    _sql_constraints = [
        (
            "app_id_key_uniq",
            "unique (app_id,key)",
            _("The key of each application must be unique!"),
        )
    ]

    @api.constrains('ttype', 'value')
    def _check_value_type(self):
        """
        验证值是否符合指定的字段类型
        """
        for record in self:
            try:
                self._convert_value(record.value, record.ttype)
            except ValueError:
                raise ValidationError(_("The value does not match the specified field type."))

    @api.model
    def _convert_value(self, value, ttype):
        """
        根据指定的类型转换值
        """
        if ttype == 'boolean':
            if isinstance(value, str):
                value = value.lower()
                if value in ('true', 'yes', 't', '1'):
                    return True
                elif value in ('false', 'no', 'f', '0'):
                    return False
            return bool(value)
        elif ttype in ('integer', 'float'):
            return fields.Float.from_string(value)
        elif ttype == 'datetime':
            return fields.Datetime.from_string(value)
        elif ttype == 'date':
            return fields.Date.from_string(value)
        return value

    @api.model
    def get_param(self, app_id, key, default=False):
        """
        获取指定键的参数值
        :param app_id: 应用ID
        :param key: 参数键
        :param default: 默认值
        :return: 参数值或默认值
        """
        param = self.search([('app_id', '=', app_id), ('key', '=', key)], limit=1)
        if not param:
            return default
        return self._convert_value(param.value, param.ttype)

    @api.model
    def set_param(self, app_id, key, value, ttype=None):
        """
        设置参数值
        :param app_id: 应用ID
        :param key: 参数键
        :param value: 参数值
        :param ttype: 参数类型
        :return: 操作是否成功
        """
        param = self.search([('app_id', '=', app_id), ('key', '=', key)])
        if param:
            if value is not False and value is not None:
                return param.write({'value': value})
            else:
                return param.unlink()
        elif value is not False and value is not None:
            if not ttype:
                ttype = 'char'
            return self.create({
                'app_id': app_id,
                'key': key,
                'value': value,
                'ttype': ttype
            })
        return False

    def update_config(self, value):
        """
        更新配置值
        :param value: 新的配置值
        :return: 更新操作的结果
        """
        self.ensure_one()
        return self.write({'value': value})

    @api.model
    def create(self, vals):
        """
        创建新记录时清除缓存
        """
        record = super(WeComAppConfig, self).create(vals)
        self.clear_caches()
        return record

    def write(self, vals):
        """
        更新记录时清除缓存
        """
        result = super(WeComAppConfig, self).write(vals)
        self.clear_caches()
        return result

    def unlink(self):
        """
        删除记录时清除缓存
        """
        result = super(WeComAppConfig, self).unlink()
        self.clear_caches()
        return result

    @api.model
    def bulk_set_params(self, app_id, params_dict):
        """
        批量设置多个参数
        :param app_id: 应用ID
        :param params_dict: 参数字典 {key: value}
        :return: 操作是否成功
        """
        for key, value in params_dict.items():
            self.set_param(app_id, key, value)
        return True

    @api.model
    def bulk_get_params(self, app_id, keys):
        """
        批量获取多个参数
        :param app_id: 应用ID
        :param keys: 参数键列表
        :return: 参数字典 {key: value}
        """
        params = self.search([('app_id', '=', app_id), ('key', 'in', keys)])
        return {param.key: self._convert_value(param.value, param.ttype) for param in params}