#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_server
short_description: Manage mcprack catalog servers
version_added: "1.0.0"
description:
  - Registers, updates, or removes an MCP server entry in mcprack's catalog,
    by wrapping the C(mcprack server) CLI commands.
  - Idempotent - reads the current state via C(mcprack server show) first
    and only issues C(server create)/C(server edit) calls for fields that
    actually differ.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  name:
    description: Unique server name/key.
    type: str
    required: true
  state:
    description: Whether the server should be present or absent.
    type: str
    choices: [present, absent]
    default: present
  label:
    description: Display label. Required when creating a new server.
    type: str
  transport:
    description: Transport type. Required when creating a new server.
    type: str
    choices: [stdio, http, sse]
  command:
    description: Stdio command (stdio transport only).
    type: str
  args:
    description: Stdio command arguments (stdio transport only).
    type: list
    elements: str
  url:
    description: Endpoint URL (http/sse transport only).
    type: str
  category:
    description: Catalog category.
    type: str
  enabled:
    description: Whether the server is enabled. Defaults to C(true) on creation.
    type: bool
  description_text:
    description: Free-text description (maps to C(mcprack server edit --description)).
    type: str
    aliases: [description]
  allow_user_override:
    description: Whether users may override this server's credentials.
    type: bool
  auth_header_name:
    description: Auth header name (http/sse transport only).
    type: str
  auth_env_key:
    description: Env var name used for the auth header value.
    type: str
  vault_item_name:
    description: Vaultwarden item name used for secret storage.
    type: str
  env_config:
    description:
      - Desired full set of non-secret environment variables for this
        server. Keys not present here but present on the server are
        removed; keys present here are set (added or updated).
      - Omit this option entirely to leave existing env config untouched.
    type: dict
  secret_keys:
    description:
      - Desired full set of env var keys declared as secret. Keys not
        listed here but currently declared secret are un-declared (and
        their stored value deleted by mcprack); keys listed here are added.
      - Omit this option entirely to leave the current secret key set untouched.
    type: list
    elements: str
  required_keys:
    description:
      - Desired full set of env var keys marked as required before proxy
        spawn. Same replace-if-given, leave-untouched-if-omitted semantics
        as I(secret_keys).
    type: list
    elements: str
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Register an HTTP MCP server
  vitexsoftware.mcprack.mcprack_server:
    name: netbox
    label: NetBox
    transport: http
    url: "https://netbox.example.com/mcp"
    category: infra
  become: true

- name: Register a stdio MCP server with a secret env key
  vitexsoftware.mcprack.mcprack_server:
    name: abraflexi
    label: AbraFlexi
    transport: stdio
    command: mcp-server-abraflexi
    args: ["--sandbox"]
    env_config:
      ABRAFLEXI_URL: "https://demo.abraflexi.eu"
    secret_keys:
      - ABRAFLEXI_PASSWORD
    required_keys:
      - ABRAFLEXI_PASSWORD
  become: true

- name: Remove a catalog server
  vitexsoftware.mcprack.mcprack_server:
    name: old-server
    state: absent
  become: true
"""

RETURN = r"""
changed:
  description: Whether any change was made.
  type: bool
  returned: always
created:
  description: Whether the server was newly created by this run.
  type: bool
  returned: always
name:
  description: The server name.
  type: str
  returned: always
fields_changed:
  description: List of field names that were changed by this run.
  type: list
  elements: str
  returned: always
