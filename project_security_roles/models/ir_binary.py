from odoo import models
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download'):
            user = self.env.user
            if not user._is_admin() and user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                if record._name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id

                    attachment_model = self.env['ir.attachment']
                    if hasattr(attachment_model, '_PROJECT_GUARDED_MODELS') and model_name in attachment_model._PROJECT_GUARDED_MODELS:
                        if hasattr(attachment_model, '_is_allowed_project_attachment_target') and not attachment_model._is_allowed_project_attachment_target(model_name, res_id, user):
                            raise AccessError("You can only download attachments of projects/tasks where you are the project responsible or task assignee.")

        return super()._record_to_stream(record, field_name)
