from odoo import models, _
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        try:
            if request and request.params.get('download'):
                user = self.env.user

                def _is_admin():
                    try:
                        return user._is_admin()
                    except AttributeError:
                        return user.has_group('base.group_erp_manager') or user.id == 1

                if not _is_admin():
                    if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                        if record._name == 'ir.attachment':
                            model_name = record.res_model
                            res_id = record.res_id
                            if model_name in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                                if not self.env['ir.attachment']._is_allowed_project_attachment_target(model_name, res_id, user):
                                    raise AccessError(_("You are not allowed to download attachments from this project/task."))
                        elif record._name in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                            if not self.env['ir.attachment']._is_allowed_project_attachment_target(record._name, record.id, user):
                                raise AccessError(_("You are not allowed to download attachments from this project/task."))
        except RuntimeError:
            pass # No HTTP request context

        return super()._record_to_stream(record, field_name)
