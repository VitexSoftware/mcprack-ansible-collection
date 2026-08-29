#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_user
short_description: Manage mcprack local user accounts
version_added: "1.0.0"
description:
  - Creates, updates, or removes an mcprack local user account, and manages
    its admin/enabled flags and (optionally) its password, by wrapping the
    C(mcprack user) CLI commands.
  - Idempotent - reads the current state via C(mcprack user list) first and
    only issues mutating commands for what actually differs.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  username:
    description: The account username.
    type: str
    required: true
  state:
    description: Whether the account should be present or absent.
    type: str
    choices: [present, absent]
    default: present
  password:
    description:
      - Password to set. Required when creating a new local account.
      - Only re-applied to an existing account when I(force_password=true)
        (the CLI itself never re-touches an existing password on C(user
        create)).
    type: str
  email:
    description: Email address. Used at creation time only.
    type: str
  admin:
    description: Whether the account should have admin privileges. Omit to leave unmanaged.
    type: bool
  enabled:
    description: Whether the account should be enabled. Omit to leave unmanaged.
    type: bool
  force_password:
    description:
      - When C(true), always (re)apply I(password) to an existing account,
        via C(mcprack user passwd). This is always reported as a change,
        since the CLI cannot report whether the new password differs from
        the old one.
    type: bool
    default: false
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Ensure an mcprack admin account exists
  vitexsoftware.mcprack.mcprack_user:
    username: alice
    password: "{{ mcprack_admin_passwords['alice'] }}"
    admin: true
    force_password: true
  become: true

- name: Remove a user account
  vitexsoftware.mcprack.mcprack_user:
    username: bob
    state: absent
  become: true
"""

RETURN = r"""
changed:
  description: Whether any change was made.
  type: bool
  returned: always
created:
  description: Whether the account was newly created by this run.
  type: bool
  returned: always
username:
  description: The account username.
  type: str
  returned: always
admin:
  description: Resulting admin flag.
  type: bool
  returned: when the account exists
enabled:
  description: Resulting enabled flag.
  type: bool
  returned: when the account exists
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import (
    fail_unless_known_error,
    parse_tsv_list,
    parse_user_list_row,
    run_mcprack,
)

NOT_FOUND_SUBSTRINGS = ("No such user",)
ALREADY_EXISTS_SUBSTRINGS = ("already exists",)


def _find_user(module, username):
    rc, stdout, stderr = run_mcprack(module, ["user", "list"], check_rc=True)
    for row in parse_tsv_list(stdout):
        parsed = parse_user_list_row(row)
        if parsed and parsed["username"] == username:
            return parsed
    return None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(type="str", required=True),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            password=dict(type="str", no_log=True),
            email=dict(type="str"),
            admin=dict(type="bool"),
            enabled=dict(type="bool"),
            force_password=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )

    p = module.params
    username = p["username"]
    state = p["state"]

    current = _find_user(module, username)
    result = {"changed": False, "created": False, "username": username}

    if state == "absent":
        if current is not None:
            result["changed"] = True
            if not module.check_mode:
                run_mcprack(module, ["user", "delete", username, "--yes"], check_rc=True)
        module.exit_json(**result)

    # state == present
    if current is None:
        if not p.get("password"):
            module.fail_json(msg="password is required when creating a new user ('%s')." % username)
        result["changed"] = True
        result["created"] = True
        result["admin"] = bool(p.get("admin"))
        result["enabled"] = True
        if not module.check_mode:
            args = [
                "user", "create",
                "--username", username,
                "--password", p["password"],
                "--email", p.get("email") or "",
            ]
            if p.get("admin"):
                args.append("--admin")
            run_mcprack(module, args, check_rc=True)
            if p.get("enabled") is False:
                run_mcprack(module, ["user", "disable", username], check_rc=True)
                result["enabled"] = False
        module.exit_json(**result)

    # existing user: reconcile admin / enabled / password
    changed = False
    if p.get("admin") is not None and p["admin"] != current["admin"]:
        changed = True
        if not module.check_mode:
            run_mcprack(module, ["user", "promote" if p["admin"] else "demote", username], check_rc=True)
        current["admin"] = p["admin"]

    if p.get("enabled") is not None and p["enabled"] != current["enabled"]:
        changed = True
        if not module.check_mode:
            run_mcprack(module, ["user", "enable" if p["enabled"] else "disable", username], check_rc=True)
        current["enabled"] = p["enabled"]

    if p.get("force_password") and p.get("password"):
        changed = True
        if not module.check_mode:
            run_mcprack(module, ["user", "passwd", username, "--password", p["password"]], check_rc=True)

    result["changed"] = changed
    result["admin"] = current["admin"]
    result["enabled"] = current["enabled"]
    module.exit_json(**result)


if __name__ == "__main__":
    main()
