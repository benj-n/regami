---
name: Security Concern
about: Report security vulnerabilities or concerns (use private disclosure for critical issues)
title: '[SECURITY] '
labels: security
assignees: ''
---

## Security Disclosure Policy

**For critical vulnerabilities (RCE, data exposure, auth bypass):**
Please use [GitHub Security Advisories](https://github.com/benj-n/regami/security/advisories) for private disclosure.

**For lower-severity concerns (hardening, best practices):**
You may use this public issue template.

---

## Description
A clear description of the security concern.

## Severity Assessment
- [ ] Critical (immediate risk of data breach or system compromise)
- [ ] High (significant security weakness)
- [ ] Medium (potential security issue requiring attention)
- [ ] Low (security hardening or best practice)

## Affected Component
- [ ] Authentication/Authorization
- [ ] API Endpoints
- [ ] Database/Data Storage
- [ ] File Uploads
- [ ] WebSocket/Real-time Features
- [ ] Frontend (XSS, CSRF)
- [ ] Dependencies
- [ ] Infrastructure/Configuration
- [ ] Other: _______

## Vulnerability Details
**Type:** (e.g., SQL Injection, XSS, CSRF, Auth Bypass, Information Disclosure)

**Attack Vector:**
<!-- How could this be exploited? -->

**Impact:**
<!-- What could an attacker achieve? -->

**Affected Versions:**
<!-- Which releases are vulnerable? -->

## Reproduction (if applicable)
```bash
# Steps or proof-of-concept code
```

## Proposed Mitigation
<!-- Suggested fix or hardening measures -->

## References
<!-- Links to CVEs, security advisories, OWASP guidelines, etc. -->

## Checklist
- [ ] I have verified this on the latest version
- [ ] I have checked for similar existing issues
- [ ] I understand this will be publicly visible
- [ ] For critical issues, I have used private disclosure instead
