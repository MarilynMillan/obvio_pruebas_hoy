from odoo import models
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.tools.translate import _

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if request and request.params.get('download'):
            user = self.env.user
            if user.has_group('project.group_project_user') and not user.has_group('base.group_system'):
                if record._name == 'ir.attachment':
                    model_name = record.res_model
                    res_id = record.res_id
                    if model_name in ['project.project', 'project.task']:
                        target = self.env[model_name].sudo().browse(res_id).exists()
                        if target:
                            if model_name == 'project.project' and target.user_id != user:
                                raise AccessError(_("You cannot download attachments from projects where you are only a follower."))
                            elif model_name == 'project.task' and target.project_id.user_id != user and user not in target.user_ids:
                                raise AccessError(_("You cannot download attachments from tasks where you are only a follower."))
        return super()._record_to_stream(record, field_name)
