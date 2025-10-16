---
name: Dependency Update
about: Track dependency upgrades or security patches
title: '[DEPS] Update [package-name] to v[version]'
labels: dependencies
assignees: ''
---

## Dependency Information
**Package:** (e.g., fastapi, react, node)
**Current Version:**
**Target Version:**
**Ecosystem:**
- [ ] Python (pip)
- [ ] JavaScript (npm)
- [ ] Docker
- [ ] GitHub Actions
- [ ] Other: _______

## Update Type
- [ ] Security Patch (CVE fix)
- [ ] Major Version Update
- [ ] Minor Version Update
- [ ] Patch Update
- [ ] Automated (Dependabot PR)

## Reason for Update
- [ ] Security vulnerability
- [ ] Bug fixes
- [ ] Performance improvements
- [ ] New features needed
- [ ] Compatibility requirements
- [ ] Technical debt reduction

## Security Advisory (if applicable)
**CVE ID:**
**Severity:**
**CVSS Score:**
**Link:**

## Breaking Changes
<!-- List any breaking changes in the new version -->

-
-

## Migration Steps
<!-- What needs to change in our codebase? -->

1.
2.
3.

## Testing Plan
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance validated
- [ ] Security scan (Bandit/npm audit)
- [ ] Docker builds successfully

## Rollback Plan
<!-- How to revert if issues arise -->

## Related Issues/PRs
<!-- Link to Dependabot PR or related issues -->

## Checklist
- [ ] Changelog reviewed for breaking changes
- [ ] Dependencies updated in requirements.txt or package.json
- [ ] Lock files regenerated (requirements.txt, package-lock.json)
- [ ] Documentation updated
- [ ] CI/CD pipeline passes
