from odoo import models, _
from odoo.exceptions import AccessError
from odoo.http import request

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        try:
            if request and request.params.get('download'):
                user = self.env.user

                # We check if user is a project user but not a project manager/admin
                is_admin = user.has_group('base.group_erp_manager') or user.id == 1
                if not is_admin and user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):

                    model_name = record.res_model if record._name == 'ir.attachment' else record._name
                    res_id = record.res_id if record._name == 'ir.attachment' else record.id

                    _PROJECT_GUARDED_MODELS = {'project.project', 'project.task', 'project.milestone', 'project.update'}

                    if model_name in _PROJECT_GUARDED_MODELS and res_id:
                        target_record = self.env[model_name].sudo().browse(res_id).exists()
                        if target_record:
                            # User is restricted from downloading attachments from guarded models
                            raise AccessError(_("No tienes permiso para descargar archivos adjuntos de este registro."))
        except RuntimeError:
            pass

        return super()._record_to_stream(record, field_name)
