from odoo import models
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        stream = super()._record_to_stream(record, field_name)

        try:
            if request and request.params.get('download'):
                user = self.env.user

                # Bypassing for admin
                if user.has_group('base.group_erp_manager') or user.id == 1:
                    return stream

                if user.has_group("project.group_project_user") and not user.has_group("project.group_project_manager"):
                    # Record can be ir.attachment or other models with binary fields
                    if record._name == 'ir.attachment':
                        # Leverage _is_allowed_project_attachment_target
                        if not self.env['ir.attachment']._is_allowed_project_attachment_target(record.res_model, record.res_id, user):
                            raise AccessError("No tienes permisos para descargar adjuntos de este proyecto o tarea.")
                    elif record._name in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                        # Direct download from project or task field
                        if not self.env['ir.attachment']._is_allowed_project_attachment_target(record._name, record.id, user):
                            raise AccessError("No tienes permisos para descargar adjuntos de este proyecto o tarea.")
        except RuntimeError:
            pass # No request context (e.g., cron or CLI)

        return stream
