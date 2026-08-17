from odoo import models, api
from odoo.exceptions import AccessError
from odoo.http import request


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    @api.model
    def _record_to_stream(self, record, field_name):
        # Allow system administrators to bypass this check
        if self.env.user.id != 1 and request and request.params.get('download'):
            user = self.env.user
            if user.has_group("project.group_project_user") and not user.has_group("project.group_project_manager"):
                model_name = record._name

                # Check if the model is in the guarded list
                guarded_models = self.env["ir.attachment"]._PROJECT_GUARDED_MODELS

                if model_name in guarded_models or model_name == "ir.attachment":
                    if model_name == "ir.attachment":
                        target_model = record.res_model
                        target_res_id = record.res_id
                    else:
                        target_model = model_name
                        target_res_id = record.id

                    if target_model in guarded_models:
                        # Use the _is_allowed_project_attachment_target method from ir.attachment
                        is_allowed = self.env["ir.attachment"]._is_allowed_project_attachment_target(
                            target_model, target_res_id, user
                        )

                        if not is_allowed:
                            raise AccessError(
                                "No tienes permisos para descargar archivos adjuntos de este proyecto o tarea."
                            )

        return super()._record_to_stream(record, field_name)
