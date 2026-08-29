from odoo import models, _
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        try:
            from odoo.http import request
            if request and request.params.get('download'):
                user = self.env.user
                is_admin = user.has_group('base.group_erp_manager') or user.id == 1
                if not is_admin and user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                    model_name = record._name
                    res_id = record.id

                    attachment_model = self.env['ir.attachment']
                    if hasattr(attachment_model, '_is_allowed_project_attachment_target'):
                        if not attachment_model._is_allowed_project_attachment_target(model_name, res_id, user):
                            raise AccessError(_("You are not allowed to download this file."))
        except RuntimeError:
            pass
        return super()._record_to_stream(record, field_name)
