from odoo import models, _
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        stream = super()._record_to_stream(record, field_name)
        if not stream or not record:
            return stream

        guarded_models = {"project.project", "project.task", "project.milestone", "project.update"}

        model_name = record._name
        target_model = False
        target_id = False

        if model_name in guarded_models:
            target_model = model_name
            target_id = record.id
        elif model_name == 'ir.attachment':
            if record.res_model in guarded_models:
                target_model = record.res_model
                target_id = record.res_id

        if target_model and target_id:
            if request:
                download_param = request.httprequest.args.get('download')
                # Check if download is true or present without being false
                is_download = False
                if download_param is not None:
                    if str(download_param).lower() not in ['false', '0']:
                        is_download = True

                if is_download:
                    user = self.env.user
                    if user.id != 1:  # skip superuser
                        is_allowed = True
                        if target_model == "project.project":
                            project = self.env["project.project"].sudo().browse(target_id).exists()
                            if project and project.user_id != user:
                                is_allowed = False
                        elif target_model == "project.task":
                            task = self.env["project.task"].sudo().browse(target_id).exists()
                            if task and task.project_id.user_id != user and user not in task.user_ids:
                                is_allowed = False
                        else:
                            record_obj = self.env[target_model].sudo().browse(target_id).exists()
                            if record_obj and hasattr(record_obj, 'project_id') and record_obj.project_id.user_id != user:
                                is_allowed = False

                        if not is_allowed:
                            raise AccessError(_("You are not allowed to download attachments from tasks or projects where you are not the responsible or assignee."))

        return stream
