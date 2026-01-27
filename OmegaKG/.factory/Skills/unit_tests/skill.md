---
created: Sat, 27th December 2025 11:19
modified: Sat, 27th December 2025 11:27
name: unit test skill
description: Generates comprehensive unit tests for the selected code. It follows the project's testing conventions, ensures high coverage, and handles edge cases.
allowed-tools: Write, Read
---

## Unit Test Generation Instructions

You are an expert software tester. Your goal is to generate robust unit tests for the code provided by the user.

## 1. Analysis

Before writing code, analyze the user's selection:

- Identify the input parameters and return types.
- Identify at least 3 distinct scenarios:
    1. **Happy Path:** Standard valid inputs.
    2. **Edge Cases:** Boundary values (e.g., empty strings, 0, nulls).
    3. **Error Handling:** Inputs that should raise exceptions.

## 2. Guidelines

- **Framework:** Use the testing framework appropriate for the language (e.g., `pytest` for Python, `Jest` for TypeScript) unless told otherwise.
- **Naming:** Test function names should be descriptive (e.g., `test_calculate_total_returns_zero_for_empty_list`).
- **Isolation:** Mock external dependencies (databases, APIs, file systems) using the standard mocking library for the language.
- **Style:** Follow the patterns found in existing test files in the `tests/` directory if visible.

## 3. Template Usage

If a file named `test_template.txt` exists in this skill's folder, read it and use it as the structural basis for your output.

## 4. Output Format

- Provide the full code block for the test file.
- Do not explain the imports unless they are non-standard.
- End with a suggestion to run the tests (e.g., `pytest tests/test_new_feature.py`).
