#!/bin/sh
# Tor refuses to use a HiddenServiceDir unless it is owned by Tor's runtime user
# and mode 0700. The persistent named volume mounts as root, so fix ownership
# and permissions on every start before handing off to tor (which drops to the
# unprivileged 'tor' user itself via the `User tor` directive in torrc).
set -e

mkdir -p /var/lib/tor/vapour
chown -R tor:tor /var/lib/tor
chmod 700 /var/lib/tor /var/lib/tor/vapour

exec "$@"
