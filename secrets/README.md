# secrets/

This directory holds local credentials and environment-specific secrets.

**Git policy (REQ-SEC-002):** Only `README.md` and `*.example` files are
tracked. All other contents are git-ignored. Never commit real credentials.

Add secret files here as needed. For each secret, provide a `<name>.example`
file as a template with placeholder values; copy it to `<name>` locally and
fill in the real values. The `.example` file is safe to commit; the real file
is not.
