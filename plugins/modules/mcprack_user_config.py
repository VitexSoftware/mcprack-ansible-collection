#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_user_config
short_description: Fetch a mcprack user's generated MCP client config
version_added: "1.0.0"
description:
  - Read-only. Fetches a user's generated MCP client configuration (e.g.
    for Claude Desktop or VS Code) by wrapping C(mcprack user config show),
    optionally also writing it to a path on the managed node via C(mcprack
    user config download).
  - Always reports C(changed=false) - this module never mutates mcprack
    state. It runs on the managed node (not the Ansible controller), since
    that's where the mcprack CLI and its database live.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  username:
    description: The account username.
    type: str
    required: true
  client:
    description: The client config format to render (e.g. C(claude), C(copilot)).
    type: str
    required: true
  dest:
    description:
      - Optional path on the managed node to also write the config to, via
        C(mcprack user config download --out).
    type: path
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Fetch a user's Claude Desktop config
  vitexsoftware.mcprack.mcprack_user_config:
    username: alice
    client: claude
  become: true
  register: alice_claude_config

- name: Fetch and also write it out on the managed node
  vitexsoftware.mcprack.mcprack_user_config:
    username: alice
    client: claude
    dest: /tmp/alice-claude-mcp.json
  become: true
"""

RETURN = r"""
changed:
  description: Always false.
  type: bool
  returned: always
config:
  description: The raw client config JSON text.
  type: str
  returned: always
dest_path:
  description: The path the config was written to on the managed node, if I(dest) was given.
  type: str
  returned: when dest is given
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import run_mcprack


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(type="str", required=True),
            client=dict(type="str", required=True),
            dest=dict(type="path"),
        ),
        supports_check_mode=True,
    )

    p = module.params
    result = {"changed": False}

    rc, stdout, stderr = run_mcprack(module, ["user", "config", "show", p["username"], p["client"]], check_rc=True)
    result["config"] = stdout.strip()

    if p.get("dest") and not module.check_mode:
        run_mcprack(
            module,
            ["user", "config", "download", p["username"], p["client"], "--out", p["dest"]],
            check_rc=True,
        )
        result["dest_path"] = p["dest"]

    module.exit_json(**result)


if __name__ == "__main__":
    main()
