#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_user_selection
short_description: Manage a mcprack user's pre-selected server list
version_added: "1.0.0"
description:
  - Replaces the full set of catalog servers included in a user's
    generated client config, by wrapping C(mcprack user server select).
  - Idempotent - reads the current selection via C(mcprack user server
    list) first and only issues the C(select) call if the desired set
    differs.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  username:
    description: The account username.
    type: str
    required: true
  servers:
    description:
      - Desired full list of server names to include. An empty list clears
        the selection. Servers the user isn't allowed to use are silently
        skipped by the CLI.
    type: list
    elements: str
    required: true
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Pre-select two servers for a user's generated config
  vitexsoftware.mcprack.mcprack_user_selection:
    username: alice
    servers: [netbox, zabbix]
  become: true

- name: Clear a user's selection
  vitexsoftware.mcprack.mcprack_user_selection:
    username: alice
    servers: []
  become: true
"""

RETURN = r"""
changed:
  description: Whether the selection was changed.
  type: bool
  returned: always
username:
  description: The account username.
  type: str
  returned: always
selection:
  description: Resulting selection.
  type: list
  elements: str
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import (
    parse_tsv_list,
    parse_user_server_access_row,
    run_mcprack,
)


def _current_selection(module, username):
    rc, stdout, stderr = run_mcprack(module, ["user", "server", "list", username], check_rc=True)
    selected = []
    for row in parse_tsv_list(stdout):
        parsed = parse_user_server_access_row(row)
        if parsed and parsed["included"] == "selected":
            selected.append(parsed["name"])
    return sorted(selected)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(type="str", required=True),
            servers=dict(type="list", elements="str", required=True),
        ),
        supports_check_mode=True,
    )

    p = module.params
    username = p["username"]
    desired = sorted(p["servers"])

    current = _current_selection(module, username)
    result = {"changed": False, "username": username, "selection": current}

    if current != desired:
        result["changed"] = True
        result["selection"] = desired
        if not module.check_mode:
            args = ["user", "server", "select", username]
            for name in p["servers"]:
                args += ["--server", name]
            run_mcprack(module, args, check_rc=True)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
