# vitexsoftware.mcprack

Ansible collection to install, configure, and manage [mcprack](https://github.com/VitexSoftware/mcprack)
— a Flask-based MCP (Model Context Protocol) server catalog and self-service
client-config portal.

This collection covers the mcprack **application** only: installing the
`.deb` package, configuring `/etc/mcprack/env`, fronting it with nginx,
managing local admin accounts, and registering catalog entries. It
deliberately does **not** manage individual MCP servers' own runtime
(e.g. running stdio servers as systemd services) — that is out of scope.

## Contents

### Role

- `vitexsoftware.mcprack.app` — installs and configures the mcprack web
  application. See [`roles/app/README.md`](roles/app/README.md).

### Modules

All modules run the `mcprack` CLI on the managed node (requires
`become: true`, since `/etc/mcprack/env` is `root:mcprack 0640`) and require
mcprack to already be installed there (e.g. via the `app` role). See each
module's documentation (`ansible-doc vitexsoftware.mcprack.<name>`) for full
details.

| Module | Wraps | Purpose |
|---|---|---|
| `mcprack_server` | `mcprack server ...` | Register/update/remove catalog servers |
| `mcprack_user` | `mcprack user ...` | Create/update/remove local users, admin flag, enable/disable, password |
| `mcprack_user_access` | `mcprack user server allow/deny` | Per-user per-server allow/deny |
| `mcprack_user_selection` | `mcprack user server select` | Per-user pre-selected server list |
| `mcprack_user_override` | `mcprack user override ...` | Per-user per-server credential overrides |
| `mcprack_user_config` | `mcprack user config show/download` | Read-only: fetch a user's rendered client config |
| `mcprack_secret` | `mcprack secret ...` | Set/unset a server's secret env keys |
| `mcprack_template` | `mcprack template ...` | Create/update/remove admin server-bundle templates |
| `mcprack_template_apply` | `mcprack template apply` | Apply a template to a user (one-shot action) |

## Requirements

- Target host: Debian/Ubuntu (mcprack ships as a `.deb`).
- `community.general` collection (used for UFW firewall management; can be
  disabled via `mcprack_firewall_enabled: false`).

## Example

```yaml
- hosts: mcprack_servers
  become: true
  roles:
    - role: vitexsoftware.mcprack.app
      vars:
        mcprack_domain: mcprack.example.com
        mcprack_admin_users: [alice]
        mcprack_catalog_servers:
          - name: netbox
            label: NetBox
            transport: http
            url: "https://netbox.example.com/mcp"
            category: infra
```

See [`examples/playbook.yml`](examples/playbook.yml) for a fuller example
also exercising the modules directly.

## License

MIT
