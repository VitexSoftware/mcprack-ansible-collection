# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vitex Software <info@vitexsoftware.cz>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "plugins", "module_utils"),
)

import mcprack as mu  # noqa: E402


# --- fixtures -----------------------------------------------------------
# Strings below match mcprack/cli.py's click.echo() formats exactly, as
# verified by reading the source at implementation time:
#   user_list:   f"{u.id}\t{u.username}\t{u.auth_type}\t{u.email or '-'}{flag_str}"
#     flag_str = f" [{', '.join(flags)}]" if flags else ""   flags in {"admin","disabled"}
#   server_list: f"{s.id}\t{s.name}\t{s.transport}\t{state}\t{s.category or '-'}"
#   server_show: fixed "key:   value" lines, no id: line.
#   user_server_list (user server list): "name\taccess\tincluded" rows
#   secret_list: f"{key}\t{'set' if values.get(key) else 'unset'}"

USER_LIST_STDOUT = (
    "1\talice\tlocal\talice@example.com [admin]\n"
    "2\tbob\tlocal\t- [disabled]\n"
    "3\tcarol\tldap\tcarol@example.com [admin, disabled]\n"
    "4\tdave\tlocal\tdave@example.com\n"
)

SERVER_LIST_STDOUT = (
    "1\tnetbox\thttp\tenabled\tinfra\n"
    "2\tabraflexi\tstdio\tdisabled\t-\n"
)

SERVER_SHOW_HTTP_STDOUT = (
    "name:        netbox\n"
    "label:       NetBox\n"
    "transport:   http\n"
    "enabled:     True\n"
    "category:    infra\n"
    "url:         https://netbox.example.com/mcp\n"
    "auth header: -\n"
    "env config:  {}\n"
    "secret keys: -\n"
)

USER_SERVER_LIST_STDOUT = (
    "netbox\tallow\tselected\n"
    "abraflexi\tdeny\t-\n"
)

SECRET_LIST_STDOUT = (
    "API_KEY\tset\n"
    "API_SECRET\tunset\n"
)


def test_parse_tsv_list_skips_blank_lines():
    rows = mu.parse_tsv_list("a\tb\n\nc\td\n")
    assert rows == [["a", "b"], ["c", "d"]]


def test_parse_kv_block_splits_on_first_colon():
    result = mu.parse_kv_block("name:        netbox\nurl:         https://x/y:1234\n")
    assert result["name"] == "netbox"
    assert result["url"] == "https://x/y:1234"


def test_parse_user_list_row_no_flags():
    rows = mu.parse_tsv_list(USER_LIST_STDOUT)
    parsed = mu.parse_user_list_row(rows[3])
    assert parsed == {
        "id": "4",
        "username": "dave",
        "auth_type": "local",
        "email": "dave@example.com",
        "admin": False,
        "enabled": True,
    }


def test_parse_user_list_row_admin_flag():
    rows = mu.parse_tsv_list(USER_LIST_STDOUT)
    parsed = mu.parse_user_list_row(rows[0])
    assert parsed["username"] == "alice"
    assert parsed["admin"] is True
    assert parsed["enabled"] is True


def test_parse_user_list_row_disabled_flag_and_dash_email():
    rows = mu.parse_tsv_list(USER_LIST_STDOUT)
    parsed = mu.parse_user_list_row(rows[1])
    assert parsed["username"] == "bob"
    assert parsed["email"] is None
    assert parsed["admin"] is False
    assert parsed["enabled"] is False


def test_parse_user_list_row_multiple_flags():
    rows = mu.parse_tsv_list(USER_LIST_STDOUT)
    parsed = mu.parse_user_list_row(rows[2])
    assert parsed["username"] == "carol"
    assert parsed["admin"] is True
    assert parsed["enabled"] is False


def test_parse_server_list_row():
    rows = mu.parse_tsv_list(SERVER_LIST_STDOUT)
    enabled = mu.parse_server_list_row(rows[0])
    disabled = mu.parse_server_list_row(rows[1])
    assert enabled == {
        "id": "1",
        "name": "netbox",
        "transport": "http",
        "enabled": True,
        "category": "infra",
    }
    assert disabled["enabled"] is False
    assert disabled["category"] is None


def test_parse_server_show_has_no_id_field():
    parsed = mu.parse_kv_block(SERVER_SHOW_HTTP_STDOUT)
    assert parsed["name"] == "netbox"
    assert parsed["transport"] == "http"
    assert "id" not in parsed


def test_parse_user_server_access_row():
    rows = mu.parse_tsv_list(USER_SERVER_LIST_STDOUT)
    parsed = mu.parse_user_server_access_row(rows[0])
    assert parsed == {"name": "netbox", "access": "allow", "included": "selected"}


def test_parse_secret_list_row():
    rows = mu.parse_tsv_list(SECRET_LIST_STDOUT)
    parsed = [mu.parse_secret_list_row(r) for r in rows]
    assert parsed == [
        {"key": "API_KEY", "is_set": True},
        {"key": "API_SECRET", "is_set": False},
    ]
