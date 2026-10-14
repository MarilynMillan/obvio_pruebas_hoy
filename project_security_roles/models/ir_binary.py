from odoo import models, _
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        from odoo.http import request

        try:
            is_download = request and request.params.get('download')
        except RuntimeError:
            is_download = False

        if is_download:
            user = self.env.user
            if not (user.has_group('base.group_erp_manager') or user.id == 1):
                if record._name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id

                    if model_name in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                        if not self.env['ir.attachment']._is_allowed_project_attachment_target(model_name, res_id, user):
                            raise AccessError(_("You can only download attachments from project records where you are the project responsible or task assignee."))

        return super()._record_to_stream(record, field_name)
