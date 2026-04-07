# Code Review Report

**Date:** {{DATE}}
**Reviewed Files:**
- {{FILE_LIST}}

## Summary
{{SUMMARY_OF_FINDINGS}}

## Critical Issues (Must Fix)
*Issues that violate the "Check for" or "Must have" requirements.*

### {{FILE_NAME}}
- [ ] **Line {{LINE_NUMBER}}**: {{DESCRIPTION}} (Requirement: {{REQUIREMENT}})
  - *Recommendation*: {{RECOMMENDATION}}

## Automated Fixes
*Changes applied automatically (spelling, docs).*

- [x] Fixed spelling in `{{FILE_NAME}}`.
- [x] Added docstring to `{{FUNCTION_NAME}}` in `{{FILE_NAME}}`.

## Manual Fixes Required
*Formatting requests, logic changes, testability improvements.*

- [ ] Install formatter: {{RECOMMENDED_FORMATTER}}
- [ ] Refactor `{{FUNCTION_NAME}}` in `{{FILE_NAME}}` for better testability.
- [ ] Remove dead code in `{{FILE_NAME}}`: line {{LINE_NUMBER}}.

## Suggestions (Good to Have)
- [ ] Test coverage is {{COVERAGE}}%. Consider using {{LIBRARY}} to improve coverage to 90%.

## Next Steps
1. Apply manual fixes.
2. Verify automated fixes.
3. Commit changes.
4. Delete this file.
