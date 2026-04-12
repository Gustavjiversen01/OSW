# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Scope

LocalDictate is a local desktop application. All speech-to-text processing
happens on your machine. The only network calls the application makes are
one-time model downloads from HuggingFace (via `huggingface-hub`). No audio
or transcription data is ever transmitted.

## Reporting a vulnerability

Please report security issues via
[GitHub private vulnerability reporting](https://github.com/Gustavjiversen01/localdictate/security/advisories/new).

Do **not** open a public issue for security vulnerabilities.

You should receive an initial response within 7 days. If confirmed, a fix will
be released as soon as practical and you will be credited (unless you prefer
otherwise).
