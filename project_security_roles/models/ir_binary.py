from odoo import models
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if record._name == 'ir.attachment' and record.res_model in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
            # If there's an active HTTP request and it's explicitly asking to download
            if request and getattr(request, 'params', {}).get('download') == 'true':
                user = self.env.user
                if user.has_group('project.group_project_user') and not self.env.su:
                    if not self.env['ir.attachment'].sudo()._is_allowed_project_attachment_target(record.res_model, record.res_id, user):
                        raise AccessError("No tienes permiso para descargar archivos adjuntos de tareas/proyectos donde solo eres seguidor.")
        return super()._record_to_stream(record, field_name)
