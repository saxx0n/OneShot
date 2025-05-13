#!/usr/bin/env python3

import os
import yaml

BASE_DIR = os.path.abspath("data_deep_full")
ROLE_ROOT = os.path.abspath("roles")

DEFAULT_TRASH = {
    "job_slice_count": 1,
    "verbosity": 0,
    "timeout": 0,
    "forks": 0,
    "diff_mode": False,
    "scm_clean": False,
    "scm_update_on_launch": False,
    "allow_override": False,
    "update_project": False,
    "overwrite": False,
    "overwrite_vars": False,
    "update_on_launch": False,
}

def clean(d):
    return {
        k: v for k, v in d.items()
        if v not in (None, "", [], {}, 0, False)
        and not (k in DEFAULT_TRASH and v == DEFAULT_TRASH[k])
    }

def load_yaml(name):
    path = os.path.join(BASE_DIR, f"{name}.yaml")
    if not os.path.isfile(path):
        return []
    with open(path, "r") as f:
        return yaml.safe_load(f) or []

def build_lookup(data):
    return {
        obj["id"]: obj.get("name") or obj.get("username") or obj.get("description") or f"id:{obj['id']}"
        for obj in data if "id" in obj
    }

def write_role(name, var_key, entries, module_name, loop_var):
    role_path = os.path.join(ROLE_ROOT, f"controller_{name}")
    tasks_path = os.path.join(role_path, "tasks")
    vars_path = os.path.join(role_path, "vars")
    os.makedirs(tasks_path, exist_ok=True)
    os.makedirs(vars_path, exist_ok=True)

    with open(os.path.join(vars_path, "main.yml"), "w") as f:
        yaml.dump({var_key: entries}, f, default_flow_style=False, sort_keys=False)

    task = [{
        "name": f"Create {name}",
        f"ansible.controller.{module_name}": {
            **{k: f"{{{{ {loop_var}.{k} | default(omit) }}}}" for k in entries[0].keys()}
        },
        "loop": f"{{{{ {var_key} }}}}",
        "loop_control": {
            "loop_var": loop_var,
            "label": f"{{{{ {loop_var}.name }}}}"
        }
    }]

    with open(os.path.join(tasks_path, "main.yml"), "w") as f:
        yaml.dump(task, f, default_flow_style=False, sort_keys=False)

def generate_projects(projects, org_map, cred_map, ee_map):
    entries = []
    for p in projects:
        entries.append(clean({
            "name": p["name"],
            "description": p.get("description"),
            "organization": org_map.get(p.get("organization")),
            "scm_type": p.get("scm_type"),
            "scm_url": p.get("scm_url"),
            "scm_branch": p.get("scm_branch"),
            "scm_clean": p.get("scm_clean"),
            "scm_update_on_launch": p.get("scm_update_on_launch"),
            "credential": cred_map.get(p.get("credential")),
            "default_environment": ee_map.get(p.get("default_environment")),
            "timeout": p.get("timeout"),
            "allow_override": p.get("allow_override"),
            "update_project": p.get("update_project"),
            "state": "present"
        }))
    write_role("projects", "projects", entries, "project", "project")

def generate_job_templates(jts, proj_map, inv_map, cred_map, ee_map, note_map):
    entries = []
    for jt in jts:
        entry = {
            "name": jt["name"],
            "description": jt.get("description"),
            "job_type": jt.get("job_type"),
            "playbook": jt.get("playbook"),
            "project": proj_map.get(jt.get("project")),
            "inv": inv_map.get(jt.get("inventory")),
            "creds": [cred_map.get(cid) for cid in jt.get("credentials", []) if cred_map.get(cid)],
            "execution_environment": ee_map.get(jt.get("execution_environment")),
            "limit": jt.get("limit"),
            "job_tags": jt.get("job_tags"),
            "skip_tags": jt.get("skip_tags"),
            "verbosity": jt.get("verbosity"),
            "forks": jt.get("forks"),
            "job_slice_count": jt.get("job_slice_count"),
            "timeout": jt.get("timeout"),
            "diff_mode": jt.get("diff_mode"),
            "ask_variables_on_launch": jt.get("ask_variables_on_launch"),
            "ask_inventory_on_launch": jt.get("ask_inventory_on_launch"),
            "ask_limit_on_launch": jt.get("ask_limit_on_launch"),
            "ask_tags_on_launch": jt.get("ask_tags_on_launch"),
            "survey_spec": jt.get("survey_spec") if jt.get("survey_spec") else None,
            "notification_started": [note_map.get(nid) for nid in jt.get("notification_templates_started", []) if note_map.get(nid)],
            "notification_success": [note_map.get(nid) for nid in jt.get("notification_templates_success", []) if note_map.get(nid)],
            "notification_error": [note_map.get(nid) for nid in jt.get("notification_templates_error", []) if note_map.get(nid)],
            "labels": jt.get("labels"),
            "instance_groups": jt.get("instance_groups"),
            "state": "present"
        }
        entries.append(clean(entry))
    write_role("job_templates", "job_templates", entries, "job_template", "template")

