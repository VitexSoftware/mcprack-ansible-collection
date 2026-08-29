#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_user_override
short_description: Manage a mcprack user's per-server credential overrides
version_added: "1.0.0"
description:
  - Sets, or resets to server defaults, a user's individual (per-user)
    credential overrides for one catalog server, by wrapping C(mcprack user
    override set)/C(mcprack user override reset).
  - Like other secret-bearing mcprack commands, override values are never
    echoed back by the CLI, so this module can only detect whether a key is
    currently set - not whether its value matches the desired one.
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
  state:
    description:
      - C(present) ensures the keys in I(overrides) are set.
      - C(reset) clears all of this user's overrides for the server,
        reverting them to the server's default credentials.
    type: str
    choices: [present, reset]
    default: present
  overrides:
    description: Mapping of env var key to value. Required when I(state=present).
    type: dict
    no_log: true
  mode:
    description:
      - C(ensure_present) (default) only sets keys in I(overrides) that are
        not already reported as set - idempotent, but can't guarantee an
        existing value is up to date.
      - C(always_set) always (re)applies every key in I(overrides), always
        reporting a change.
    type: str
    choices: [ensure_present, always_set]
    default: ensure_present
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Ensure per-user overrides are set for keys not already set
  vitexsoftware.mcprack.mcprack_user_override:
    username: alice
    server: abraflexi
    overrides:
      ABRAFLEXI_PASSWORD: "{{ vaulted_alice_password }}"
  become: true

- name: Reset a user's overrides back to server defaults
  vitexsoftware.mcprack.mcprack_user_override:
    username: alice
    server: abraflexi
    state: reset
  become: true
"""

RETURN = r"""
changed:
  description: Whether any change was made.
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
keys_set:
  description: Which keys were actually (re)applied by this run.
  type: list
  elements: str
  returned: when state is present
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import (
    parse_tsv_list,
    run_mcprack,
)

NO_OVERRIDES = "No individual credentials set"


def _current_keys(module, username, server):
    rc, stdout, stderr = run_mcprack(module, ["user", "override", "list", username, server], check_rc=True)
    if NO_OVERRIDES in stdout:
        return set()
    keys = set()
    for row in parse_tsv_list(stdout):
        if row:
            keys.add(row[0])
    return keys


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(type="str", required=True),
            server=dict(type="str", required=True),
            state=dict(type="str", choices=["present", "reset"], default="present"),
            overrides=dict(type="dict", no_log=True),
            mode=dict(type="str", choices=["ensure_present", "always_set"], default="ensure_present"),
        ),
        required_if=[("state", "present", ["overrides"])],
        supports_check_mode=True,
    )

    p = module.params
    username, server, state = p["username"], p["server"], p["state"]

    current_keys = _current_keys(module, username, server)
    result = {"changed": False, "username": username, "server": server}

    if state == "reset":
        if current_keys:
            result["changed"] = True
            if not module.check_mode:
                run_mcprack(module, ["user", "override", "reset", username, server], check_rc=True)
        module.exit_json(**result)

    overrides = p["overrides"] or {}
    if p["mode"] == "always_set":
        keys_to_set = list(overrides.keys())
    else:
        keys_to_set = [k for k in overrides if k not in current_keys]

    result["keys_set"] = keys_to_set
    if keys_to_set:
        result["changed"] = True
        if not module.check_mode:
            pairs = ["%s=%s" % (k, overrides[k]) for k in keys_to_set]
            run_mcprack(module, ["user", "override", "set", username, server] + pairs, check_rc=True)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
