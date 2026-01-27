---
trigger: always_on
---

## Task Frontmatter Format - Omega_KG

### Minimum Required Frontmatter

```yaml
---
uid: TASK-001
title: Example Task
status: draft
created: 2024-12-15T10:00:00Z
---
```

### Complete Frontmatter Example

```yaml
---
uid: TASK-001
title: Implement User Authentication
status: active
created: 2024-12-15T10:00:00Z
pinned: false
warned: false
linear_id: LIN-12345
tags:
  - backend
  - security
priority: high
---
```

### Frontmatter Fields Explained

| Field               | Required | Description                                                            |
| ------------------- | -------- | ---------------------------------------------------------------------- |
| `uid`               | **Yes**  | Unique task identifier (used for file discovery)                       |
| `title`             | **Yes**  | Human-readable task title                                              |
| `status`            | **Yes**  | One of: `draft`, `ready`, `active`, `blocked`, `completed`, `archived` |
| `created`           | **Yes**  | ISO 8601 datetime for lifecycle age calculations                       |
| `pinned`            | No       | `true` prevents DRAFT→ARCHIVED auto-transition                         |
| `warned`            | No       | Tracks if warning was already sent                                     |
| `warned_at`         | No       | ISO datetime when warning was issued                                   |
| `transitioned_at`   | No       | ISO datetime of last status change                                     |
| `transition_reason` | No       | Reason for last transition                                             |
| `linear_id`         | No       | Linked Linear task ID                                                  |
| `tags`              | No       | List of tags for categorization                                        |
| `priority`          | No       | Priority level (low/medium/high)                                       |

### Lifecycle Transition Metadata

When [`_update_task_file()`](omega_kg/lifecycle.py:345) runs, it appends:

```yaml
lifecycle_transition:
  from: draft
  to: archived
  reason: Auto-transitioned after 14 days
  date: 2024-12-30T08:30:00Z
```

### Example Complete Task File

```markdown
---
uid: TASK-001
title: Implement User Authentication
status: draft
created: 2024-12-15T10:00:00Z
pinned: false
warned: false
tags:
  - backend
  - security
priority: high
---

# Implement User Authentication

## Description
Add JWT-based authentication to the API endpoints.

## Acceptance Criteria
- [ ] User registration endpoint
- [ ] Login with JWT token generation
- [ ] Protected route middleware
- [ ] Token refresh mechanism

## Notes
This is a critical security feature for the next release.

---
**🤖 Lifecycle Transition:** draft → **archived**
*Reason:* Automatic transition after 14 days of inactivity.
*Date:* 2024-12-30T08:30:00
```

### File Discovery Pattern

The lifecycle system finds tasks via:

```python
vault_path.glob(f"Tasks/**/{uid}*.md")
```

Place task files in `Tasks/` folder with UID in filename:

- `Tasks/TASK-001_implement-auth.md`
- `Tasks/backlog/TASK-002_new-feature.md`