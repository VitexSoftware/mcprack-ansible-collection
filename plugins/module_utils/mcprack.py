# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

MCPRACK_BIN = "/usr/bin/mcprack"


def run_mcprack(module, args, check_rc=False, data=None):
    """Run ``mcprack <args>`` on the managed node.

    The caller (task/role) is expected to have set ``become: true`` — this
    helper does not itself elevate privileges, it simply execs the binary
    as whichever user the module process is already running as.

    :param module: the AnsibleModule instance (used for run_command).
    :param args: list of CLI arguments to pass to ``mcprack`` (not
        including the binary name itself).
    :param check_rc: if True, a non-zero return code fails the module
        immediately via ``module.fail_json``. Leave False when the caller
        needs to inspect stderr itself first (e.g. to tolerate "already
        exists" / "No such ..." / "is not set for ..." as non-failures).
    :param data: optional stdin data to feed the command.
    :returns: (rc, stdout, stderr) tuple, all stripped of surrounding
        whitespace is NOT performed here (callers decide) except that
        run_command already returns text.
    """
    rc, stdout, stderr = module.run_command(
        [MCPRACK_BIN] + list(args),
        check_rc=check_rc,
        data=data,
    )
    return rc, stdout, stderr


def fail_unless_known_error(module, rc, stdout, stderr, tolerate_substrings=()):
    """Fail the module unless rc==0 or stderr matches a tolerated substring.

    Returns True if the command is considered to have failed with a
    "known"/tolerated condition (so the caller can treat it as a no-op /
    changed=False rather than success), False if rc==0 (a real success).
    Calls module.fail_json (which exits) for any other non-zero rc.
    """
    if rc == 0:
        return False
    for substring in tolerate_substrings:
        if substring in stderr or substring in stdout:
            return True
    module.fail_json(
        msg="mcprack command failed (rc=%d): %s" % (rc, stderr.strip() or stdout.strip()),
        rc=rc,
        stdout=stdout,
        stderr=stderr,
    )
    return True  # pragma: no cover - fail_json exits, never reached


def parse_tsv_list(stdout):
    """Split CLI list-command stdout into rows of tab-separated fields.

    Empty-catalog messages such as "No users." / "No servers." naturally
    produce zero data rows here (no tab present -> callers should treat a
    single-column, tab-less line as "no rows", or simply check for known
    empty-list sentinel strings before calling this).
    """
    rows = []
    for line in stdout.splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def parse_kv_block(stdout):
    """Parse ``key: value`` lines into an ordered dict.

    Splits on the FIRST colon only and strips both sides. Intended for
    simple fixed-shape ``show`` output (e.g. ``server show``). Commands
    whose output mixes a kv block with a differently-shaped sub-section
    (e.g. ``template show``'s trailing ``servers:`` list) need their own
    bespoke parser instead of this generic one.
    """
    result = {}
    for line in stdout.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def parse_user_list_row(row):
    """Parse one row of ``user list`` output: id, username, auth_type, email, flags.

    Format (mcprack/cli.py user_list): ``id\\tusername\\tauth_type\\temail-or-dash[ [flag, flag]]``
    where flags is an optional " [admin, disabled]"-style suffix appended
    directly to the email field (no separate tab column).
    """
    if len(row) < 4:
        return None
    user_id, username, auth_type, email_and_flags = row[0], row[1], row[2], row[3]
    flags = []
    email = email_and_flags
    if " [" in email_and_flags and email_and_flags.endswith("]"):
        email, _, flag_part = email_and_flags.partition(" [")
        flags = [f.strip() for f in flag_part[:-1].split(",")]
    return {
        "id": user_id,
        "username": username,
        "auth_type": auth_type,
        "email": None if email == "-" else email,
        "admin": "admin" in flags,
        "enabled": "disabled" not in flags,
    }


def parse_server_list_row(row):
    """Parse one row of ``server list``: id, name, transport, state, category."""
    if len(row) < 5:
        return None
    server_id, name, transport, state, category = row[0], row[1], row[2], row[3], row[4]
    return {
        "id": server_id,
        "name": name,
        "transport": transport,
        "enabled": state == "enabled",
        "category": None if category == "-" else category,
    }


def parse_user_server_access_row(row):
    """Parse one row of ``user server list USERNAME``: name, access, included."""
    if len(row) < 3:
        return None
    name, access, included = row[0], row[1], row[2]
    return {"name": name, "access": access, "included": included}


def parse_secret_list_row(row):
    """Parse one row of ``secret list SERVER``: key, set|unset."""
    if len(row) < 2:
        return None
    key, state = row[0], row[1]
    return {"key": key, "is_set": state.strip().lower() == "set"}
