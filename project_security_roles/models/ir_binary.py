from odoo import models, _
from odoo.http import request
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        stream = super()._record_to_stream(record, field_name)

        if request and request.params.get('download'):
            user = self.env.user
            # Check if user is a restricted project user
            if user.has_group('project.group_project_user') and not user.has_group('project.group_project_manager'):
                # Handle direct attachments or other models
                if record._name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id
                else:
                    model_name = record._name
                    res_id = record.id

                # Use the existing guard logic from ir.attachment
                attachment_model = self.env['ir.attachment']
                if hasattr(attachment_model, '_PROJECT_GUARDED_MODELS') and model_name in attachment_model._PROJECT_GUARDED_MODELS:
                    # System administrators bypass this check (usually done implicitly, but to be sure we check if they are explicitly bypassing)
                    if not attachment_model._is_allowed_project_attachment_target(model_name, res_id, user):
                        raise AccessError(_("You are not allowed to download attachments from this project record."))

        return stream