def generate_credentials(creds, org_map):
    entries = []
    for c in creds:
        entry = {
            "name": c["name"],
            "description": c.get("description"),
            "credential_type": c.get("credential_type"),
            "organization": org_map.get(c.get("organization")),
            "inputs": c.get("inputs"),
            "state": "present"
        }
        entries.append(clean(entry))
    write_role("credentials", "credentials", entries, "credential", "cred")

def generate_inventories(inventories, org_map):
    entries = []
    for inv in inventories:
        entries.append(clean({
            "name": inv["name"],
            "description": inv.get("description"),
            "organization": org_map.get(inv.get("organization")),
            "variables": inv.get("variables"),
            "state": "present"
        }))
    write_role("inventories", "inventories", entries, "inventory", "inv")

def generate_inventory_sources(sources, inv_map, cred_map, org_map):
    entries = []
    for src in sources:
        entries.append(clean({
            "name": src["name"],
            "description": src.get("description"),
            "source": src.get("source"),
            "inventory": inv_map.get(src.get("inventory")),
            "credential": cred_map.get(src.get("credential")),
            "overwrite": src.get("overwrite"),
            "overwrite_vars": src.get("overwrite_vars"),
            "source_vars": src.get("source_vars"),
            "source_path": src.get("source_path"),
            "update_on_launch": src.get("update_on_launch"),
            "organization": org_map.get(src.get("organization")),
            "state": "present"
        }))
    write_role("inventory_sources", "inventory_sources", entries, "inventory_source", "source")

def generate_execution_environments(envs, cred_map, org_map):
    entries = []
    for ee in envs:
        entry = {
            "name": ee["name"],
            "image": ee.get("image"),
            "credential": cred_map.get(ee.get("credential")),
            "organization": org_map.get(ee.get("organization")),
            "pull": ee.get("pull"),
            "state": "present"
        }
        entries.append(clean(entry))
    write_role("execution_environments", "execution_environments", entries, "execution_environment", "ee")

def generate_organizations(orgs):
    entries = []
    for org in orgs:
        entries.append(clean({
            "name": org["name"],
            "description": org.get("description"),
            "state": "present"
        }))
    write_role("organizations", "organizations", entries, "organization", "org")

