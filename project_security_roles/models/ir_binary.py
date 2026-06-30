from odoo import models, _
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        user = self.env.user

        # intercept only explicit download requests
        if request and request.params.get('download'):
            # Allow bypass for system admins
            if not user.has_group('base.group_system'):

                # We need to see if the record is an attachment and applies to project/task models
                if record._name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id

                    _PROJECT_GUARDED_MODELS = {
                        "project.project",
                        "project.task",
                        "project.milestone",
                        "project.update",
                    }

                    if model_name in _PROJECT_GUARDED_MODELS and res_id:
                        target_record = self.env[model_name].sudo().browse(res_id).exists()

                        is_allowed = False
                        if target_record:
                            if model_name == "project.project":
                                is_allowed = (target_record.user_id == user)
                            elif model_name == "project.task":
                                is_allowed = (target_record.project_id.user_id == user or user in target_record.user_ids)
                            else:
                                is_allowed = (target_record.project_id.user_id == user)

                        if not is_allowed:
                            raise AccessError(
                                _("You can only download attachments on project records where you are the project responsible or task assignee.")
                            )

        return super()._record_to_stream(record, field_name)
