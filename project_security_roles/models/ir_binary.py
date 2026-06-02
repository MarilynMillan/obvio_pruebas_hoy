from odoo import models, _
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download') and str(request.params.get('download')).lower() not in ('0', 'false') and not self.env.su:
            user = self.env.user
            if user.has_group("project.group_project_user") and not user.has_group("project.group_project_manager"):
                model_name = record._name
                res_id = record.id

                if model_name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id

                if model_name in ('project.project', 'project.task', 'project.milestone', 'project.update'):
                    target_record = self.env[model_name].sudo().browse(res_id).exists()
                    if target_record:
                        is_allowed = False
                        if model_name == 'project.project':
                            is_allowed = (target_record.user_id == user)
                        elif model_name == 'project.task':
                            is_allowed = (target_record.project_id.user_id == user or user in target_record.user_ids)
                        else:
                            is_allowed = (target_record.project_id.user_id == user)

                        if not is_allowed:
                            raise AccessError(_("You are not allowed to download attachments from records where you are not the responsible or assignee."))

        return super()._record_to_stream(record, field_name)
