from odoo import models, fields, api, _
import pytz

# =========================
# CHATTER (mail.message)
# =========================
class MailMessage(models.Model):
    _inherit = 'mail.message'

    def unlink(self):
        # Extendemos a tareas y proyectos
        valid_models = ['project.task', 'project.project']
        task_messages = self.filtered(lambda r: r.model in valid_models)
        other_messages = self - task_messages

        for record in task_messages:
            if record.body and '🗑️' in str(record.body):
                other_messages |= record
                continue

            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            current_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
            user_name = self.env.user.name.replace(' - USER', '').strip()

            del_msg = _("🗑️ MESSAGE DELETED")
            by_msg = _("By %s on %s") % (user_name, current_time)

            new_body = f"""
                <div class="is_deleted_message" style="background-color: #fff5f5; border: 1px solid #ffcccc; padding: 10px; border-radius: 5px; color: #a94442;">
                    <div style="font-weight: bold; margin-bottom: 5px;">{del_msg}</div>
                    <small style="color: #666;">{by_msg}</small>
                    <hr style="border: 0; border-top: 1px solid #ffcccc; margin: 5px 0;"/>
                    <div style="text-decoration: line-through; color: #999; font-style: italic;">
                        {record.body or ''}
                    </div>
                </div>
            """
            super(MailMessage, record.with_context(skip_tracking=True)).write({'body': new_body})

        if other_messages:
            return super(MailMessage, other_messages).unlink()
        return True

# =========================
# ACTIVIDADES (mail.activity)
# =========================
class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _get_activity_log_info(self):
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        now_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
        stranger_msg = _('A stranger')
        creator_name = (self.create_uid.name or stranger_msg).replace(' - USER', '').strip()
        current_user_name = self.env.user.name.replace(' - USER', '').strip()
        create_time = fields.Datetime.to_datetime(self.create_date).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
        return {
            'now': now_time,
            'creator': creator_name,
            'created_at': create_time,
            'current_user': current_user_name
        }

    def _action_done(self, feedback=False, attachment_ids=None):
        info = self._get_activity_log_info()
        created_msg = _("📅 Created: %s (%s)") % (info['creator'], info['created_at'])
        finished_msg = _("✅ Finished: %s (%s)") % (info['current_user'], info['now'])

        log_msg = f"""
        \n{created_msg}
        {finished_msg}

        """
        full_message = f"{feedback or ''}{log_msg}"
        return super(MailActivity, self.with_context(skip_cancel_log=True))._action_done(
            feedback=full_message,
            attachment_ids=attachment_ids
        )

    def write(self, vals):
        tracked_fields = {
            'summary': _('Summary'),
            'note': _('Note'),
            'date_deadline': _('Deadline'),
            'user_id': _('Assigned to'),
            'activity_type_id': _('Type of activity'),
        }
        # Ahora incluimos project.project en el rastreo
        valid_models = ['project.task', 'project.project']
        activities_to_log = self.filtered(lambda a: a.res_model in valid_models)

        old_values = {}
        for activity in activities_to_log:
            old_values[activity.id] = {
                f_name: (activity[f_name].display_name if activity._fields[f_name].type == 'many2one' else activity[f_name])
                for f_name in tracked_fields if f_name in vals
            }

        result = super(MailActivity, self).write(vals)

        for activity in activities_to_log:
            changes = []
            info = activity._get_activity_log_info()
            for field_name, label in tracked_fields.items():
                if field_name not in vals: continue
                old_val = old_values.get(activity.id, {}).get(field_name, '')
                new_val = activity[field_name].display_name if activity._fields[field_name].type == 'many2one' else activity[field_name]
                if str(old_val).strip() != str(new_val).strip():
                    empty_msg = _('Empty')
                    changes.append(f"<li><b>{label}:</b> {old_val or empty_msg} → {new_val or empty_msg}</li>")

            if changes:
                created_msg = _("📅 Created:")
                updated_msg = _("✎ Updated:")
                activity.env['mail.message'].create({
                    'body': f"""
                        <div style="color:#555; border-left:3px solid #6c757d; padding-left:10px;">
                            <small>{created_msg} <b>{info['creator']}</b> ({info['created_at']})</small><br/>
                            <small>{updated_msg} <b>{info['current_user']}</b> ({info['now']})</small>
                            <ul style="margin:4px 0 0 15px; padding:0;">{''.join(changes)}</ul>
                        </div>
                    """,
                    'model': activity.res_model,
                    'res_id': activity.res_id,
                    'message_type': 'notification',
                })
        return result

    def unlink(self):
        if not self._context.get('skip_cancel_log'):
            valid_models = ['project.task', 'project.project']
            for activity in self:
                if activity.res_model in valid_models:
                    info = activity._get_activity_log_info()
                    created_msg = _("📅 Created:")
                    canceled_msg = _("🗙 Canceled:")
                    subject_msg = _("Subject:")
                    note_msg = _("Note:")
                    no_note_msg = _("No note")

                    self.env['mail.message'].create({
                        'body': f"""
                            <div style="color: #666666; border-left: 3px solid #ccc; padding-left: 10px;">
                                <small>{created_msg} <b>{info['creator']}</b> ({info['created_at']})</small><br/>
                                <small>{canceled_msg} <b>{info['current_user']}</b> ({info['now']})</small>
                                <br/><b>{subject_msg}</b> {activity.summary or activity.activity_type_id.name}
                                <br/><span style="font-size: 0.9em;">{note_msg} {activity.note or no_note_msg}</span>
                            </div>
                        """,
                        'model': activity.res_model,
                        'res_id': activity.res_id,
                        'message_type': 'notification',
                    })
        return super(MailActivity, self).unlink()
