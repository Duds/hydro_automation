# Security Audit Instructions

## Purpose
Step-by-step security audit instructions for Cursor to check the hydroponic automation project for security vulnerabilities.

## Audit Process

### Step 1: Check for Hardcoded Credentials

**Action**: Search codebase for hardcoded passwords, API keys, or credentials.

**Commands to run:**
```bash
# Search for hardcoded passwords
grep -r "password.*=" src/ --include="*.py" | grep -v "#" | grep -v "self.password" | grep -v "password:" | grep -v "password,"

# Search for email patterns that might be hardcoded
grep -r "@.*\.com\|@.*\.au" src/ --include="*.py" | grep -v "#" | grep -v "example.com"

# Search for API keys
grep -r "api.*key\|apikey\|API_KEY" src/ --include="*.py" -i

# Search for device IDs or MAC addresses
grep -r "[0-9A-F]\{12\}" src/ --include="*.py" | grep -v "#"
```

**Expected result**: No hardcoded credentials found. All credentials should come from config files.

**If found**: Flag as CRITICAL - credentials must be removed and moved to config.

---

### Step 2: Verify Sensitive Files in .gitignore

**Action**: Check that sensitive files are properly gitignored.

**Commands to run:**
```bash
# Check .gitignore contents
cat .gitignore | grep -E "config.json|DEVICE_INFO|\.log"

# Verify sensitive files are not tracked
git ls-files | grep -E "config/config.json|DEVICE_INFO.md"

# Check if any sensitive files are staged
git diff --cached --name-only | grep -E "config/config.json|DEVICE_INFO.md"
```

**Expected result**: 
- `.gitignore` contains `config/config.json` and `DEVICE_INFO.md`
- These files are NOT in `git ls-files` output
- These files are NOT in staged changes

**If found**: Flag as CRITICAL - remove from git tracking immediately.

---

### Step 3: Audit API Password Sanitization

**Action**: Verify all API endpoints that return config data sanitize passwords.

**File to check**: `src/web/api.py`

**Specific checks:**
1. Find all endpoints that return config data:
   ```bash
   grep -n "get_config\|config" src/web/api.py | grep "@self.app"
   ```

2. Verify password sanitization in `get_config()`:
   - Check line ~214-218 in `src/web/api.py`
   - Must contain: `device_config["password"] = "***"`
   - Must NOT return actual password value

3. Check for any other endpoints that might expose config:
   ```bash
   grep -A 10 "@self.app" src/web/api.py | grep -B 5 -A 5 "config\|password"
   ```

**Expected result**: All config-returning endpoints sanitize passwords to `"***"`.

**If found**: Flag as HIGH - passwords must be sanitized before returning to client.

---

### Step 4: Check for Sensitive Data in Logs

**Action**: Verify logging doesn't expose sensitive information.

**Commands to run:**
```bash
# Search for password logging
grep -r "logger.*password\|log.*password\|print.*password" src/ --include="*.py" -i

# Search for email logging (should be minimal)
grep -r "logger.*email\|log.*email" src/ --include="*.py" -i | grep -v "example.com"

# Check error messages that might expose credentials
grep -r "raise\|except\|error\|Error" src/ --include="*.py" | grep -i "password\|email\|credential"
```

**Expected result**: 
- No passwords logged (except masked: `'*' * len(password)`)
- Error messages don't include actual credentials
- Email addresses only logged if necessary and safe

**If found**: Flag as MEDIUM - sanitize log output.

---

### Step 5: Verify Input Validation

**Action**: Check that all API endpoints validate and sanitize user input.

**File to check**: `src/web/api.py`

**Specific checks:**
1. Find all POST/PUT endpoints:
   ```bash
   grep -n "@self.app\.\(post\|put\)" src/web/api.py
   ```

2. For each endpoint, verify:
   - Uses Pydantic models for request validation
   - Validates file paths (no directory traversal)
   - Validates time formats
   - Validates numeric ranges

3. Check for path traversal vulnerabilities:
   ```bash
   grep -A 5 "open\|Path\|file" src/web/api.py | grep -E "\.\./|\.\.\\\\"
   ```

**Expected result**: All user inputs validated, file paths sanitized.

**If found**: Flag as HIGH - add input validation.

---

### Step 6: Check Error Message Exposure

**Action**: Verify error messages don't expose sensitive information.

**Commands to run:**
```bash
# Search for error messages that might expose credentials
grep -r "HTTPException\|raise.*Error\|except.*:" src/web/api.py -A 3 | grep -i "password\|email\|credential\|device.*id"

# Check for detailed error messages in API responses
grep -r "detail=\|message=" src/web/api.py | grep -v "#"
```

**Expected result**: 
- Error messages are generic (e.g., "Connection failed" not "Invalid password for user@example.com")
- No credentials in exception messages
- Detailed errors logged server-side, generic errors returned to client

