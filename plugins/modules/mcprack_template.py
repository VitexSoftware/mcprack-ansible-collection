#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_template
short_description: Manage mcprack admin server-bundle templates
version_added: "1.0.0"
description:
  - Creates, updates, or removes a reusable server ACL/selection template,
    by wrapping the C(mcprack template) CLI commands.
  - Idempotent - reads current state via C(mcprack template show) first.
    Note C(mcprack template create) itself errors on a duplicate name
    (unlike C(mcprack server create)), so this module checks existence
    before ever calling it.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  name:
    description: Unique template name.
    type: str
    required: true
  state:
    description: Whether the template should be present or absent.
    type: str
    choices: [present, absent]
    default: present
  label:
    description: Display label. Defaults to I(name) on creation.
    type: str
  description_text:
    description: Free-text description.
    type: str
    aliases: [description]
  allow:
    description: Server names to mark allowed.
    type: list
    elements: str
  deny:
    description: Server names to mark denied and un-select.
    type: list
    elements: str
  select:
    description: Server names to pre-select (implies allow).
    type: list
    elements: str
  deselect:
    description: Server names to stop pre-selecting, without denying.
    type: list
    elements: str
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Create/update a template
  vitexsoftware.mcprack.mcprack_template:
    name: standard-devops
    label: Standard DevOps Bundle
    select: [netbox, zabbix]
    deny: [internal-only-tool]
  become: true

- name: Remove a template
  vitexsoftware.mcprack.mcprack_template:
    name: old-bundle
    state: absent
  become: true
"""

RETURN = r"""
changed:
  description: Whether any change was made.
  type: bool
  returned: always
created:
  description: Whether the template was newly created by this run.
  type: bool
  returned: always
name:
  description: The template name.
  type: str
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import (
    fail_unless_known_error,
    run_mcprack,
)

NOT_FOUND_SUBSTRINGS = ("No such template",)
NO_SERVERS_CONFIGURED = "none configured"


def _get_template(module, name):
    rc, stdout, stderr = run_mcprack(module, ["template", "show", name])
    if fail_unless_known_error(module, rc, stdout, stderr, NOT_FOUND_SUBSTRINGS):
        return None
    kv = {}
    entries = {}
    in_servers = False
    for line in stdout.splitlines():
        if line.startswith("servers:"):
            in_servers = True
            if NO_SERVERS_CONFIGURED in line:
                in_servers = False
            continue
        if in_servers and line.startswith("  "):
            parts = line.strip().split("\t")
            if len(parts) == 3:
                entries[parts[0]] = {"access": parts[1], "selected": parts[2] == "selected"}
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            kv[key.strip()] = value.strip()
    kv["entries"] = entries
    return kv


def _needs_set_servers(current_entries, p):
    for name in p.get("allow") or []:
        if current_entries.get(name, {}).get("access") != "allow":
            return True
    for name in p.get("deny") or []:
        entry = current_entries.get(name)
        if entry is None or entry.get("access") != "deny":
            return True
    for name in p.get("select") or []:
        entry = current_entries.get(name)
        if entry is None or entry.get("access") != "allow" or not entry.get("selected"):
            return True
    for name in p.get("deselect") or []:
        entry = current_entries.get(name)
        if entry is not None and entry.get("selected"):
            return True
    return False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            label=dict(type="str"),
            description_text=dict(type="str", aliases=["description"]),
            allow=dict(type="list", elements="str"),
            deny=dict(type="list", elements="str"),
            select=dict(type="list", elements="str"),
            deselect=dict(type="list", elements="str"),
        ),
        supports_check_mode=True,
    )

    p = module.params
    name = p["name"]
    state = p["state"]

    current = _get_template(module, name)
    result = {"changed": False, "created": False, "name": name}

    if state == "absent":
        if current is not None:
            result["changed"] = True
            if not module.check_mode:
                run_mcprack(module, ["template", "delete", name, "--yes"], check_rc=True)
        module.exit_json(**result)

    # state == present
    if current is None:
        result["changed"] = True
        result["created"] = True
        if not module.check_mode:
            args = ["template", "create", name]
            if p.get("label"):
                args += ["--label", p["label"]]
            if p.get("description_text"):
                args += ["--description", p["description_text"]]
            run_mcprack(module, args, check_rc=True)
        current_entries = {}
    else:
        current_entries = current.get("entries", {})

    set_servers_args = ["template", "set-servers", name]
    have_set_servers = False
    for name_ in p.get("allow") or []:
        set_servers_args += ["--allow", name_]
        have_set_servers = True
    for name_ in p.get("deny") or []:
        set_servers_args += ["--deny", name_]
        have_set_servers = True
    for name_ in p.get("select") or []:
        set_servers_args += ["--select", name_]
        have_set_servers = True
    for name_ in p.get("deselect") or []:
        set_servers_args += ["--deselect", name_]
        have_set_servers = True

    if have_set_servers and (result["created"] or _needs_set_servers(current_entries, p)):
        result["changed"] = True
        if not module.check_mode:
            run_mcprack(module, set_servers_args, check_rc=True)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
