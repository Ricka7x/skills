


A collection of reusable **AI agent skills** for modern TypeScript full-stack development.

These skills encode real architecture decisions, development patterns, and workflows used in production projects built with:

- Better Auth
- Hono
- oRPC
- TanStack Router
- TanStack Query
- TanStack Form
- Drizzle ORM
- React 19
- Expo
- Turborepo
- Bun

Each skill provides **procedural knowledge** that helps AI agents generate code consistent with the conventions of this stack.

---

# Install

Install the entire collection:

```bash
npx skills add Ricka7x/skills
````

Install a specific skill:

```bash
npx skills add Ricka7x/skills@better-t-stack-development
```

List available skills before installing:

```bash
npx skills add Ricka7x/skills --list
```

---

# Available Skills

| Skill                                 | Description                                                   |
| ------------------------------------- | ------------------------------------------------------------- |
| **better-t-stack-development**        | **Compound skill — all conventions for the Better-T-Stack architecture** (procedures, routing, forms, tables, auth, multi-tenancy, plugins, database, testing, native, payments, storage, email, AI, OpenAPI, base-ui migration) |
| **asset-forge**                       | Image/video asset generation & processing CLI (icons, OG images, conversion) |

---

# Repository Structure

```
skills/
  better-t-stack-development/
    SKILL.md
    references/        → procedures, routing, forms, tables, auth, multi-tenancy,
                         plugins, database, testing, native, payments, storage,
                         email, AI, OpenAPI, base-ui migration

  asset-forge/
    SKILL.md
```

The **better-t-stack-development** skill is the single source of truth for the stack — all
patterns live as references under it (no duplicated standalone skills).

Each skill directory contains:

* `SKILL.md` → skill definition and instructions
* `references/` → optional documentation loaded when needed

---

# What Are Agent Skills?

Agent skills are reusable instruction packages that extend AI agents with specialized capabilities.

A skill is typically a folder containing a `SKILL.md` file with structured instructions describing **when and how the agent should apply the skill**.

Skills can include:

* architecture patterns
* development workflows
* coding conventions
* API design guidelines
* testing strategies

---

# Supported Agents

These skills work with many AI development tools including:

* Claude Code
* Cursor
* OpenAI Codex
* GitHub Copilot
* Windsurf
* VS Code agents

---

# Contributing

New skills are welcome.

To add a new skill:

1. Create a new folder inside `skills/`
2. Add a `SKILL.md`
3. Optionally add documentation in `references/`

Example:

```
skills/my-new-skill/
  SKILL.md
  references/
```

---

# License

MIT

