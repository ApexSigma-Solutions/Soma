# Project Rules and Standards

This document outlines the mandatory rules and standards for all projects within the organization. Adherence to these guidelines ensures consistency, maintainability, and quality across our codebases.

## 1. Repository Architecture & Hygiene

- **Standard Structure:** The repository root must include a properly populated and linted `.vscode/`, `.github/`, `.gitignore`, `.dockerignore`, and `Dockerfile`.
- **Code Hygiene:** Repositories must be purged of unnecessary scripts, orphaned markdown files, and legacy tests before initialization.
- **Branching Strategy:** Adhere to a **Trunk-based Development** or **GitFlow** model. All feature branches must be merged via Pull Requests with mandatory peer review.

## 2. Runtime & Dependency Management

- **Python Version:** 3.12.10
- **Package Manager:** **Poetry (>2.2.0)** is the exclusive tool for dependency, project, and virtual environment management.
- **Integrity:** `pyproject.toml` and `poetry.lock` must remain synchronized. Lock files must be committed to version control to ensure deterministic builds.

## 3. Code Quality & Standards

- **Linting & Formatting:** Managed exclusively by **Ruff**. Configuration should be defined in `pyproject.toml`.
- **Type Safety:** Strict type hinting is required for all function signatures and class attributes.
- **Documentation:**

  - **Docstrings:** All public functions, classes, and modules must follow the **Google** or **NumPy** docstring format.
  - **Automated Docs:** Project documentation is generated via **MKDocs** from source docstrings.
  - **README:** A comprehensive `README.md` must detail the project purpose, setup instructions, architectural decisions, and API references.

## 4. API Design & Documentation

- **Framework:** All services utilize **FastAPI**.
- **Specification:** A **Swagger/OpenAPI** specification must be exposed for all public endpoints.
- **Versioning:** APIs must be versioned (e.g., `/v1/...`) to ensure backward compatibility.

## 5. Configuration & Security

- **Settings Management:** Implemented via **Pydantic `BaseSettings`** for type-safe configuration.
- **Environment Variables:** Handled via local-only `.env` files; a version-controlled `.env.example` template is mandatory.
- **Secrets Management:** **Bitwarden Secrets Manager** is utilized to enforce Zero Trust principles. Hardcoded credentials or secrets in version control are strictly prohibited.

## 6. Testing & Quality Assurance

- **Framework:** **Pytest** is the standard testing framework.
- **Coverage:** Maintain a minimum of 80% code coverage. Coverage reports should be generated during CI.
- **Test Types:** Implement a pyramid of Unit, Integration, and End-to-End (E2E) tests.

## 7. Project Management & Version Control

- **Workflow:** Tasks planned in **Obsidian** are promoted to issues in **Linear**, and in turn become issues in **GitHub**.
- **Project Management:** **Linear** is used for project management and coordinating issues and tasks.
- **Commit Strategy:** Commits must be atomic and follow the **Conventional Commits** specification.
- **Platform:** GitHub is the primary platform for VCS and collaborative development.
- **Automation:** GitHub Actions must be used for CI/CD pipelines, including automated linting, testing, and container builds.
- **Version Control:** All repositories must be initialized with a clean commit history, free of merge commits, and with no orphaned branches.
- **Database Migrations:** Managed via **Alembic** for SQLAlchemy-based projects, ensuring version-controlled schema changes.

## 8. Development Environment

- **Shell:** **PowerShell** is the primary development shell.
- **Containerization:** Multi-stage `Dockerfile` builds are required to optimize image size and security.
- **IDE Configuration:** A standardized `.vscode/` setup must be included for consistent development environments across the team.
- **Local Development:** Use of `docker-compose` for local development environments is encouraged to mirror production setups.

## 9. Logging & Monitoring

- **Logging Framework:** Utilize Python's built-in `logging` module, configured for structured logging.
- **Monitoring:** Integrate with monitoring solutions (e.g., Prometheus, Grafana) for production services to track performance and errors.
