from odoo import models, _
from odoo.exceptions import AccessError

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name, **kwargs):
        is_download = kwargs.get('download') or self.env.context.get('download')

        if is_download:
            user = self.env.user
            if user.has_group("project.group_project_user") and not user.has_group("project.group_project_manager"):
                model_name = record._name

                # Use IrAttachment's logic to check target
                if model_name in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                    res_id = record.id
                    if not self.env['ir.attachment']._is_allowed_project_attachment_target(model_name, res_id, user):
                        raise AccessError(_("You can only download attachments on project records where you are the project responsible or task assignee."))

                elif model_name == 'ir.attachment':
                    target_model = record.res_model
                    target_res_id = record.res_id
                    if target_model in self.env['ir.attachment']._PROJECT_GUARDED_MODELS:
                        if not self.env['ir.attachment']._is_allowed_project_attachment_target(target_model, target_res_id, user):
                            raise AccessError(_("You can only download attachments on project records where you are the project responsible or task assignee."))

        return super()._record_to_stream(record, field_name, **kwargs)
