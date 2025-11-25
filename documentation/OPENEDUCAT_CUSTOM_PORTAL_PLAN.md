# OpenEducat Custom Portal Development Plan
**Institution:** UEIPAB - Instituto Privado Andrés Bello
**Date:** 2025-11-25
**Status:** PLANNING

---

## 1. Requirements Summary

### Portal Users
| Role | Access Type | Description |
|------|-------------|-------------|
| **Students** | Self-service | View own academic data |
| **Parents/Representatives** | Child monitoring | View children's academic data |

### Education Levels
- **PreSchool:** 1er a 3er grupo (Maternal, Pre-kinder, Kinder)
- **Primary:** 1er a 6to grado
- **Secondary:** 1er a 5to año

### Priority Features (All 4 selected)
1. **Grades/Calificaciones** - View exam results and academic performance
2. **Attendance/Asistencia** - View attendance records and absences
3. **Schedule/Horario** - View class timetable
4. **Assignments/Tareas** - View and submit homework

---

## 2. Technical Architecture

### New Module: `ueipab_education_portal`

```
ueipab_education_portal/
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   ├── portal_main.py          # Main portal routes
│   ├── portal_grades.py        # /my/grades
│   ├── portal_attendance.py    # /my/attendance
│   ├── portal_schedule.py      # /my/schedule
│   └── portal_assignments.py   # /my/assignments
├── models/
│   ├── __init__.py
│   └── res_users.py            # Extend user for parent-child linking
├── security/
│   ├── ir.model.access.csv
│   └── portal_security.xml     # Record rules for portal access
├── views/
│   └── portal_templates.xml    # Portal menu items
└── static/
    └── src/
        └── xml/
            ├── portal_grades.xml
            ├── portal_attendance.xml
            ├── portal_schedule.xml
            └── portal_assignments.xml
```

### Data Flow

```
Student Login → Check op.student.user_id → Fetch student data → Render portal

Parent Login → Check op.parent → Get child_ids → Fetch children data → Render portal
```

---

## 3. Portal Routes Design

### Student Portal Routes

| Route | Description | Data Source |
|-------|-------------|-------------|
| `/my/grades` | View exam results | `op.exam.attendees` |
| `/my/grades/<exam_id>` | Exam detail | `op.exam.attendees` |
| `/my/attendance` | Attendance summary | `op.attendance.line` |
| `/my/schedule` | Weekly timetable | `op.session` |
| `/my/assignments` | Assignment list | `op.assignment` |
| `/my/assignments/<id>` | Assignment detail/submit | `op.assignment.sub.line` |

### Parent Portal Routes

| Route | Description |
|-------|-------------|
| `/my/children` | List of children |
| `/my/child/<id>/grades` | Child's grades |
| `/my/child/<id>/attendance` | Child's attendance |
| `/my/child/<id>/schedule` | Child's schedule |

---

## 4. OpenEducat CE Models Used

### Core Models (Available)
```python
op.student          # Student records (user_id links to portal user)
op.faculty          # Teacher records
op.course           # Courses (e.g., "Educación Primaria")
op.batch            # Class sections (e.g., "1er Grado A")
op.subject          # Subjects (e.g., "Matemáticas")
op.student.course   # Student-Course enrollment
```

### Academic Models (Available)
```python
op.exam             # Exam definitions
op.exam.attendees   # Student exam results (marks, status)
op.attendance.sheet # Attendance sheet (date, batch)
op.attendance.line  # Individual attendance (student, present/absent)
op.session          # Timetable sessions
op.assignment       # Homework assignments
op.assignment.sub.line  # Assignment submissions
```

### Parent Model (Available)
```python
op.parent           # Parent record with child linking
```

---

## 5. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create module structure
- [ ] Setup portal security rules
- [ ] Implement base portal controller
- [ ] Add portal menu items (My Grades, My Attendance, etc.)

### Phase 2: Grades Portal (Week 2)
- [ ] `/my/grades` - List all exams with results
- [ ] `/my/grades/<id>` - Detailed exam view
- [ ] Grade statistics (average, trends)
- [ ] Parent view: `/my/child/<id>/grades`

### Phase 3: Attendance Portal (Week 3)
- [ ] `/my/attendance` - Monthly attendance view
- [ ] Attendance statistics (% present, absences)
- [ ] Calendar view of attendance
- [ ] Parent view: `/my/child/<id>/attendance`

