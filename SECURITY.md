# Security

VHS Studio runs locally with the current user's permissions. It does not require
administrator access and exposes MCP over standard input/output, not a network
listener. Connect only local automation clients you trust: they can start jobs,
read local results and submit reviews within your user account.

Runtime downloads use pinned original upstream addresses and SHA-256 checks.
Application updates trust this repository's GitHub releases and their asset
digests. A checksum protects file integrity; it is not an independent code audit.

Settings, footage, OCR databases, processing logs and credentials do not belong
in the source repository or public issue attachments. Review any diagnostic
material before sharing it. Never post access tokens, private keys or personal
family footage in a security report.

Report vulnerabilities through GitHub's private vulnerability reporting feature
when available. Otherwise open a minimal issue requesting a private contact
channel, without exploit details or sensitive data. Do not submit credentials
or private data to demonstrate a problem.
