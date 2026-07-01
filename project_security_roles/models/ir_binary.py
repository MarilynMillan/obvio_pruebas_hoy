from odoo import models, _
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download'):
            user = self.env.user
            if not user.has_group('base.group_system') and record._name == 'ir.attachment':
                # Re-evaluating the check because _is_allowed_project_attachment_target exists in project_import_guard.py under IrAttachment.
                # However, just to be sure we correctly reference the method on the actual model instance
                is_allowed = self.env['ir.attachment']._is_allowed_project_attachment_target(record.res_model, record.res_id, user)
                if not is_allowed:
                    raise AccessError(_("You are not allowed to download attachments from a project or task where you are merely a follower."))
        return super()._record_to_stream(record, field_name)
