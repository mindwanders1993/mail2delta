---
name: kaizen
description: Global GitHub workflow guidelines, branching strategies, and agentic execution standards. Incorporates Karpathy's principles (Simplicity First, Surgical Changes), flexible branching (feature->main or feature->dev->main), Conventional Commits, pre-push quality gates, and automated PR creation via gh CLI.
---

# `kaizen` — Continuous Disciplined Development & GitHub Workflow

> **Definition:** *Kaizen (改善)* — Japanese philosophy of continuous, disciplined, high-quality improvement.

When making codebase changes, managing Git branches, writing commits, opening Pull Requests, or executing CI/CD tasks, ALL AI agents MUST strictly follow the principles and workflows outlined in this document.

---

## 1. Karpathy Agentic Engineering Principles

### 🧠 Think Before Coding
- **State assumptions explicitly:** Never guess silently. If the target branch (`main` vs `dev`) or scope is ambiguous, ask the user.
- **Present multiple options:** If there are multiple ways to implement a feature or structure a branch, outline the trade-offs.
- **Push back on unnecessary complexity:** If 200 lines can be written in 50, explain why and write the simpler version.
- **Stop when confused:** If a build fails or requirements are unclear, state the exact problem and seek input before making broad code edits.

### 🎯 Simplicity First
- **Minimum viable change:** Solve the exact problem asked. Write zero speculative code or unrequested abstractions.
- **Surgical changes:** Touch ONLY what is necessary. Leave adjacent formatting, comments, and unrelated code untouched.
- **Clean up your own mess:** If you introduce temporary scratch files or test artifacts, delete them before committing.

### 🔬 Goal-Driven Execution
- **Empirical verification required:** Never claim a task is complete or open a PR until local build checks, linters, and unit tests pass cleanly.

---

## 2. Branching Strategy

### Flow Selection Matrix

1. **Standard Flow (`feature → main`)** *(Default)*:
   - Primary stable branch is `main`.
   - Feature branches branch directly off `main` and merge back into `main` via PR.

2. **Staging Flow (`feature → dev → main`)**:
   - Used when specified by the user or project convention.
   - Feature branches branch off `dev`, merge into `dev` via PR, and `dev` is later merged into `main`.

> [!TIP]
> **Branch Target Prompting:** If the repository has both `main` and `dev` branches and the user hasn't specified the target flow, ask: *"Should this feature branch merge into `dev` or directly into `main`?"*

### Branch Naming Conventions
- `feat/<scope>-<description>` — New features (e.g. `feat/audio-resampler`, `feat/dashboard-ui`)
- `fix/<scope>-<description>` — Bug fixes (e.g. `fix/mic-permission`, `fix/sigabrt-crash`)
- `docs/<topic>` — Documentation updates (e.g. `docs/architecture-primer`)
- `chore/<task>` — Maintenance, toolchain, or dependency updates (e.g. `chore/deps-update`)

---

## 3. Conventional Commit Standard

Commit messages MUST follow the Conventional Commits specification:
`type(scope): concise imperative description`

### Types
- `feat`: A new feature for the user
- `fix`: A bug fix
- `docs`: Documentation-only changes
- `perf`: A code change that improves performance
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Maintenance tasks, build scripts, dependency updates

### Rules
- Use imperative mood: `feat(asr): add whisper model` (NOT `added whisper model`)
- Keep header line under 72 characters.
- Never write generic commits like `updated files` or `fixed bugs`.

---

## 4. Pre-Push Quality Gate

Before committing or pushing, the AI agent MUST execute local verification commands:

### Rust Workspaces
```bash
cargo check --workspace
cargo clippy --workspace -- -D warnings
cargo test --workspace
```

### JavaScript / TypeScript Projects
```bash
npm run lint # or pnpm / yarn
npm test
npm run build
```

### Python Projects
```bash
pytest
ruff check . # or flake8
```

---

## 5. Pull Request (PR) Strategy & Automation

When the user asks to **"create a PR"**, **"open PR"**, or **"submit PR"**, the AI agent executes the following steps:

1. **Verify Quality Gate**: Ensure all local tests and linters pass cleanly.
2. **Push Feature Branch**: Push branch to remote: `git push -u origin <current-branch>`.
3. **Construct PR Body**: Generate a structured markdown file (`/tmp/pr_body.md`).

### PR Template

```markdown
## Summary
Brief 2-3 sentence overview of what this PR introduces and why.

## Key Changes
- Item 1: Detail of change
- Item 2: Detail of change

## Verification Evidence
- [x] Local build passed cleanly
- [x] Linters passed with zero warnings
- [x] Unit / Integration tests passed

## Karpathy Compliance Checklist
- [x] Touch only necessary code (Surgical changes)
- [x] No unrequested abstractions or bloat (Simplicity first)
```

4. **Create PR via GitHub CLI**:
```bash
gh pr create \
  --base <target-branch> \
  --head <current-branch> \
  --title "type(scope): Concise title matching commit" \
  --body-file /tmp/pr_body.md
```

---

## 6. Merge & Post-Merge Policy

- **Default Merge Method**: **Squash and Merge** (ensures a single atomic, clean commit on target branch).
- **Branch Cleanup**: After successful PR merge, delete both remote and local feature branches:
```bash
git checkout <target-branch>
git pull origin <target-branch>
git branch -d <feature-branch>
git push origin --delete <feature-branch>
```

---

## 7. Step-by-Step AI Agent Playbook

When given a task under the `kaizen` skill:

1. **Checkout & Branch**: Ensure clean working tree, pull latest target branch, and create feature branch (`feat/...` or `fix/...`).
2. **Surgical Implementation**: Write minimal, robust code following project code standards.
3. **Local Quality Verification**: Run build checks, linters, and unit tests.
4. **Conventional Commit**: Write crisp commit messages using `type(scope): description`.
5. **PR Creation (if requested)**: Push branch and run `gh pr create` with structured template.
6. **Clean Up**: Remove any temporary scratch files or test artifacts created during execution.
