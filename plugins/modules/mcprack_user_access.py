#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_user_access
short_description: Manage a mcprack user's per-server allow/deny access
version_added: "1.0.0"
description:
  - Allows or denies a user's access to one catalog server, by wrapping
    C(mcprack user server allow)/C(mcprack user server deny).
  - Idempotent - reads current access via C(mcprack user server list) first.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  username:
    description: The account username.
    type: str
    required: true
  server:
    description: The catalog server name.
    type: str
    required: true
  access:
    description: Desired access.
    type: str
    choices: [allow, deny]
    required: true
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Deny a user access to a server
  vitexsoftware.mcprack.mcprack_user_access:
    username: alice
    server: internal-only-tool
    access: deny
  become: true
"""

RETURN = r"""
changed:
  description: Whether access was changed.
  type: bool
  returned: always
username:
  description: The account username.
  type: str
  returned: always
server:
  description: The catalog server name.
  type: str
  returned: always
access:
  description: Resulting access.
  type: str
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import (
    parse_tsv_list,
    parse_user_server_access_row,
    run_mcprack,
)


def _current_access(module, username, server):
    rc, stdout, stderr = run_mcprack(module, ["user", "server", "list", username], check_rc=True)
    for row in parse_tsv_list(stdout):
        parsed = parse_user_server_access_row(row)
        if parsed and parsed["name"] == server:
            return parsed["access"]
    return "allow"  # servers default to allowed when not explicitly denied


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(type="str", required=True),
            server=dict(type="str", required=True),
            access=dict(type="str", choices=["allow", "deny"], required=True),
        ),
        supports_check_mode=True,
    )

    p = module.params
    username, server, access = p["username"], p["server"], p["access"]

    current = _current_access(module, username, server)
    result = {"changed": False, "username": username, "server": server, "access": current}

    if current != access:
        result["changed"] = True
        result["access"] = access
        if not module.check_mode:
            run_mcprack(module, ["user", "server", access, username, server], check_rc=True)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
