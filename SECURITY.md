# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | Yes                |
| 0.4.x   | Security fixes only|
| < 0.4   | No                 |

## Reporting a Vulnerability

**Do NOT report security vulnerabilities through public GitHub issues.**

Instead, please send an email to **security@bitcoinsapi.com** with the following information:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response Timeline

- **Acknowledgement:** Within 48 hours of report
- **Initial assessment:** Within 72 hours
- **Fix for critical issues:** Within 7 days
- **Fix for non-critical issues:** Within 30 days

## Scope

The following are in scope for security reports:

- Authentication or authorization bypasses
- Remote code execution via MCP tool inputs
- Information disclosure (e.g., leaking RPC credentials)
- Denial of service against the MCP server
- PSBT analysis tools providing misleading security assessments
- Unsafe transaction broadcasting behavior

## Out of Scope

- Vulnerabilities in Bitcoin Core itself (report those to [Bitcoin Core](https://bitcoincore.org/en/contact/))
- Issues requiring physical access to the host machine
- Social engineering attacks

## Disclosure Policy

We follow coordinated disclosure. We ask that you give us reasonable time to address the issue before any public disclosure. We will credit reporters in the release notes unless anonymity is requested.
