# OneShot
Just one shot scripts that do specific thing that don't fit into other places


# Ansible Tower Configuration Extract + Regenerate

This is based around two Python 3 scripts:

- `tower_deep_extract.py`  
  Connects to a live Ansible Tower or AAP instance and extracts all major configuration objects. Outputs to `data_deep_full/` as structured YAML.

- `generate_all.py`  
  Consumes the extracted YAML and generates modular Ansible roles under `roles/` using `ansible.controller` modules. Also generates a `site.yml` to apply them in order.

## Requirements

- Python 3.x
- PyYAML
- Ansible Collections:
  - `ansible.controller` (must be installed)

## Usage

1. **Set environment variables:**
   ```bash
   export TOWER_URL=https://your-tower-url
   export TOWER_USER=admin
   export TOWER_PASS=your-password
2. **Extract from Tower:**
   ```bash
   python3 tower_deep_extract.py
3. **Generate roles and site.yml:**
   ```bash
   python3 generate_all.py
4. **Apply with Ansible:**
   ```bash
   ansible-playbook site.yml

## Notes
    - All generated roles live in roles/controller_*
    - site.yml reflects only present roles — no stale references
    - Defaults and empty fields are stripped
    - Only objects present in data_deep_full/ are processed

## Included Resources
    Organizations
    Users
    Role bindings
    Projects
    Inventories
    Inventory Sources
    Credentials
    Execution Environments
    Job Templates
    Schedules

## Not Yet Supported
    Workflow Job Templates
    Teams
    Hosts & Groups
    Labels