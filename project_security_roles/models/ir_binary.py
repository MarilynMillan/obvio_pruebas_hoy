from odoo import models, _
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download'):
            user = self.env.user
            if not user._is_admin():
                if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                    if record._name == 'ir.attachment':
                        model_name = record.res_model
                        res_id = record.res_id

                        if model_name in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                            if not self.env['ir.attachment']._is_allowed_project_attachment_target(model_name, res_id, user):
                                raise AccessError(_("No tienes permisos para descargar adjuntos de este proyecto o tarea."))

        return super()._record_to_stream(record, field_name)
