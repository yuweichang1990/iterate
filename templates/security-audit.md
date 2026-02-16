---
name: security-audit
description: "Security-focused analysis — vulnerabilities, attack surface, hardening"
mode: research
---

Security audit: {{TOPIC}}

You are conducting a security-focused audit of the codebase in the current working directory. Identify vulnerabilities, assess risk, and provide actionable remediation guidance.

## Structure your exploration as follows:

1. **Attack Surface** (iteration 1): Entry points, exposed APIs, authentication boundaries, trust zones
2. **Input Validation** (iteration 2): User input handling, sanitization, injection vectors (SQL, XSS, command, path traversal)
3. **Authentication & Authorization** (iteration 3): Auth mechanisms, session management, privilege escalation paths
4. **Secrets Management** (iteration 4): Hardcoded credentials, API keys, environment variables, secret rotation
5. **Dependencies** (iteration 5): Known CVEs, outdated packages, supply chain risks
6. **Data Protection** (iteration 6): Encryption at rest/in transit, PII handling, data leakage paths
7. **Configuration** (iteration 7): Security headers, CORS, CSP, TLS settings, debug modes in production
8. **Error Handling** (iteration 8): Information leakage in errors, stack traces, verbose logging
9. **Race Conditions & Logic** (iteration 9): TOCTOU bugs, business logic flaws, state management issues
10. **Remediation Plan** (iteration 10+): Prioritized findings (Critical/High/Medium/Low) with specific fixes

For each finding, include:
- **Severity**: Critical / High / Medium / Low
- **Location**: File path and line number
- **Description**: What the issue is and how it could be exploited
- **Remediation**: Specific code changes or configuration fixes

Read actual source files. Reference specific files and line numbers.

Write findings to {{OUTPUT_DIR}}/. Start with 00-overview.md for an attack surface overview.
Each iteration, write a numbered file (01-<subtopic>.md, 02-<subtopic>.md, etc.).
Update {{OUTPUT_DIR}}/_index.md each iteration.

Always end your response with:
<explore-next>specific security area to audit next</explore-next>
