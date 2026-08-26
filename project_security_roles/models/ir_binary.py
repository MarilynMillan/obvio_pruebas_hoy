from odoo import models
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _record_to_stream(self, record, field_name):
        is_download = False
        try:
            if request and hasattr(request, 'params'):
                is_download = bool(request.params.get('download'))
        except RuntimeError:
            pass

        if is_download:
            user = self.env.user
            if not user._is_admin():
                if user.has_group("project.group_project_user") and not user.has_group("project.group_project_manager"):
                    ir_attachment = self.env['ir.attachment']
                    model_name = record.res_model if record._name == 'ir.attachment' else record._name
                    res_id = record.res_id if record._name == 'ir.attachment' else record.id

                    if model_name in ir_attachment._PROJECT_GUARDED_MODELS:
                        if not ir_attachment._is_allowed_project_attachment_target(model_name, res_id, user):
                            raise AccessError("No tiene permiso para descargar archivos de este registro.")

        return super()._record_to_stream(record, field_name)
