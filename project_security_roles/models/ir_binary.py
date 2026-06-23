from odoo import models, api, _
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download'):
            user = self.env.user
            if not self.env.su and user.has_group("project.group_project_user") and not user.has_group("project.group_project_manager"):
                model_name = record._name
                res_id = record.id

                # Si es un ir.attachment, validamos el modelo destino (res_model y res_id)
                if model_name == 'ir.attachment':
                    target_model = record.res_model
                    target_res_id = record.res_id
                    if target_model in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                        if not self.env['ir.attachment']._is_allowed_project_attachment_target(target_model, target_res_id, user):
                            raise AccessError(_("You are not allowed to download attachments from records where you are not the project responsible or task assignee."))

                # Si estamos descargando directamente de un modelo de proyecto
                elif model_name in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                    if not self.env['ir.attachment']._is_allowed_project_attachment_target(model_name, res_id, user):
                        raise AccessError(_("You are not allowed to download attachments from records where you are not the project responsible or task assignee."))

        return super()._record_to_stream(record, field_name)
