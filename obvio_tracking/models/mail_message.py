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
            create_time = fields.Datetime.to_datetime(record.create_date).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if record.create_date else 'Desconocido'
            creator_name = record.create_uid.name or 'Desconocido'
            user_name = self.env.user.name or 'Desconocido'

            new_body = f"""
                <div class="is_deleted_message" style="color: #555; border-left: 3px solid #6c757d; padding-left: 10px; background-color: #fcfcfc; padding: 5px; margin-bottom: 5px;">
                    <small>
                        <i>🗑️ Mensaje eliminado por {user_name} el {current_time}</i><br/>
                        <i>📅 Creado originalmente por {creator_name} el {create_time}</i>
                    </small>
                    <div style="margin-top: 5px; text-decoration: line-through; color: #999; font-style: italic;">
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
                create_time = fields.Datetime.to_datetime(record.create_date).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if record.create_date else 'Desconocido'
                creator_name = record.create_uid.name or 'Desconocido'
                user_name = self.env.user.name or 'Desconocido'

                new_body = f"""{new_content}
    {marker}
    <div style="margin-top: 10px; border-top: 1px solid #eee; padding-top: 5px;">
        <div style="color: #555; border-left: 3px solid #6c757d; padding-left: 10px; background-color: #fcfcfc; padding: 5px; margin-bottom: 5px;">
            <small>
                <i>✎ Mensaje editado por {user_name} el {current_time}</i><br/>
                <i>📅 Creado originalmente por {creator_name} el {create_time}</i>
            </small>
            <div style="margin-top: 5px; color: #888; font-style: italic;">
                <i>Anterior:</i><br/>
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

    """def _action_done(self, feedback=False, attachment_ids=None):
        return super(MailActivity, self.with_context(skip_cancel_log=True))._action_done(
            feedback=feedback, 
            attachment_ids=attachment_ids
        )"""

    def _action_done(self, feedback=False, attachment_ids=None):
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        now_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
        user_name = self.env.user.name or 'Desconocido'
        content = feedback or ''

        messages = []

        for activity in self:
            create_time = fields.Datetime.to_datetime(
                activity.create_date
            ).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if activity.create_date else 'Desconocido'
            creator_name = activity.create_uid.name or 'Desconocido'

            html_msg = f"""
                <div style="color: #555; border-left: 3px solid #6c757d; padding-left: 10px; background-color: #fcfcfc; padding: 5px; margin-bottom: 5px;">
                    <small>
                        <i>✅ Actividad marcada como hecha por {user_name} el {now_time}</i><br/>
                        <i>📅 Creada originalmente por {creator_name} el {create_time}</i>
                    </small>
                    <div style="margin-top: 5px; color: #333;">
                        {content}
                    </div>
                </div>
            """
            messages.append(html_msg)

        full_message = "".join(messages)

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
                    <li>
                        <b>{label}:</b>
                        <span style="color:#888;">{old_value or 'Vacío'}</span>
                        <span style="padding: 0 6px;">→</span>
                        <span style="color:#222;">{new_value or 'Vacío'}</span>
                    </li>
                """)

            if changes:
                user_tz = pytz.timezone(self.env.user.tz or 'UTC')
                current_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
                create_time = fields.Datetime.to_datetime(activity.create_date).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if activity.create_date else 'Desconocido'
                creator_name = activity.create_uid.name or 'Desconocido'
                user_name = self.env.user.name or 'Desconocido'

                self.env['mail.message'].create({
                    'body': f"""
                        <div style="color: #555; border-left: 3px solid #6c757d; padding-left: 10px; background-color: #fcfcfc; padding: 5px; margin-bottom: 5px;">
                            <small>
                                <i>✎ Actividad editada por {user_name} el {current_time}</i><br/>
                                <i>📅 Creada originalmente por {creator_name} el {create_time}</i>
                            </small>
                            <ul style="margin:6px 0 0 15px; padding:0; color: #333;">
                                {''.join(changes)}
                            </ul>
                        </div>
                    """,
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
                    current_time = fields.Datetime.now().astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
                    create_time = fields.Datetime.to_datetime(activity.create_date).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if activity.create_date else 'Desconocido'
                    creator_name = activity.create_uid.name or 'Desconocido'
                    user_name = self.env.user.name or 'Desconocido'

                    self.env['mail.message'].create({
                        'body': f"""
                            <div style="color: #555; border-left: 3px solid #6c757d; padding-left: 10px; background-color: #fcfcfc; padding: 5px; margin-bottom: 5px;">
                                <small>
                                    <i>❌ Actividad cancelada por {user_name} el {current_time}</i><br/>
                                    <i>📅 Creada originalmente por {creator_name} el {create_time}</i>
                                </small>
                                <div style="margin-top: 5px; color: #333;">
                                    <b>Asunto:</b> {activity.summary or activity.activity_type_id.name}<br/>
                                    <span style="font-size: 0.9em;">Nota: {activity.note or 'Sin nota'}</span>
                                </div>
                            </div>
                        """,
                        'model': activity.res_model,
                        'res_id': activity.res_id,
                        'message_type': 'notification',
                    })
        return super(MailActivity, self).unlink() 

   