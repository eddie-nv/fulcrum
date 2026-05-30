---
name: git-workflow
description: Git workflow patterns including branching strategies, commit conventions, merge vs rebase, conflict resolution, and collaborative development best practices for teams of all sizes.
origin: ECC
---

# Git Workflow Patterns

Best practices for Git version control, branching strategies, and collaborative development.

## When to Activate

- Setting up Git workflow for a new project
- Deciding on branching strategy
- Writing commit messages and PR descriptions
- Resolving merge conflicts
- Managing releases and version tags

## Branching Strategy (GitHub Flow)

```
main (protected, always deployable)
  │
  ├── feature/user-auth      → PR → merge to main
  ├── feature/payment-flow   → PR → merge to main
  └── fix/login-bug          → PR → merge to main
```

**Rules:**
- `main` is always deployable
- Create feature branches from `main`
- Open Pull Request when ready for review
- After approval and CI passes, merge to `main`

## Commit Messages (Conventional Commits)

```
<type>(<scope>): <subject>
```

| Type | Use For |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `refactor` | Code refactoring |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |
| `setup` | Initial project setup |

**Examples:**
```
feat(fork-engine): add parallel container fork with health check
fix(strategy): correct redis port in network-fix executor
setup: project foundation, docker infrastructure, target service containers
```

## Branch Naming

```
feature/<name>        feat/fulcrum-core-api
fix/<name>            fix/redis-port-detection
setup/<name>          setup/project-foundation
```

## PR Workflow

Every milestone follows this exact flow:
```bash
git checkout -b <branch>
# build
git add .
git commit -m "<type>(<scope>): <description>"
git push -u origin <branch>
# open PR → merge → checkout main → git pull
```

## Common Commands

```bash
# Start milestone
git checkout main && git pull
git checkout -b feat/my-milestone

# Stage and commit
git add .
git commit -m "feat(scope): description"

# Push and PR
git push -u origin feat/my-milestone
# open PR on GitHub

# After merge
git checkout main
git pull origin main

# Clean up
git branch -d feat/my-milestone
```

## .gitignore Essentials

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.env
.env.*

# Node
node_modules/
dist/
.next/

# Docker
*.log

# OS
.DS_Store
```

## Anti-Patterns

- Committing directly to main
- Giant PRs (500+ lines) — break into milestones
- Vague commit messages ("fix", "update", "WIP")
- Committing `.env` files or secrets
- Force pushing to main
