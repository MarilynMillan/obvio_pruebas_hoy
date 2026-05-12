from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = 'project.project'
    _order = "name asc"

    privacy_visibility = fields.Selection(default='followers')

    partner_id = fields.Many2one(
        'res.partner', 
        string='Customer',tracking=True, domain=[('customer_is', '=', True)])
    maintenance_equipment_ids = fields.One2many(
        'maintenance.equipment',
        'project_id',
        string='Equipment creation'
    )

    partner_operator_id = fields.Many2one(
        'res.partner', 
        string='Operator',
        tracking=True,
        domain=[('is_operator', '=', True)]  # Solo mostrar contactos que son operadores
    )
    create_equipment = fields.Boolean(string='Create equipment', default=False)
    #sequence = fields.Char(string='Correlativo', readonly=True, copy=False)
    operation = fields.Char(string='Operator',tracking=True)
    zona_id = fields.Many2one('project.zone', string='Country',tracking=True)
    ubication_id = fields.Many2one(
        'zone.ubication',
        string='Location',
        tracking=True ,
        domain="[('zone_id', '=', zona_id)]"
    )
    tienda_id = fields.Many2one(
        'zone.tienda',
        string='Store',
        tracking=True ,
        domain="[('ubication_id', '=', ubication_id)]"
    )
    type_project = fields.Many2one('type.project', string='Project type', tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    template_project_id = fields.Many2one(
    'project.project',
    string='Project template',
    domain="[('is_template', '=', True)]",
    help="Selecciona un proyecto marcado como plantilla.")
    is_template = fields.Boolean(
    string='Is template',
    default=False,
    help="If checked, this project can be used as a template.")
    original_name = fields.Char(string='Original name', copy=False)
    name_copy = fields.Char(string='Short name',help="Short project name. Used in automatic naming.")
    sequence_new = fields.Char(string='Sequence', readonly=True, copy=False)
    priority = fields.Selection([
        ('0', 'very low'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], string="Prioridad")

    is_subproject = fields.Boolean(string='Main Project',tracking=True ,default=False)
    parent_project_id = fields.Many2one('project.project', string='Subproject Suffix', domain=[('is_subproject', '=', True)])
    subproject_suffix = fields.Char(string='Suffix',tracking=True, size=2)
    use_suffix = fields.Boolean(string='Subproject', default=False, tracking=True)

    completion_date = fields.Date(string="Completion Date")
    is_manager_custom = fields.Boolean(compute='_compute_is_manager_custom')


    def _compute_is_manager_custom(self):
        is_manager = self.env.user.has_group('project.group_project_manager') or self.env.uid == 1
        for reg in self:
            reg.is_manager_custom = is_manager

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        return super()._get_view_cache_key(view_id=view_id, view_type=view_type, **options) + (
            self.env.company.id,
        )

    @api.model
    def _get_root_analytic_plans(self):
        project_plan, other_plans = self.env["account.analytic.plan"]._get_all_plans()
        return project_plan + other_plans

    @api.model
    def _get_analytic_plan_company_map(self):
        root_plans = self._get_root_analytic_plans()
        company_map = defaultdict(set)

        analytic_accounts_data = self.env["account.analytic.account"].sudo()._read_group(
            [
                ("root_plan_id", "in", root_plans.ids),
                ("company_id", "!=", False),
            ],
            ["root_plan_id", "company_id"],
            ["__count"],
        )
        for root_plan, company, _count in analytic_accounts_data:
            if root_plan and company:
                company_map[root_plan.id].add(company.id)

        return {
            plan._column_name(): {
                "company_ids": sorted(company_map.get(plan.id, set())),
                "show_on_all_companies": bool(plan.show_on_all_companies),
            }
            for plan in root_plans
            if plan._column_name() in self._fields
        }

    @api.model
    def _get_resettable_analytic_field_names(self):
        return [
            "account_id",
            *[
                plan._column_name()
                for plan in self._get_root_analytic_plans()
                if plan._column_name() in self._fields
            ],
        ]

    @api.model
    def _prepare_analytic_reset_vals(self):
        return {field_name: False for field_name in self._get_resettable_analytic_field_names()}

    def _get_company_visible_analytic_plan_field_names(self, company=None):
        company = company or self.env.company
        company_id = company.id if company else False
        visible_field_names = set()

        for field_name, plan_visibility in self._get_analytic_plan_company_map().items():
            if plan_visibility["show_on_all_companies"] or company_id in plan_visibility["company_ids"]:
                visible_field_names.add(field_name)

        return visible_field_names

    @api.onchange("company_id")
    def _onchange_company_id(self):
        super()._onchange_company_id()
        reset_vals = self._prepare_analytic_reset_vals()
        for project in self:
            project.update(reset_vals)

    def _patch_view(self, arch, view, view_type):
        arch, view = super()._patch_view(arch, view, view_type)

        if view_type != "form" or self._context.get("studio"):
            return arch, view

        analytic_plan_company_map = self._get_analytic_plan_company_map()
        analytic_page_nodes = arch.xpath("//page[@name='analytic']")
        if not analytic_page_nodes:
            return arch, view

        analytic_page = analytic_page_nodes[0]
        for field_node in analytic_page.xpath(".//field[@name]"):
            field_name = field_node.get("name")
            plan_visibility = analytic_plan_company_map.get(field_name)
            if not plan_visibility or plan_visibility["show_on_all_companies"]:
                continue

            company_ids = plan_visibility["company_ids"]
            invisible_expr = (
                "True" if not company_ids
                else f"company_id not in {company_ids}"
            )
            existing_invisible = field_node.get("invisible")
            field_node.set(
                "invisible",
                f"({existing_invisible}) or ({invisible_expr})" if existing_invisible else invisible_expr,
            )

        return arch, view

    @api.onchange('parent_project_id')
    def _onchange_parent_project_id(self):
        if self.use_suffix and self.parent_project_id:
            parent = self.parent_project_id

            self.partner_id = parent.partner_id
            self.type_project = parent.type_project
            self.zona_id = parent.zona_id
            self.partner_operator_id = parent.partner_operator_id
            self.ubication_id = parent.ubication_id
            self.tienda_id = parent.tienda_id
            self.name_copy = parent.name_copy or parent.original_name or parent.name
            self.date_start = parent.date_start
            self.date = parent.date
            self.completion_date = parent.completion_date

            # Heredar plantilla y etiquetas
            self.template_project_id = parent.template_project_id
            self.tag_ids = [(6, 0, parent.tag_ids.ids)]

    @api.constrains('use_suffix', 'parent_project_id')
    def _check_parent_required_for_subproject(self):
        for record in self:
            if record.use_suffix and not record.parent_project_id:
                raise UserError(_("You must select a main project to create a subproject."))
                


    @api.onchange('template_project_id')
    def _onchange_template_project_id(self):
        if self.template_project_id:
            return {
                'warning': {
                    'title': _('Validation'),
                    'message': _(
                        "Please make sure the template '%s', is the correct one."
                    ) % self.template_project_id.name
                }
            }

     # 1. Onchange para el País/Zona
    @api.onchange('zona_id')
    def _onchange_zona_id(self):
        """
        Limpia la Localidad y la Tienda si la Localidad actual no pertenece
        al nuevo País/Zona.
        """
        # Limpia Localidad si el valor actual no está en el nuevo País/Zona.
        if self.ubication_id and self.ubication_id.zone_id != self.zona_id:
            self.ubication_id = False
        


    # 2. Onchange para la Localidad
    @api.onchange('ubication_id')
    def _onchange_ubication_id(self):
        """
        Limpia la Tienda si la Tienda actual no pertenece a la nueva Localidad.
        """
        # Limpia Tienda si el valor actual no está en la nueva Localidad.
        if self.tienda_id and self.tienda_id.ubication_id != self.ubication_id:
            self.tienda_id = False

        # Si ubication_id cambia, también nos aseguramos de que el País/Zona esté asociado
        # (Aunque el dominio en la vista ya ayuda con esto, es una buena práctica defensiva).
        if self.ubication_id and self.ubication_id.zone_id != self.zona_id:
            self.zona_id = self.ubication_id.zone_id

    @api.constrains('zona_id', 'ubication_id', 'tienda_id')
    def _check_location_hierarchy(self):
        """
        Verifica la coherencia entre País, Localidad y Tienda.
        Se ejecuta en create y write.
        """
        for record in self:
            # 1. Verificar Localidad vs. País (Zona)
            if record.ubication_id and record.ubication_id.zone_id != record.zona_id:
                if record.zona_id:
                    raise UserError(
                        ("The Location"
                         f"'{record.ubication_id.display_name}' does not belong to the country "
                         f"'{record.zona_id.display_name}'.")
                    )
                else:
                    raise UserError(
                        ("You must select a country "
                         f"Valid for the Locality '{record.ubication_id.display_name}'.")
                    )

            # 2. Verificar Tienda vs. Localidad
            if record.tienda_id and record.tienda_id.ubication_id != record.ubication_id:
                if record.ubication_id:
                    raise UserError(
                        ("The Store "
                         f"'{record.tienda_id.display_name}' it is not associated with the locality. "
                         f"'{record.ubication_id.display_name}'.")
                    )
                else:
                    raise UserError(
                        ("You must select a location "
                         f"Valid for the Store '{record.tienda_id.display_name}'.")
                    )


    @api.onchange('is_template', 'name_copy')
    def _onchange_nomenclatura(self):
        """ Actualiza el 'name' en la vista en tiempo real sin duplicar prefijos """
        for project in self:
            # Extraemos el valor puro del nombre corto
            # Si ya tiene 'TEMPLATE - ', lo eliminamos temporalmente para procesarlo
            raw_short = (project.name_copy or '').replace('TEMPLATE - ', '').strip()
            
            # Si el valor es una barra sola (/) o está vacío, lo limpiamos
            if raw_short == "/":
                raw_short = ""

            if project.is_template:
                # Formato rígido: Siempre TEMPLATE - seguido del nombre limpio
                project.name = f"TEMPLATE - {raw_short}" if raw_short else "TEMPLATE"
            else:
                # Si no es plantilla, el nombre en la vista será solo el nombre corto
                project.name = raw_short

    def _get_project_full_name(self):
        self.ensure_one()

        p_short = (self.name_copy or self.original_name or '').replace('TEMPLATE - ', '').strip()
        if p_short == "/":
            p_short = ""

        if self.is_template:
            return f"TEMPLATE - {p_short}" if p_short else "TEMPLATE"

        parts = [
            self.sequence_new or '',
            self.type_project.alias_name or '',
            self.partner_id.alias_name or '',
            p_short,
            self.partner_operator_id.codigo_operator or '',
            self.tienda_id.tienda or '',
            self.ubication_id.zone or '',
            self.zona_id.code or '',
        ]

        return " - ".join(p for p in parts if p) or p_short or self.sequence_new or "/"   

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_template = vals.get('is_template', False)
            is_sub = vals.get('is_subproject', False)
            use_suffix = vals.get('use_suffix', False)
            parent_id = vals.get('parent_project_id')

            # --- 1. PLANTILLA ---
            if is_template:
                vals.update({
                    'sequence_new': 'TEMPLATE',
                    'account_id': False,
                    'use_documents': False,
                    'documents_folder_id': False,
                })

            # --- 2. SUBPROYECTO DERIVADO DEL PROYECTO PRINCIPAL ---
            elif use_suffix:
                if not parent_id:
                    raise UserError(_("You must select a main project to create a subproject."))

                parent = self.env['project.project'].browse(parent_id)

                if not parent.exists():
                    raise UserError(_("The selected main project does not exist."))

                suffix = (vals.get('subproject_suffix') or '').strip().upper()

                if not suffix:
                    raise UserError(_("You must enter a suffix for the subproject. Example: B, C, D."))

                if suffix == 'A':
                    raise UserError(_("The suffix 'A' is for the main project. Use B, C, D..."))

                if not parent.template_project_id:
                    raise UserError(_(
                        "The main project does not have an assigned template. "
                        "Tasks cannot be copied to the subproject."
                    ))

                # Heredar campos del proyecto principal
                def _set_if_empty(field_name, value):
                    if vals.get(field_name) in [False, None, '', []]:
                        vals[field_name] = value

                _set_if_empty('type_project', parent.type_project.id or False)
                _set_if_empty('partner_id', parent.partner_id.id or False)
                _set_if_empty('zona_id', parent.zona_id.id or False)
                _set_if_empty('partner_operator_id', parent.partner_operator_id.id or False)
                _set_if_empty('ubication_id', parent.ubication_id.id or False)
                _set_if_empty('tienda_id', parent.tienda_id.id or False)
                _set_if_empty('name_copy', parent.name_copy or parent.original_name or parent.name or '')
                _set_if_empty('date_start', parent.date_start)
                _set_if_empty('date', parent.date)
                _set_if_empty('completion_date', parent.completion_date)

                # Tags heredados solo si no llegaron valores manuales
                if not vals.get('tag_ids'):
                    vals['tag_ids'] = [(6, 0, parent.tag_ids.ids)]

                # Plantilla: puede venir manual o heredada del padre
                if not vals.get('template_project_id') and not parent.template_project_id:
                    raise UserError(_(
                        "You must select a template, or the main project must have an assigned template."
                    ))

                _set_if_empty('template_project_id', parent.template_project_id.id or False)

                # Secuencia heredada del proyecto principal
                if parent.sequence_new and parent.sequence_new != 'TEMPLATE':
                    base_seq = parent.sequence_new
                    parts = base_seq.split(' ')

                    if parts and parts[-1].isalpha() and len(parts[-1]) <= 2:
                        base_seq = ' '.join(parts[:-1])

                    vals['sequence_new'] = f"{base_seq} {suffix}"
                else:
                    vals['sequence_new'] = self.env['ir.sequence'].next_by_code('project.project') or ''

                # Nombre provisional requerido
                vals['name'] = vals['name_copy'] or vals['sequence_new'] or '/'

            # --- 3. PROYECTO PRINCIPAL ---
            elif is_sub and not use_suffix:
                seq = self.env['ir.sequence'].next_by_code('project.project') or ''
                vals['sequence_new'] = f"{seq} A" if seq else ''

            # --- 4. PROYECTO NORMAL ---
            else:
                if not vals.get('sequence_new') or vals.get('sequence_new') in ['New', '/', False]:
                    vals['sequence_new'] = self.env['ir.sequence'].next_by_code('project.project') or ''

            # --- 5. NOMENCLATURA ---
            p_short = (
                vals.get('name_copy')
                or vals.get('name')
                or ''
            ).replace('TEMPLATE - ', '').strip()

            if p_short == "/":
                p_short = ""

            vals['name_copy'] = p_short
            vals['original_name'] = p_short

            if is_template:
                vals['name'] = f"TEMPLATE - {p_short}" if p_short else "TEMPLATE"
            else:
                t_alias = self.env['type.project'].browse(vals.get('type_project')).alias_name or ''
                partner_alias = self.env['res.partner'].browse(vals.get('partner_id')).alias_name or ''
                op_code = self.env['res.partner'].browse(vals.get('partner_operator_id')).codigo_operator or ''
                z_code = self.env['project.zone'].browse(vals.get('zona_id')).code or ''
                t_name = self.env['zone.tienda'].browse(vals.get('tienda_id')).tienda or ''
                u_name = self.env['zone.ubication'].browse(vals.get('ubication_id')).zone or ''

                display_seq = vals.get('sequence_new', '')

                name_parts = [
                    p for p in [
                        display_seq,
                        t_alias,
                        partner_alias,
                        p_short,
                        op_code,
                        t_name,
                        u_name,
                        z_code,
                    ] if p
                ]

                vals['name'] = " - ".join(name_parts) if name_parts else (p_short or vals.get('sequence_new') or '/')

        # --- 6. CREACIÓN REAL ---
        projects = super(ProjectProject, self).create(vals_list)

        # --- 7. POST-CREACIÓN ---
        for vals, project in zip(vals_list, projects):

            # Si es plantilla, eliminar cuenta analítica y documentos
            if project.is_template:
                if project.account_id:
                    analytic_account = project.account_id
                    project.write({'account_id': False})
                    analytic_account.sudo().unlink()

                project.write({
                    'use_documents': False,
                    'documents_folder_id': False,
                })
                continue

            # Actualizar nombre de cuenta analítica
            if project.account_id:
                project.account_id.name = project.name

            # Copiar tareas desde la plantilla asignada/heredada
            template = project.template_project_id

            if template:
                project_user_ids = [(6, 0, [project.user_id.id])] if project.user_id else False

                for task in template.task_ids:
                    task.with_context(copy_project=True).copy({
                        'project_id': project.id,
                        'name': task.name,
                        'stage_id': task.stage_id.id,
                        'sequence': task.sequence,
                        'tag_ids': [(6, 0, task.tag_ids.ids)],
                        'user_ids': project_user_ids,
                    })

        return projects

    def copy(self, default=None):
        default = dict(default or {})
        if default.get('sale_line_id'):
            default.setdefault('privacy_visibility', 'followers')
        return super().copy(default)



    @api.constrains('subproject_suffix', 'is_subproject')
    def _check_suffix_not_a(self):
        for record in self:
            if record.is_subproject and record.subproject_suffix:
                if record.subproject_suffix.upper() == 'A' and record.parent_project_id:
                    raise UserError(_("He suffix 'A' is for the main project. For derived subprojects use B, C, D..."))

    @api.constrains('is_subproject', 'use_suffix')
    def _check_project_type_exclusive(self):
        for record in self:
            if record.is_subproject and record.use_suffix:
                raise UserError(_(
                    "A project cannot be Main Project and Subproject at the same time."
                ))


    def unlink(self):
        return super(ProjectProject, self.with_context(is_unlinking_parent=True)).unlink()


    def write(self, vals):
        protected_fields = [
            'operation', 'zona_id', 'ubication_id', 'tienda_id',
            'type_project', 'partner_id', 'partner_operator_id'
        ]

        # 0. BLOQUEOS DE SUBPROYECTO / PROYECTO PRINCIPAL
        for project in self:
            # No permitir quitar Proyecto principal después de creado
            if 'is_subproject' in vals and vals.get('is_subproject') is False and project.is_subproject:
                raise UserError(_(
                    "You cannot remove the Main Project checkmark after it has been created."
                ))

            # No permitir cambiar el sufijo después de creado
            if 'subproject_suffix' in vals and project.id and project.subproject_suffix:
                new_suffix = (vals.get('subproject_suffix') or '').strip().upper()
                old_suffix = (project.subproject_suffix or '').strip().upper()

                if new_suffix != old_suffix:
                    raise UserError(_(
                        "You cannot change the suffix after created because it is part of the project's sequential number."
                    ))

            # No permitir quitar Subproject si ya tiene proyecto principal
            if 'use_suffix' in vals and vals.get('use_suffix') is False and project.use_suffix and project.parent_project_id:
                raise UserError(_(
                    "You cannot remove the Subproject checkmark after you have selected a main project."
                ))

            # Si activan subproyecto, debe tener proyecto principal
            new_use_suffix = vals.get('use_suffix', project.use_suffix)
            new_parent_id = vals.get('parent_project_id', project.parent_project_id.id)

            if new_use_suffix and not new_parent_id:
                raise UserError(_(
                    "You must select a main project to create a subproject."
                ))

            # Validar sufijo para subproyecto
            if new_use_suffix:
                suffix = (vals.get('subproject_suffix', project.subproject_suffix or '') or '').strip().upper()

                if not suffix:
                    raise UserError(_(
                        "DYou must enter a suffix for the subproject. Example: B, C, D."
                    ))

                if suffix == 'A':
                    raise UserError(_(
                        "The suffix 'A' is for the main project. Use B, C, D..."
                    ))

        # 1. SEGURIDAD: Solo Manager o Responsable pueden editar campos críticos
        if not self.env.user.has_group('project.group_project_manager'):
            current_user = self.env.user
            for project in self:
                if (
                    not project.is_template
                    and any(f in vals for f in protected_fields)
                    and project.user_id != current_user
                ):
                    raise UserError(_(
                        "You cannot modify critical fields in an active project. Contact a Manager."
                    ))

        # 2. PRE-PROCESO: Si se marca como plantilla ahora
        if vals.get('is_template'):
            vals.update({
                'account_id': False,
                'sequence_new': 'TEMPLATE',
                'use_documents': False,
                'documents_folder_id': False,
            })

        # 2.1 PRE-PROCESO: Si se convierte/actualiza como subproyecto, heredar del padre
        if vals.get('use_suffix') or vals.get('parent_project_id'):
            for project in self:
                parent_id = vals.get('parent_project_id') or project.parent_project_id.id

                if parent_id:
                    parent = self.env['project.project'].browse(parent_id)

                    if not parent.exists():
                        raise UserError(_("The selected main project does not exist."))

                    if not parent.template_project_id:
                        raise UserError(_(
                            "The main project does not have an assigned template."
                            "Tasks cannot be copied to the subproject."
                        ))

                    vals.update({
                        'type_project': parent.type_project.id or False,
                        'partner_id': parent.partner_id.id or False,
                        'zona_id': parent.zona_id.id or False,
                        'partner_operator_id': parent.partner_operator_id.id or False,
                        'ubication_id': parent.ubication_id.id or False,
                        'tienda_id': parent.tienda_id.id or False,
                        'name_copy': parent.name_copy or parent.original_name or '',
                        'date_start': parent.date_start,
                        'date': parent.date,
                        'completion_date': parent.completion_date,
                        'template_project_id': parent.template_project_id.id,
                    })

        # Capturamos estado anterior
        template_status_before = {p.id: p.is_template for p in self}

        # Para saber si hay que recargar tareas después del write
        reload_tasks_from_template = bool(vals.get('template_project_id'))

        # 3. GUARDADO BASE
        res = super(ProjectProject, self).write(vals)

        # 4. CARGA DE TAREAS
        if reload_tasks_from_template:
            for project in self:
                if project.is_template:
                    continue

                template = project.template_project_id

                if template:
                    project.task_ids.unlink()

                    project_user_ids = [(6, 0, [project.user_id.id])] if project.user_id else False

                    for task in template.task_ids:
                        task.with_context(copy_project=True).copy({
                            'project_id': project.id,
                            'name': task.name,
                            'stage_id': task.stage_id.id,
                            'sequence': task.sequence,
                            'tag_ids': [(6, 0, task.tag_ids.ids)],
                            'user_ids': project_user_ids,
                        })

        # 5. POST-PROCESO
        campos_nom = [
            'type_project', 'partner_id', 'partner_operator_id', 'zona_id',
            'tienda_id', 'ubication_id', 'name_copy', 'is_subproject',
            'parent_project_id', 'subproject_suffix', 'use_suffix', 'is_template'
        ]

        for project in self:
            was_template = template_status_before.get(project.id)
            is_now_template = project.is_template

            # CASO A: PASÓ A SER PLANTILLA
            if is_now_template:
                if project.account_id:
                    acc = project.account_id
                    super(ProjectProject, project).write({'account_id': False})
                    acc.sudo().unlink()

                p_short = (project.name_copy or '').replace('TEMPLATE - ', '').strip()
                new_name = f"TEMPLATE - {p_short}" if p_short else "TEMPLATE"

                if project.name != new_name:
                    super(ProjectProject, project).write({
                        'name': new_name,
                        'sequence_new': 'TEMPLATE',
                    })
                continue

            # CASO B: REVERSA DE PLANTILLA A PROYECTO REAL
            if was_template and not is_now_template:
                new_seq = self.env['ir.sequence'].next_by_code('project.project') or ''

                if project.is_subproject and not project.use_suffix:
                    new_seq = f"{new_seq} A"

                plan = self.env['account.analytic.plan'].sudo().search([], limit=1)

                analytic_vals = {
                    'name': project.name,
                    'company_id': project.company_id.id,
                    'partner_id': project.partner_id.id,
                    'plan_id': plan.id if plan else False,
                }

                new_acc = self.env['account.analytic.account'].sudo().create(analytic_vals)

                super(ProjectProject, project).write({
                    'sequence_new': new_seq,
                    'account_id': new_acc.id,
                    'use_documents': True,
                })

            # 6. NOMENCLATURA
            if any(campo in vals for campo in campos_nom) or (was_template and not is_now_template):
                seq = project.sequence_new

                if project.is_subproject:
                    if project.use_suffix and project.parent_project_id:
                        parent_seq = project.parent_project_id.sequence_new
                        suffix = (project.subproject_suffix or '').strip().upper()

                        if parent_seq and parent_seq != 'TEMPLATE':
                            base_seq = parent_seq
                            parts_seq = base_seq.split(' ')

                            if parts_seq and parts_seq[-1].isalpha() and len(parts_seq[-1]) <= 2:
                                base_seq = ' '.join(parts_seq[:-1])

                            seq = f"{base_seq} {suffix}" if suffix else base_seq

                    elif not project.use_suffix and seq and seq != 'TEMPLATE':
                        parts_seq = seq.split(' ')

                        if not (parts_seq and parts_seq[-1].isalpha()):
                            seq = f"{seq} A"

                p_short = (project.name_copy or '').replace('TEMPLATE - ', '').strip()

                if p_short == "/":
                    p_short = ""

                t_alias = project.type_project.alias_name or ''
                part_alias = project.partner_id.alias_name or ''
                op = project.partner_operator_id.codigo_operator or ''
                z = project.zona_id.code or ''
                t = project.tienda_id.tienda or ''
                u = project.ubication_id.zone or ''

                display_seq = seq if seq and seq != '/' else ''

                parts = [
                    p for p in [
                        display_seq,
                        t_alias,
                        part_alias,
                        p_short,
                        op,
                        t,
                        u,
                        z,
                    ] if p
                ]

                final_name = " - ".join(parts) if parts else p_short

                if project.name != final_name or project.sequence_new != seq:
                    super(ProjectProject, project).write({
                        'name': final_name,
                        'sequence_new': seq,
                    })

                    if project.account_id:
                        project.account_id.sudo().write({'name': final_name})

        return res


    def create_maintenance_equipment(self):
        self.ensure_one()  # Asegura que solo se esté trabajando con un registro a la vez

        # Obtener los valores necesarios
        partner_alias = self.partner_id.alias_name or ''
        country_code = self.zona_id.code or ''  # Código del país
        zone_name = self.ubication_id.zone or ''  # Nombre de la zona
        tienda_name = self.tienda_id.tienda or ''  # Nombre de la tienda
        operator_code = self.partner_operator_id.codigo_operator or ''  # Código del operador

        # Construir la información de zona, tienda y país
        zona_info = f"{tienda_name} - {zone_name} - {country_code}"

        # Concatenar el nombre del equipo
        equipment_name = f"{partner_alias} - {operator_code} - {zona_info}"

        # Crear un nuevo equipo y asociarlo con el proyecto
        equipment = self.env['maintenance.equipment'].create({
            'name': equipment_name,
            'project_id': self.id,  # Asociar el equipo con el proyecto
            'project_sequence': self.sequence_new,  # Guardar la secuencia del proyecto en el nuevo campo
            # Agrega otros campos necesarios aquí
        })

        # Retornar una acción para abrir la vista de formulario del equipo creado
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.equipment',
            'view_mode': 'form',
            'view_id': self.env.ref('maintenance.hr_equipment_view_form').id,  # Especificar el ID de la vista de formulario
            'res_id': equipment.id,
            'target': 'current',
        }
