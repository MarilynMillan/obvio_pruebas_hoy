from odoo import models
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download'):
            user = self.env.user
            if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                model_name = record._name
                res_id = record.id

                # For ir.attachment we check the related model
                if model_name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id

                # Replicating IrAttachment._is_allowed_project_attachment_target logic
                guarded_models = {"project.project", "project.task", "project.milestone", "project.update"}

                if model_name in guarded_models and res_id:
                    target_record = self.env[model_name].sudo().browse(res_id).exists()
                    if target_record:
                        allowed = False
                        if model_name == "project.project":
                            allowed = (target_record.user_id == user)
                        elif model_name == "project.task":
                            allowed = (target_record.project_id.user_id == user or user in target_record.user_ids)
                        else:
                            allowed = (target_record.project_id.user_id == user)

                        if not allowed:
                            raise AccessError("No puedes descargar archivos adjuntos de proyectos o tareas en las que solo eres un seguidor.")

        return super()._record_to_stream(record, field_name)
