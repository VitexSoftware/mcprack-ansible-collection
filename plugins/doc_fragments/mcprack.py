# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options: {}
requirements:
  - The C(mcprack) command-line tool must be installed and configured on the
    managed node (see the C(vitexsoftware.mcprack.app) role).
notes:
  - This module runs the C(mcprack) CLI on the managed node, not on the
    Ansible controller.
  - C(/etc/mcprack/env) is C(root:mcprack 0640), so the task (or play) must
    set C(become=true) to run as root; the module does not elevate
    privileges itself.
  - The C(mcprack) CLI has no JSON output mode. This module parses its
    human-readable text output, which is tied to the installed mcprack
    version; verify compatibility after upgrading mcprack.
"""
