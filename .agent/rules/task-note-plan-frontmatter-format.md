---
trigger: always_on
---

## task-note-plan Format - Omega_KG

### TL;DR

A task-note-plan (`.tnp.md`) is a structured markdown file containing multiple tasks with a specific 4-section format. Each task uses checkbox syntax (`- [ ]`) for tracking. The lifecycle.py system tracks individual Task nodes in Neo4j, while the TNP provides the human-readable planning document.

---

### TNP File Structure

```
[IDENTIFIER] Project Name.tnp.md
```

Located in: `vault_path/Linear/` directory

---

### Required Sections

```markdown
## 1. High-Level Objective
[Parent issue title goes here]

## 2. "Done Means Done" Criteria
[Exit criteria for the entire project]

## 3. Task Breakdown
- [ ] [TASK-001] Task one description
- [ ] [TASK-002] Task two description
- [x] [TASK-003] Completed task (checkbox marked)

## 4. Notes & Context
- Linear URL: https://linear.app/...
- Additional context and notes
```

---

### Complete Example

```markdown
---
uid: APX-100
title: Implement User Authentication System
status: active
created: 2024-12-15T10:00:00Z
tags:
  - linear
  - priority/high
---

# Implement User Authentication System

## 1. High-Level Objective
Implement JWT-based authentication for the Omega_KG API with secure token management.

## 2. "Done Means Done" Criteria
- [ ] User registration endpoint returns 201 with user data
- [ ] Login endpoint returns JWT token
- [ ] Protected routes reject unauthenticated requests
- [ ] Token refresh endpoint works correctly
- [ ] All auth endpoints have unit tests (>80% coverage)

## 3. Task Breakdown
This is the granular, tactical list of work. **Every task here MUST use the `- [ ]` or `- [x]` syntax.**

- [ ] [APX-101] Set up JWT library dependencies
- [ ] [APX-102] Create user registration endpoint
- [ ] [APX-103] Implement login with token generation
- [ ] [APX-104] Create authentication middleware
- [ ] [APX-105] Implement token refresh endpoint
- [ ] [APX-106] Add unit tests for auth module
- [ ] [APX-107] Update API documentation

## 4. Notes & Context
Linear URL: https://linear.app/apexsigma/issue/APX-100

**Implementation Notes:**
- Use PyJWT library for token handling
- Token expiry: 15 minutes for access, 7 days for refresh
- Store refresh tokens in PostgreSQL with expiration
- Follow OWASP auth guidelines

**Related Resources:**
- [[Auth-Architecture-Doc]]
- [[API-Security-Checklist]]
```

---

### Frontmatter for TNP Files

| Field        | Required | Description                                        |
| ------------ | -------- | -------------------------------------------------- |
| `uid`        | Yes      | Parent project identifier (e.g., APX-100)          |
| `title`      | Yes      | Project/title name                                 |
| `status`     | Yes      | One of: `draft`, `active`, `completed`, `archived` |
| `created`    | Yes      | ISO datetime                                       |
| `tags`       | No       | List of tags                                       |
| `linear_id`  | No       | Link to Linear issue                               |
| `identifier` | No       | Human-readable Linear identifier                   |

---

### Key Syntax Rules

1. **Checkbox format**: Must use `- [ ]` (unchecked) or `- [x]` (checked)
2. **Task references**: Include UID in brackets `[TASK-XXX]`
3. **Section headers**: Use `## N. Section Name` format
4. **Nested tasks**: Use indentation for sub-tasks

---

### How Lifecycle.py Interacts with TNP

| Component                                          | Interaction                                   |
| -------------------------------------------------- | --------------------------------------------- |
| [`_find_violations()`](omega_kg/lifecycle.py:262)  | Queries `(t:Task)` nodes in Neo4j by status   |
| [`_update_task_file()`](omega_kg/lifecycle.py:345) | Updates individual task files, NOT TNP        |
| Linear sync                                        | Creates/updates TNP from Linear parent issues |

**Important**: The lifecycle system operates on individual Task nodes in Neo4j. Each checkbox in the TNP should correspond to a separate Task node with its own frontmatter file in `Tasks/` directory.

---

### File Discovery Pattern

| File Type        | Pattern                        |
| ---------------- | ------------------------------ |
| Individual tasks | `Tasks/**/{uid}*.md`           |
| TNPs             | `Linear/[IDENTIFIER] *.tnp.md` |

---

### Missing Template Note

The [`template_task-note-plan.tnp.md`](test_vault/template_task-note-plan.tnp.md) referenced in [`mapper.py:143`](omega_kg/domain/linear/mapper.py:143) does not exist. The system falls back to a basic 4-section structure when the template is missing.