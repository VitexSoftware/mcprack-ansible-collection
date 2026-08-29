#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_secret
short_description: Manage a mcprack catalog server's secret env values
version_added: "1.0.0"
description:
  - Sets or removes a single credential (secret env var) value for a
    catalog server, by wrapping C(mcprack secret set)/C(mcprack secret
    unset).
  - The CLI never echoes stored values back, so this module can only detect
    whether a key is currently I(set) or I(unset) - not whether an
    already-set value matches the desired one. By default, a key already
    reported as set is left untouched; set I(force=true) to always push the
    given value.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  server:
    description: The catalog server name.
    type: str
    required: true
  key:
    description: The env var key name.
    type: str
    required: true
  state:
    description: Whether the key should be set or unset.
    type: str
    choices: [present, absent]
    default: present
  value:
    description: The secret value. Required when I(state=present).
    type: str
    no_log: true
  force:
    description:
      - When C(true), always run C(secret set) even if the key is already
        reported as set. See the module description for why this can't be
        made truly idempotent on value.
    type: bool
    default: false
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Ensure a secret is set (no-op if already set, unless force is used)
  vitexsoftware.mcprack.mcprack_secret:
    server: abraflexi
    key: ABRAFLEXI_PASSWORD
    value: "{{ vaulted_abraflexi_password }}"
  become: true

- name: Always push the latest vaulted value
  vitexsoftware.mcprack.mcprack_secret:
    server: abraflexi
    key: ABRAFLEXI_PASSWORD
    value: "{{ vaulted_abraflexi_password }}"
    force: true
  become: true

- name: Remove a secret
  vitexsoftware.mcprack.mcprack_secret:
    server: abraflexi
    key: ABRAFLEXI_PASSWORD
    state: absent
  become: true
"""

RETURN = r"""
changed:
  description: Whether any change was made.
  type: bool
  returned: always
server:
  description: The catalog server name.
  type: str
  returned: always
key:
  description: The env var key name.
  type: str
  returned: always
backend:
  description: Which secret backend is currently active (informational).
  type: str
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import (
    fail_unless_known_error,
    parse_secret_list_row,
    parse_tsv_list,
    run_mcprack,
)

NO_SECRETS_DECLARED = "declares no secret env vars"
NOT_SET_SUBSTRINGS = ("is not set for server",)


def _current_state(module, server, key):
    rc, stdout, stderr = run_mcprack(module, ["secret", "list", server], check_rc=True)
    if NO_SECRETS_DECLARED in stdout:
        return False
    for row in parse_tsv_list(stdout):
        parsed = parse_secret_list_row(row)
        if parsed and parsed["key"] == key:
            return parsed["is_set"]
    return False


def _backend(module):
    rc, stdout, stderr = run_mcprack(module, ["secret", "backend"], check_rc=True)
    return stdout.strip()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            server=dict(type="str", required=True),
            key=dict(type="str", required=True),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            value=dict(type="str", no_log=True),
            force=dict(type="bool", default=False),
        ),
        required_if=[("state", "present", ["value"])],
        supports_check_mode=True,
    )

    p = module.params
    server = p["server"]
    key = p["key"]
    state = p["state"]

    is_set = _current_state(module, server, key)
    result = {"changed": False, "server": server, "key": key, "backend": _backend(module)}

    if state == "present":
        if not is_set or p.get("force"):
            result["changed"] = True
            if not module.check_mode:
                run_mcprack(module, ["secret", "set", server, key, "--value", p["value"]], check_rc=True)
    else:
        if is_set:
            result["changed"] = True
            if not module.check_mode:
                rc, stdout, stderr = run_mcprack(module, ["secret", "unset", server, key])
                fail_unless_known_error(module, rc, stdout, stderr, NOT_SET_SUBSTRINGS)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
