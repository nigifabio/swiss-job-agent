"""Swiss Job Agent platform: one isolated app instance (tenant) per person.

- gateway: the only public entry. Signs people in (Cloudflare Access), runs invites and the
  admin page, and forwards each request to the caller's own tenant, chosen from the verified
  email, never from the URL.
- provisioner: the only service with the Docker socket. Creates, stops, exports, upgrades and
  deletes tenants with a fixed, locked-down container spec; the gateway calls it over an
  internal network with a shared token.
"""