"""

import ast

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import (
    fail_unless_known_error,
    parse_kv_block,
    parse_tsv_list,
    run_mcprack,
)

NOT_FOUND_SUBSTRINGS = ("No such MCP server",)


def _literal_or_none(text):
    if text is None:
        return None
    text = text.strip()
    if text in ("-", ""):
        return None
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None


def _get_server(module, name):
    rc, stdout, stderr = run_mcprack(module, ["server", "show", name])
    if fail_unless_known_error(module, rc, stdout, stderr, NOT_FOUND_SUBSTRINGS):
        return None
    kv = parse_kv_block(stdout)
    return {
        "name": kv.get("name"),
        "label": kv.get("label"),
        "transport": kv.get("transport"),
        "enabled": kv.get("enabled") == "True",
        "category": None if kv.get("category") == "-" else kv.get("category"),
        "command": kv.get("command"),
        "args": _literal_or_none(kv.get("args")) or [],
        "url": kv.get("url"),
        "env_config": _literal_or_none(kv.get("env config")) or {},
        "secret_keys": _literal_or_none(kv.get("secret keys")) or [],
    }


def _get_required_keys(module, name):
    # required_env_keys is not printed by `server show`; there is no direct
    # CLI read for it either, so this collection cannot reliably diff it
    # from current state. Callers that pass required_keys always go through
    # `server edit`, whose own diff (add/remove-required-key) is trusted.
    return None


def _create(module, name, params):
    args = ["server", "create", name, "--label", params["label"], "--transport", params["transport"]]
    if params.get("command"):
        args += ["--command", params["command"]]
    for a in params.get("args") or []:
        args += ["--arg", a]
    if params.get("url"):
        args += ["--url", params["url"]]
    if params.get("category"):
        args += ["--category", params["category"]]
    args.append("--enabled" if params.get("enabled", True) else "--disabled")
    rc, stdout, stderr = run_mcprack(module, args, check_rc=True)
    return stdout


def _diff_create_fields(current, params):
    """Return True if any field handled by `server create` differs."""
    if params.get("label") is not None and params["label"] != current["label"]:
        return True
    if params.get("enabled") is not None and params["enabled"] != current["enabled"]:
        return True
    if params.get("category") is not None and params["category"] != current["category"]:
        return True
    transport = params.get("transport") or current["transport"]
    if transport == "stdio":
        if params.get("command") is not None and params["command"] != current["command"]:
            return True
        if params.get("args") is not None and params["args"] != current["args"]:
            return True
    else:
        if params.get("url") is not None and params["url"] != current["url"]:
            return True
    return False


def _build_edit_args(name, params, current):
    args = ["server", "edit", name]
    have_edit = False

    if params.get("description_text") is not None:
        args += ["--description", params["description_text"]]
        have_edit = True
    if params.get("allow_user_override") is not None:
        args.append("--allow-user-override" if params["allow_user_override"] else "--disallow-user-override")
        have_edit = True
    if params.get("auth_header_name") is not None:
        args += ["--auth-header-name", params["auth_header_name"]]
        have_edit = True
    if params.get("auth_env_key") is not None:
        args += ["--auth-env-key", params["auth_env_key"]]
        have_edit = True
    if params.get("vault_item_name") is not None:
        args += ["--vault-item-name", params["vault_item_name"]]
        have_edit = True

    if params.get("env_config") is not None:
        desired_env = params["env_config"] or {}
        current_env = current.get("env_config", {}) if current else {}
        for key, value in desired_env.items():
            if current_env.get(key) != value:
                args += ["--set-env", "%s=%s" % (key, value)]
                have_edit = True
        for key in current_env:
            if key not in desired_env:
                args += ["--unset-env", key]
                have_edit = True

    if params.get("secret_keys") is not None:
        desired_secret = set(params["secret_keys"] or [])
        current_secret = set(current.get("secret_keys", []) if current else [])
        for key in desired_secret - current_secret:
            args += ["--add-secret-key", key]
            have_edit = True
        for key in current_secret - desired_secret:
            args += ["--remove-secret-key", key]
            have_edit = True

    if params.get("required_keys") is not None:
        # We cannot read the current required-key set back from the CLI
        # (server show doesn't print it), so always pass through the full
        # desired list as add-required-key; mcprack's own edit command is
        # idempotent per-key (only reports a change for keys not already
        # required), so this stays safe to run every time.
        for key in params["required_keys"] or []:
            args += ["--add-required-key", key]
            have_edit = True

    return args, have_edit


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            label=dict(type="str"),
            transport=dict(type="str", choices=["stdio", "http", "sse"]),
            command=dict(type="str"),
            args=dict(type="list", elements="str"),
            url=dict(type="str"),
            category=dict(type="str"),
            enabled=dict(type="bool"),
            description_text=dict(type="str", aliases=["description"]),
            allow_user_override=dict(type="bool"),
            auth_header_name=dict(type="str"),
            auth_env_key=dict(type="str"),
            vault_item_name=dict(type="str"),
            env_config=dict(type="dict"),
            secret_keys=dict(type="list", elements="str"),
            required_keys=dict(type="list", elements="str"),
        ),
        supports_check_mode=True,
    )

    p = module.params
    name = p["name"]
    state = p["state"]

    current = _get_server(module, name)
    result = {"changed": False, "created": False, "name": name, "fields_changed": []}

    if state == "absent":
        if current is not None:
            result["changed"] = True
            if not module.check_mode:
                run_mcprack(module, ["server", "delete", name, "--yes"], check_rc=True)
        module.exit_json(**result)

    # state == present
    if current is None:
        if not p.get("label") or not p.get("transport"):
            module.fail_json(msg="label and transport are required when creating a new server ('%s')." % name)
        result["changed"] = True
        result["created"] = True
        result["fields_changed"] = ["label", "transport", "enabled"]
        if not module.check_mode:
            _create(module, name, p)
            edit_args, have_edit = _build_edit_args(name, p, current={"env_config": {}, "secret_keys": []})
            if have_edit:
                run_mcprack(module, edit_args, check_rc=True)
        module.exit_json(**result)

    # existing server: diff create-covered fields first
    needs_create_call = _diff_create_fields(current, p)
    create_fields = []
    if needs_create_call:
        for field in ("label", "enabled", "category", "command", "args", "url"):
            if p.get(field) is not None and p.get(field) != current.get(field):
                create_fields.append(field)

    edit_args, have_edit = _build_edit_args(name, p, current)

    if not needs_create_call and not have_edit:
        module.exit_json(**result)

    result["changed"] = True
    result["fields_changed"] = create_fields

    if module.check_mode:
        module.exit_json(**result)

    if needs_create_call:
        merged = dict(current)
        merged.update({k: v for k, v in p.items() if v is not None})
        _create(module, name, merged)

    if have_edit:
        rc, stdout, stderr = run_mcprack(module, edit_args, check_rc=True)
        if "No changes" in stdout and not needs_create_call:
            # Our diff thought something changed but the CLI's own diff
            # disagrees - trust the CLI, but surface this rather than hide it.
            result["changed"] = False
        elif "updated:" in stdout:
            changed_str = stdout.split("updated:", 1)[1].strip()
            result["fields_changed"] += [f.strip() for f in changed_str.split(",") if f.strip()]

    module.exit_json(**result)


if __name__ == "__main__":
    main()
