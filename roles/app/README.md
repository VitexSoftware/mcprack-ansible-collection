# vitexsoftware.mcprack.app

Installs and configures the mcprack MCP server catalog / self-service
portal application (a Flask app, packaged as a `.deb` on
`repo.vitexsoftware.com`).

## What this role does

1. Adds the VitexSoftware apt repo and installs the `mcprack` package
   (optionally installing/starting a local PostgreSQL server for it).
2. Overlays deployment-specific settings onto `/etc/mcprack/env` (the
   package's own `postinst` already generates `SECRET_KEY` and the DB URI —
   this role never overwrites those).
3. Optionally fronts the app with an nginx reverse proxy.
4. Optionally opens UFW firewall rules for the app's port.
5. Waits for `/health` to return 200.
6. Creates configured local admin accounts
   (`vitexsoftware.mcprack.mcprack_user`), auto-generating and caching
   their passwords under `credentials/mcprack-admin-<user>.txt` (relative
   to the playbook's parent directory — gitignore this).
7. Registers configured catalog servers
   (`vitexsoftware.mcprack.mcprack_server`).

This role does **not** install or manage individual MCP servers' own
runtime — only the mcprack application. Servers you list in
`mcprack_catalog_servers` are expected to already be reachable (for
`http`/`sse` transports) or installed on the mcprack host itself (for
`stdio` transport), by whatever means you choose.

## Key variables

See [`defaults/main.yml`](defaults/main.yml) for the full, documented list.
The most commonly overridden:

| Variable | Default | Purpose |
|---|---|---|
| `mcprack_domain` | `mcprack.example.com` | vhost server_name / health-check host |
| `mcprack_reverse_proxy_enabled` | `true` | front with nginx on `mcprack_http_port` |
| `mcprack_firewall_enabled` | `true` | manage UFW rules (needs `community.general`) |
| `mcprack_ufw_allow_from` | `[]` | CIDRs allowed through the firewall |
| `mcprack_db_type` | `pgsql` | dbconfig-common database backend |
| `mcprack_admin_users` | `[]` | local admin usernames to create |
| `mcprack_catalog_servers` | `[]` | catalog entries to register |

Secrets (`mcprack_db_password`, `mcprack_ldap_bind_password`,
`mcprack_bw_*`) are intentionally left empty by default — supply them via a
vaulted vars file.

## Example

```yaml
- hosts: mcprack_servers
  become: true
  roles:
    - role: vitexsoftware.mcprack.app
      vars:
        mcprack_domain: mcprack.example.com
        mcprack_ufw_allow_from: ["10.0.0.0/24"]
        mcprack_admin_users: [alice]
        mcprack_catalog_servers:
          - name: netbox
            label: NetBox
            transport: http
            url: "https://netbox.example.com/mcp"
            category: infra
```