def generate_users_and_roles(users, org_map):
    user_entries = []
    role_assignments = []

    for user in users:
        user_entries.append(clean({
            "username": user.get("username"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "email": user.get("email"),
            "is_superuser": user.get("is_superuser"),
            "state": "present"
        }))

        summary_roles = user.get("summary_fields", {}).get("roles", [])
        for role in summary_roles:
            role_assignments.append(clean({
                "user": user.get("username"),
                "role": role.get("name"),
                "organization": org_map.get(role.get("resource_name")) if "resource_name" in role else None
            }))

    write_role("users", "users", user_entries, "user", "user")

    if role_assignments:
        role_path = os.path.join(ROLE_ROOT, "controller_roles")
        os.makedirs(os.path.join(role_path, "tasks"), exist_ok=True)
        os.makedirs(os.path.join(role_path, "vars"), exist_ok=True)
        with open(os.path.join(role_path, "vars", "main.yml"), "w") as f:
            yaml.dump({"role_assignments": role_assignments}, f, default_flow_style=False, sort_keys=False)
        with open(os.path.join(role_path, "tasks", "main.yml"), "w") as f:
            yaml.dump([{
                "name": "Assign user roles",
                "ansible.controller.role": {
                    "user": "{{ assignment.user }}",
                    "role": "{{ assignment.role }}",
                    "organization": "{{ assignment.organization | default(omit) }}"
                },
                "loop": "{{ role_assignments }}",
                "loop_control": {
                    "loop_var": "assignment",
                    "label": "{{ assignment.user }} → {{ assignment.role }}"
                }
            }], f, default_flow_style=False, sort_keys=False)

def generate_schedules(schedules, jt_map, wf_map, inv_map, proj_map):
    entries = []
    for s in schedules:
        summary = s.get("summary_fields", {})
        related = summary.get("unified_job_template", {})
        job_type = related.get("unified_job_type")

        parent_name = related.get("name")
        parent_type = (
            "workflow_job_template" if job_type == "workflow_job"
            else "job_template" if job_type == "job"
            else None
        )

        if not parent_name or not parent_type:
            continue

        entry = {
            "name": s["name"],
            "description": s.get("description"),
            "rrule": s.get("rrule"),
            "timezone": s.get("timezone"),
            "unified_job_template": parent_name,
            "unified_job_type": parent_type,
            "inventory": inv_map.get(s.get("inventory")),
            "project": proj_map.get(s.get("project")),
            "credentials": s.get("credentials", []),
            "extra_data": s.get("extra_data"),
            "enabled": s.get("enabled"),
            "limit": s.get("limit"),
            "job_tags": s.get("job_tags"),
            "skip_tags": s.get("skip_tags"),
            "verbosity": s.get("verbosity"),
            "execution_environment": s.get("execution_environment"),
            "state": "present"
        }
        entries.append(clean(entry))

    write_role("schedules", "schedules", entries, "schedule", "sched")

def generate_site_yaml():
    roles_root = ROLE_ROOT
    role_dirs = sorted([
        name for name in os.listdir(roles_root)
        if os.path.isdir(os.path.join(roles_root, name))
    ])

    play = [{
        "name": "Apply Tower configuration",
        "hosts": "localhost",
        "connection": "local",
        "gather_facts": False,
        "roles": role_dirs
    }]

    with open("site.yml", "w") as f:
        yaml.dump(play, f, default_flow_style=False, sort_keys=False)

def generate_all():
    orgs = load_yaml("organizations")
    users = load_yaml("users")
    teams = load_yaml("teams")
    credentials = load_yaml("credentials")
    inventories = load_yaml("inventories")
    inventory_sources = load_yaml("inventory_sources")
    projects = load_yaml("projects")
    job_templates = load_yaml("job_templates")
    workflow_templates = load_yaml("workflow_job_templates")
    execution_environments = load_yaml("execution_environments")
    notifications = load_yaml("notification_templates")
    schedules = load_yaml("schedules")

    org_map = build_lookup(orgs)
    user_map = build_lookup(users)
    team_map = build_lookup(teams)
    cred_map = build_lookup(credentials)
    inv_map = build_lookup(inventories)
    proj_map = build_lookup(projects)
    ee_map = build_lookup(execution_environments)
    note_map = build_lookup(notifications)
    jt_map = build_lookup(job_templates)
    wf_map = build_lookup(workflow_templates)

    if projects:
        generate_projects(projects, org_map, cred_map, ee_map)

    if job_templates:
        generate_job_templates(job_templates, proj_map, inv_map, cred_map, ee_map, note_map)

    if credentials:
        generate_credentials(credentials, org_map)

    if inventories:
        generate_inventories(inventories, org_map)

    if inventory_sources:
        generate_inventory_sources(inventory_sources, inv_map, cred_map, org_map)

    if execution_environments:
        generate_execution_environments(execution_environments, cred_map, org_map)

    if orgs:
        generate_organizations(orgs)

    if users:
        generate_users_and_roles(users, org_map)

    if schedules:
        generate_schedules(schedules, jt_map, wf_map, inv_map, proj_map)


if __name__ == "__main__":
    generate_all()
    generate_site_yaml()