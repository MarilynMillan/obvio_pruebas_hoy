from odoo import models
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if not self.env.su and request and request.params.get('download'):
            user = self.env.user
            if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                model_name = record._name
                res_id = record.id

                guard_models = self.env['ir.attachment']._PROJECT_GUARDED_MODELS

                is_guarded_record = False

                if model_name in guard_models:
                    is_guarded_record = True
                elif model_name == 'ir.attachment':
                    if record.res_model in guard_models:
                        model_name = record.res_model
                        res_id = record.res_id
                        is_guarded_record = True

                if is_guarded_record:
                    if not self.env['ir.attachment']._is_allowed_project_attachment_target(model_name, res_id, user):
                        raise AccessError("You can only download attachments on project records where you are the project responsible or task assignee.")

        return super()._record_to_stream(record, field_name)
