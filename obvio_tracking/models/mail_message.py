from odoo import models, fields, api, _
import pytz

# =========================
# CHATTER (mail.message)
# =========================
class MailMessage(models.Model):
    _inherit = 'mail.message'

    def unlink(self):
        task_messages = self.filtered(lambda r: r.model == 'project.task')
        other_messages = self - task_messages

        for record in task_messages:
            # Usamos el emoji para detectar si ya está borrado
            if record.body and '🗑️' in str(record.body):
                other_messages |= record
                continue

            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            current_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')

            new_body = f"""
                <div class="is_deleted_message" style="background-color: #fff5f5; border: 1px solid #ffcccc; padding: 10px; border-radius: 5px; color: #a94442;">
                    <div style="font-weight: bold; margin-bottom: 5px;">🗑️ MENSAJE ELIMINADO</div>
                    <small style="color: #666;">Por {self.env.user.name} el {current_time}</small>
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

    def write(self, vals):
        if 'body' in vals and vals.get('body') and not self._context.get('skip_tracking'):

            marker = "<!-- HISTORY -->"

            for record in self:
                if record.model != 'project.task' or not record.body:
                    continue

                body_str = str(record.body or '')

                # 🚫 No tocar eliminados
                if '🗑️' in body_str or 'is_deleted_message' in body_str:
                    continue

                new_content = str(vals.get('body', ''))

                # ✅ separación correcta
                if marker in body_str:
                    old_content, history = body_str.split(marker, 1)
                else:
                    old_content, history = body_str, ""

                if new_content.strip() == old_content.strip():
                    continue

                user_tz = pytz.timezone(self.env.user.tz or 'UTC')
                current_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')

                new_body = f"""{new_content}
    {marker}
    <div style="margin-top: 10px; border-top: 1px solid #eee; padding-top: 5px;">
        <div style="color: #555; font-size: 0.8em; background-color: #fcfcfc; padding: 5px; border-left: 2px solid #ddd;">
            <i>✎ Before (Editado por {self.env.user.name} el {current_time}):</i>
            <div style="color: #888; padding-left: 10px; font-style: italic;">
                {old_content}
            </div>
        </div>
        {history}
    </div>"""

                super(MailMessage, record).write({'body': new_body})

            vals.pop('body', None)

        return super().write(vals)

# =========================
# ACTIVIDADES (mail.activity)
# =========================
class MailActivity(models.Model):
    _inherit = 'mail.activity'


    def _get_unified_tracking_html(self, action_icon, action_title, action_verb, activity, user_tz, changes_html=""):
        create_time_dt = fields.Datetime.to_datetime(activity.create_date)
        if create_time_dt:
            create_time = create_time_dt.astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
        else:
            create_time = 'Desconocida'

        current_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')

        creator_name = activity.create_uid.name or 'Desconocido'
        current_user_name = self.env.user.name or 'Desconocido'

        return f'''
            <div style="color:#555; border-left:3px solid #6c757d; padding-left:10px; font-size: 13px; margin-bottom: 5px;">
                <div style="font-weight: bold; margin-bottom: 5px; color: #333;">{action_icon} {action_title}</div>
                <div style="margin-bottom: 4px; padding-left: 5px; border-left: 2px solid #eee;">
                    <span style="color: #777;">👤 Creado por:</span> {creator_name} <br/>
                    <span style="color: #777;">📅 Fecha de creación:</span> {create_time}
                </div>
                <div style="margin-bottom: 4px; padding-left: 5px; border-left: 2px solid #eee;">
                    <span style="color: #777;">👤 {action_verb} por:</span> {current_user_name} <br/>
                    <span style="color: #777;">🕒 Fecha:</span> {current_time}
                </div>
                {changes_html}
            </div>
        '''

    def action_done(self):
        """ Cubre el botón 'Mark Done' directo del Chatter """
        return super(MailActivity, self.with_context(skip_cancel_log=True)).action_done()

    def action_feedback(self, feedback=False, attachment_ids=None, **kwargs):
        """ 
        Cubre el Wizard y botones con comentarios. 
        Usamos **kwargs para capturar argumentos extra como 'web_send_message' 
        y evitar el TypeError.
        """
        return super(MailActivity, self.with_context(skip_cancel_log=True)).action_feedback(
            feedback=feedback, 
            attachment_ids=attachment_ids, 
            **kwargs
        )

    def _action_done(self, feedback=False, attachment_ids=None):
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        messages = []
        for activity in self:
            changes_html = ""
            if feedback:
                changes_html = f'<div style="margin-top: 8px; border-top: 1px solid #ddd; padding-top: 5px;"><b>Nota:</b> {feedback}</div>'

            html_block = self._get_unified_tracking_html(
                action_icon="✅",
                action_title="Actividad Finalizada",
                action_verb="Finalizado",
                activity=activity,
                user_tz=user_tz,
                changes_html=changes_html
            )
            messages.append(html_block)

        full_message = "<br/>".join(messages) if messages else feedback

        return super(
            MailActivity,
            self.with_context(skip_cancel_log=True)
        )._action_done(
            feedback=full_message,
            attachment_ids=attachment_ids
        )

    def write(self, vals):
        tracked_fields = {
            'summary': 'Resumen',
            'note': 'Nota',
            'date_deadline': 'Fecha límite',
            'user_id': 'Asignado a',
            'activity_type_id': 'Tipo de actividad',
        }

        activities_to_log = self.filtered(lambda a: a.res_model == 'project.task')

        old_values = {}

        for activity in activities_to_log:
            old_values[activity.id] = {}

            for field_name in tracked_fields:
                if field_name not in vals:
                    continue

                field = activity._fields.get(field_name)
                old_value = activity[field_name]

                if field.type == 'many2one':
                    old_values[activity.id][field_name] = old_value.display_name if old_value else ''
                else:
                    old_values[activity.id][field_name] = old_value or ''

        result = super(MailActivity, self).write(vals)

        for activity in activities_to_log:
            changes = []

            for field_name, label in tracked_fields.items():
                if field_name not in vals:
                    continue

                old_value = old_values.get(activity.id, {}).get(field_name, '')

                field = activity._fields.get(field_name)
                new_value = activity[field_name]

                if field.type == 'many2one':
                    new_value = new_value.display_name if new_value else ''
                else:
                    new_value = new_value or ''

                if str(old_value).strip() == str(new_value).strip():
                    continue

                changes.append(f"""
                    <li style="margin-bottom: 3px;">
                        <b>{label}:</b>
                        <span style="color:#888;">{old_value or 'Vacío'}</span>
                        <span style="padding: 0 6px;">→</span>
                        <span style="color:#222;">{new_value or 'Vacío'}</span>
                    </li>
                """)

            if changes:
                user_tz = pytz.timezone(self.env.user.tz or 'UTC')
                changes_html = f'<div style="margin-top: 8px; border-top: 1px solid #ddd; padding-top: 5px;"><ul style="margin:0; padding-left: 15px;">{"".join(changes)}</ul></div>'

                html_block = self._get_unified_tracking_html(
                    action_icon="✎",
                    action_title="Actividad Editada",
                    action_verb="Editado",
                    activity=activity,
                    user_tz=user_tz,
                    changes_html=changes_html
                )

                self.env['mail.message'].create({
                    'body': html_block,
                    'model': activity.res_model,
                    'res_id': activity.res_id,
                    'message_type': 'notification',
                })

        return result

    def unlink(self):
        if not self._context.get('skip_cancel_log'):
            for activity in self:
                if activity.res_model == 'project.task':
                    user_tz = pytz.timezone(self.env.user.tz or 'UTC')

                    nota = f"Nota: {activity.note}" if activity.note else 'Sin nota'
                    changes_html = f'''
                        <div style="margin-top: 8px; border-top: 1px solid #ddd; padding-top: 5px;">
                            <b>Asunto:</b> {activity.summary or activity.activity_type_id.name}<br/>
                            <span style="font-size: 0.9em; color: #555;">{nota}</span>
                        </div>
                    '''

                    html_block = self._get_unified_tracking_html(
                        action_icon="🗙",
                        action_title="Actividad Cancelada",
                        action_verb="Cancelado",
                        activity=activity,
                        user_tz=user_tz,
                        changes_html=changes_html
                    )

                    self.env['mail.message'].create({
                        'body': html_block,
                        'model': activity.res_model,
                        'res_id': activity.res_id,
                        'message_type': 'notification',
                    })
        return super(MailActivity, self).unlink()
