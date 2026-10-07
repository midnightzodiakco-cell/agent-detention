# Security Policy

Report security vulnerabilities privately to the repository maintainer rather than opening a public issue with exploit details.

Agent Detention stores behavioral records. Integrations must protect state files from unauthorized modification and must not place credentials, tokens, or private user data in investigation records.

The reference engine is local and dependency-free. Host adapters should fail closed when Detention state cannot be read or validated.
