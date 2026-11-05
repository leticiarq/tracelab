# Security and privacy

## Data location

Structured records default to `backend/data/tracelab.db`; evidence defaults to `backend/data/evidences/`. Both are local and ignored by Git. ZIPs are assembled in memory and returned to the browser. TraceLab sends no telemetry and requires no hosted API.

TraceLab does not encrypt the database, evidence, environment file, or downloads. Use operating-system permissions and full-disk encryption where appropriate.

## Implemented controls

- Documented services bind to loopback; trusted-host and CORS settings constrain browser access.
- Cross-site and unapproved-origin mutating requests are rejected.
- Upload names reject paths and null bytes; extensions are checked against image signatures or UTF-8 text.
- Count and size limits, SHA-256 duplicate detection, generated names, and restrictive file modes reduce file-handling risk.
- Evidence responses disable MIME sniffing and caching and use a restrictive sandbox policy.
- Ownership checks prevent cross-lab evidence associations.
- Preview creates React text nodes instead of injecting raw HTML.
- Export validates manifests, paths, names, ownership, selected references, active HTML, and size.
- Pattern warnings and a required review confirmation add friction before export.

## Limitations

There is no login, authorization, encryption at rest, malware scanner, or automatic redaction. Anyone with equivalent operating-system access may access the data. Warning patterns cover only a few secret formats. File checks establish a supported format, not safe content.

Do not expose the current application on a public or shared interface without authentication, TLS, authorization, rate limiting, and deployment hardening.

## Publication checklist

- Remove tokens, cookies, API keys, passwords, private keys, and authorization headers.
- Redact personal data, private addresses/hostnames, account identifiers, and customer information.
- Confirm the target and lab rules allow disclosure.
- Inspect image pixels, captions, filenames, TXT files, and HTTP evidence.
- Verify only intended evidence is selected.
- Extract the ZIP and review its final `README.md` and every file.
- Never commit `.env`, SQLite databases, local evidence, logs, or personal exports.

Back up the database and evidence together using [Database backup](database-backup.md). If a secret is published, remove it from the public location and history where needed, then revoke or rotate it.
