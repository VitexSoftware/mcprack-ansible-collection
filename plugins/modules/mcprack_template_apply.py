#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: mcprack_template_apply
short_description: Apply a mcprack template to a user
version_added: "1.0.0"
description:
  - Applies a template's server ACL and pre-selection to a user, by
    wrapping C(mcprack template apply).
  - This is a one-shot imperative action, not a piece of persistent state
    the CLI can report a "no changes" diff for - it always reports
    C(changed=true) when run (outside check mode). Re-applying an
    already-applied template is itself a deliberate re-sync action.
extends_documentation_fragment:
  - vitexsoftware.mcprack.mcprack
options:
  name:
    description: The template name.
    type: str
    required: true
  username:
    description: The account username to apply the template to.
    type: str
    required: true
author:
  - Vitex Software (@VitexSoftware)
"""

EXAMPLES = r"""
- name: Apply a template to a user
  vitexsoftware.mcprack.mcprack_template_apply:
    name: standard-devops
    username: alice
  become: true
"""

RETURN = r"""
changed:
  description: Always true when run (outside check mode).
  type: bool
  returned: always
name:
  description: The template name.
  type: str
  returned: always
username:
  description: The account username.
  type: str
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vitexsoftware.mcprack.plugins.module_utils.mcprack import run_mcprack


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            username=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )

    p = module.params
    result = {"changed": True, "name": p["name"], "username": p["username"]}

    if not module.check_mode:
        run_mcprack(module, ["template", "apply", p["name"], p["username"]], check_rc=True)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
