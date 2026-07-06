from odoo import models
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download'):
            user = self.env.user
            if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                if record._name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id

                    ir_attachment_model = self.env['ir.attachment']

                    guarded_models = getattr(ir_attachment_model, '_PROJECT_GUARDED_MODELS', None)
                    if not guarded_models:
                         guarded_models = {
                             "project.project",
                             "project.task",
                             "project.milestone",
                             "project.update",
                         }

                    if model_name in guarded_models:
                        has_access = False
                        if hasattr(ir_attachment_model, '_is_allowed_project_attachment_target'):
                            has_access = ir_attachment_model._is_allowed_project_attachment_target(model_name, res_id, user)
                        else:
                            record_target = self.env[model_name].sudo().browse(res_id).exists()
                            if record_target:
                                if model_name == "project.project":
                                    has_access = record_target.user_id == user
                                elif model_name == "project.task":
                                    has_access = record_target.project_id.user_id == user or user in record_target.user_ids
                                else:
                                    has_access = record_target.project_id.user_id == user

                        if not has_access:
                            raise AccessError("No tienes permisos para descargar este adjunto del proyecto o tarea.")

        return super()._record_to_stream(record, field_name)