**If found**: Flag as MEDIUM - sanitize error messages.

---

### Step 7: Verify Config File Handling

**Action**: Check that config files are handled securely.

**File to check**: `src/main.py`

**Specific checks:**
1. Verify config loading doesn't expose passwords:
   ```bash
   grep -A 20 "_load_config" src/main.py | grep -i "password\|print\|log"
   ```

2. Check config validation:
   - Config file path is validated
   - Required fields are checked
   - No default passwords or credentials

**Expected result**: Config loaded securely, no credentials exposed during load.

**If found**: Flag as MEDIUM - improve config handling.

---

### Step 8: Check Network Security

**Action**: Verify network operations are secure.

**Files to check**: `src/tapo_controller.py`, `src/bom_temperature.py`

**Specific checks:**
1. Verify timeouts are set:
   ```bash
   grep -r "timeout\|Timeout" src/ --include="*.py" | grep -v "#"
   ```

2. Check for insecure HTTP (should only be for public BOM API):
   ```bash
   grep -r "http://" src/ --include="*.py" | grep -v "bom.gov.au\|#"
   ```

3. Verify User-Agent headers for external APIs:
   ```bash
   grep -A 5 "requests.get\|requests.post" src/bom_temperature.py
   ```

**Expected result**: 
- All network calls have timeouts
- Only BOM API uses HTTP (public data, acceptable)
- User-Agent header set for BOM API

**If found**: Flag as LOW - add timeouts or improve security.

---

### Step 9: Check Dependencies for Vulnerabilities

**Action**: Verify dependencies don't have known vulnerabilities.

**Commands to run:**
```bash
# Check if pip-audit is available
pip list | grep pip-audit || echo "pip-audit not installed"

# If available, run audit
pip-audit --requirement requirements.txt 2>/dev/null || echo "Run: pip install pip-audit && pip-audit -r requirements.txt"
```

**Expected result**: No known vulnerabilities in dependencies.

**If found**: Flag as HIGH - update vulnerable dependencies.

---

### Step 10: Verify Web Server Security

**Action**: Check web server configuration for security issues.

**File to check**: `src/web/api.py`, `src/main.py`

**Specific checks:**
1. Verify web server host binding:
   ```bash
   grep -r "host.*=" src/ --include="*.py" | grep -E "web\|api\|uvicorn"
   ```

2. Check for authentication:
   ```bash
   grep -r "auth\|login\|password\|token" src/web/api.py -i | grep -v "device_config\|password.*="
   ```

**Expected result**: 
- Web server binds to `0.0.0.0` (local network only)
- No authentication implemented (acceptable for local network)
- Documentation warns against public internet exposure

**If found**: Flag as INFO - document security assumptions.

---

### Step 11: Check Commit History for Secrets

**Action**: Verify no sensitive data was committed in the past.

**Commands to run:**
```bash
# Check commit messages for sensitive data
git log --all --grep="password\|secret\|key\|credential" -i

# Check for passwords in recent commits (last 10)
git log -10 --pretty=format:"%H %s" | while read hash msg; do
  git show $hash | grep -i "password\|secret" | grep -v "^\+.*password.*=" | grep -v "^\-\-.*password.*="
done
```

**Expected result**: No sensitive data in commit history.

**If found**: Flag as CRITICAL - credentials may need to be rotated.

---

## Audit Report Template

After completing all steps, generate a report:

```
SECURITY AUDIT REPORT
=====================

Date: [current date]
Auditor: Cursor AI

CRITICAL ISSUES:
- [List any CRITICAL findings]

HIGH ISSUES:
- [List any HIGH findings]

MEDIUM ISSUES:
- [List any MEDIUM findings]

LOW ISSUES:
- [List any LOW findings]

INFO:
- [List any informational findings]

RECOMMENDATIONS:
- [List security improvement recommendations]
```

---

## Quick Security Checklist

Run this checklist before any commit:

- [ ] No hardcoded credentials in code
- [ ] `config/config.json` in `.gitignore` and not tracked
- [ ] `DEVICE_INFO.md` in `.gitignore` and not tracked
- [ ] All API endpoints sanitize passwords
- [ ] No sensitive data in logs
- [ ] Input validation on all API endpoints
- [ ] Error messages don't expose credentials
- [ ] Network calls have timeouts
- [ ] Dependencies are up to date
- [ ] Web server not exposed to public internet

---

## Automated Checks

**Pre-commit hook suggestion:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for sensitive files
if git diff --cached --name-only | grep -E "config/config.json|DEVICE_INFO.md"; then
    echo "ERROR: Attempting to commit sensitive files!"
    exit 1
fi

# Check for hardcoded passwords
if git diff --cached | grep -i "password.*=.*['\"].*[^=]"; then
    echo "WARNING: Possible hardcoded password detected!"
    echo "Review the changes before committing."
fi

exit 0
```
