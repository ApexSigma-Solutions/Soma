---
description: Stage changes, commit and push changes to origin beta remote. 
---

You are acting as a senior DevOps engineer. Please execute the following Git workflow to deploy the current changes in all projects to their respective origin beta branch.

Adhere to these industry standard best practices:
1. **Branch Verification**: Verify we are currently on the beta branch. If not, checkout Beta.
2. **Synchronization**: Perform a `git pull --rebase origin Beta` to integrate remote changes and maintain a clean linear history.
3. **Quality Check**: Review the staged changes for any inadvertent secrets (API keys, passwords) before committing. Abort if found.
4. **Staging**: Stage all modified files using `git add .`.
5. **Commit Message**: Create a commit using the Conventional Commits specification.
   - Type: `fix`
   - Scope: `auth` or `capture`
   - Subject: "resolve Neo4j authentication and browser capture stability issues"
   - Body: Summarize the technical changes based on the diff (e.g., token refresh logic, capture buffer handling).
6. **Push**: Push the changes to the remote repository using `git push origin Beta`.

Provide a summary of the actions taken and the resulting commit hash.