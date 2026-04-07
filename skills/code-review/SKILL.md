---
name: code-review
description: Review code before committing, inspect staged files, suggest fixes, and produce a markdown review report. Use when asked to do a code review or check staged files before a commit.
---

# Code Review

## When to use this skill

Use this skill when the user wants to:

- Perform a code review.
- Check staged files.
- Review code before committing.

## What to do

Perform the following tasks during the review.

### Must have

1. **No inline comments**: Avoid comments between code lines unless absolutely necessary. Move them to the top of the function as documentation or docstrings when possible.
2. **Function documentation**: Ensure non-trivial functions have documentation or docstrings. Very simple functions may be exempt.
3. **Appropriate logging**: Add logging in important places, but avoid excessive logging.

## Check for

1. **Repeated code**: Identify and flag DRY violations.
2. **Spelling mistakes**: Check for typos in code and comments.
3. **Formatting**: Ensure code is properly formatted.
4. **No TODOs**: The code should not contain TODO comments.
5. **Complex dependencies**: Functions should not have high coupling or invalid dependencies.
6. **Testability**: Code should be written in a unit-testable way, for example by using dependency injection where appropriate.
7. **Single responsibility**: Each function or class should have a concrete, single purpose.
8. **Linter suppression**: Strictly disallow comments that suppress linter checks, such as `// eslint-disable` or `#[allow(...)]`, unless they are absolutely necessary.
9. **Dead code**: Identify unused code using language-appropriate tools.

## How to fix

1. **Spelling mistakes**: Fix them yourself.
2. **Formatting**: Ask the user to install a formatter first, then recommend the best formatter for the language.
3. **Documentation**: Update the documentation yourself if the change is small.
4. **Other issues**: Point the user to the exact place that needs to be changed so they can edit it.

## How to process the review

1. **Output**: Write the review output in markdown format.
2. **Comparison**: When resubmitting a review, check the previous markdown review if it exists and acknowledge what changed.
3. **Cleanup**: After the user commits the changes, delete the review file.

## Good to have

1. **Test coverage**: Check test coverage. If it is below 90% or missing, suggest a good library to improve it.

## Assets

- [review_template.md](assets/review_template.md): A template for the markdown review report.
