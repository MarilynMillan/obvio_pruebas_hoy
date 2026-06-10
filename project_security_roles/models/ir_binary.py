from odoo import models, _
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name, **kwargs):
        # We only care about explicit download requests
        if request and request.params.get('download') and not self.env.su:
            user = self.env.user
            if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                model_name = record._name
                res_id = record.id

                # If the record itself is an attachment, we check its target
                if model_name == 'ir.attachment':
                    target_model = record.res_model
                    target_id = record.res_id
                    if target_model in ['project.task', 'project.project']:
                        raise AccessError(_("You are not allowed to download attachments from this project/task."))

                # If the record is directly a guarded model (like downloading a document directly linked)
                elif model_name in ['project.task', 'project.project']:
                    raise AccessError(_("You are not allowed to download attachments from this project/task."))

        return super()._record_to_stream(record, field_name, **kwargs)
