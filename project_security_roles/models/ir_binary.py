from odoo import models, api, _
from odoo.exceptions import AccessError
from odoo.http import request


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _record_to_stream(self, record, field_name):
        # We enforce download limits only for explicit downloads
        if request and request.params.get("download") and not self.env.su:
            # We determine the real target record (a project object or attachment)
            model_name = record._name
            res_id = record.id

            if model_name == "ir.attachment":
                model_name = record.res_model
                res_id = record.res_id

            # Only verify if it belongs to project guarded models
            if model_name in self.env["ir.attachment"]._PROJECT_GUARDED_MODELS:
                # Use the already defined method in IrAttachment to verify rights
                if not self.env["ir.attachment"]._is_allowed_project_attachment_target(
                    model_name, res_id, self.env.user
                ):
                    raise AccessError(
                        _(
                            "You do not have permission to download attachments for this record. "
                            "You must be the project responsible or a task assignee."
                        )
                    )

        return super()._record_to_stream(record, field_name)