### Phase 4: Schedule Portal (Week 4)
- [ ] `/my/schedule` - Weekly timetable
- [ ] Current day highlighting
- [ ] Subject/teacher info display
- [ ] Parent view: `/my/child/<id>/schedule`

### Phase 5: Assignments Portal (Week 5)
- [ ] `/my/assignments` - List pending/completed
- [ ] `/my/assignments/<id>` - Detail view
- [ ] File submission capability
- [ ] Due date tracking

### Phase 6: Parent Portal (Week 6)
- [ ] `/my/children` - Children list
- [ ] Child selector for all views
- [ ] Notification preferences

---

## 6. UI/UX Design

### Portal Menu Structure
```
My Portal
├── 📊 Calificaciones (Grades)
├── ✅ Asistencia (Attendance)
├── 📅 Horario (Schedule)
├── 📝 Tareas (Assignments)
└── 👨‍👩‍👧 Mis Hijos (Parents only)
```

### Responsive Design
- Mobile-first approach (many Venezuelan parents use phones)
- Bootstrap 5 (Odoo 17 standard)
- Spanish language throughout

### Sample Grade View
```
┌─────────────────────────────────────────────────┐
│  📊 MIS CALIFICACIONES                          │
│  Estudiante: Luis Pérez | 3er Grado A           │
├─────────────────────────────────────────────────┤
│  MATEMÁTICAS                                    │
│  ├── Examen Parcial 1: 18/20 (90%)    ✅       │
│  ├── Examen Parcial 2: 16/20 (80%)    ✅       │
│  └── Promedio: 17/20 (85%)                      │
│                                                 │
│  LENGUA Y LITERATURA                            │
│  ├── Examen Parcial 1: 15/20 (75%)    ✅       │
│  └── Promedio: 15/20 (75%)                      │
└─────────────────────────────────────────────────┘
```

---

## 7. Security Considerations

### Record Rules
```xml
<!-- Student can only see own records -->
<record id="student_grade_rule" model="ir.rule">
    <field name="name">Student: Own Grades Only</field>
    <field name="model_id" ref="openeducat_exam.model_op_exam_attendees"/>
    <field name="domain_force">[('student_id.user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
</record>

<!-- Parent can see children's records -->
<record id="parent_child_grade_rule" model="ir.rule">
    <field name="name">Parent: Children Grades Only</field>
    <field name="model_id" ref="openeducat_exam.model_op_exam_attendees"/>
    <field name="domain_force">[('student_id.parent_ids.user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
</record>
```

### Access Control
- Portal users: Read-only access to academic data
- No write access except assignment submissions
- Parent can only view linked children

---

## 8. Venezuelan Adaptations

### Grading System
- Venezuelan scale: 1-20 (passing: 10+)
- Show both numeric and qualitative (Excelente, Bueno, Regular, Deficiente)

### Academic Calendar
- Venezuelan school year: September - July
- Three lapsos (terms) per year

### Language
- All UI in Spanish
- Venezuelan date format: DD/MM/YYYY

---

## 9. Dependencies

### Required Modules
```python
'depends': [
    'portal',              # Odoo base portal
    'openeducat_core',     # Students, courses, batches
    'openeducat_exam',     # Grades/exams
    'openeducat_attendance', # Attendance
    'openeducat_timetable',  # Schedule
    'openeducat_assignment', # Homework
    'openeducat_parent',     # Parent portal
],
```

---

## 10. Estimated Effort

| Phase | Features | Est. Hours |
|-------|----------|------------|
| Phase 1 | Foundation | 8-12 hrs |
| Phase 2 | Grades Portal | 12-16 hrs |
| Phase 3 | Attendance Portal | 8-12 hrs |
| Phase 4 | Schedule Portal | 8-12 hrs |
| Phase 5 | Assignments Portal | 12-16 hrs |
| Phase 6 | Parent Portal | 8-12 hrs |
| **Total** | | **56-80 hrs** |

---

## 11. Next Steps

1. **Review & Approve** this plan
2. **Create module skeleton** in `/mnt/extra-addons/`
3. **Start Phase 1** - Foundation & Security
4. **Iterative development** with testing on `openeducat_demo` database

---

**Document Version:** 1.0
**Author:** Claude Code Assistant
**For:** UEIPAB - Venezuela
