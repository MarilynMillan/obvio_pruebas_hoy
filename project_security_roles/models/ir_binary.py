from odoo import models, _
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        # Prevent sudo breakage by using an explicit check
        is_sudo = self.env.su
        if not is_sudo and request and request.params.get('download'):
            user = self.env.user
            if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                if record._name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id
                    # Import our guard logic from the custom IrAttachment implementation
                    attachment_model = self.env['ir.attachment']
                    if hasattr(attachment_model, '_is_allowed_project_attachment_target'):
                        if model_name in attachment_model._PROJECT_GUARDED_MODELS:
                            if not attachment_model._is_allowed_project_attachment_target(model_name, res_id, user):
                                raise AccessError(
                                    _("You can only download attachments on project records where you are the project responsible or task assignee.")
                                )
        return super()._record_to_stream(record, field_name)
