from odoo import models, _
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        # We check if the request is for downloading
        if request and request.params.get('download'):
            user = self.env.user
            if not self.env.su and user.has_group("project.group_project_user") and not user.has_group("project.group_project_manager"):
                model_name = record._name
                res_id = record.id

                # If downloading an attachment, check its linked record
                if model_name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id

                if model_name in ('project.project', 'project.task') and res_id:
                    target_record = self.env[model_name].sudo().browse(res_id).exists()
                    if target_record:
                        is_manager = False
                        if model_name == 'project.project':
                            is_manager = (target_record.user_id == user)
                        elif model_name == 'project.task':
                            is_manager = (target_record.project_id.user_id == user or user in target_record.user_ids)

                        if not is_manager:
                            raise AccessError(_("No tienes permisos para descargar adjuntos de este registro. Solo puedes visualizarlos."))

        return super()._record_to_stream(record, field_name)
