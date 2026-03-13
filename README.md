


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
| **better-t-stack-development**        | Core development patterns for the Better-T-Stack architecture |
| **better-auth-plugin**                | Patterns for building custom Better Auth plugins              |
| **hono-orpc-endpoints**               | API architecture patterns using Hono + oRPC                   |
| **tanstack-router-orpc**              | Integration patterns between TanStack Router and oRPC         |
| **tanstack-form-architecture**        | Form architecture using TanStack Form and Zod                 |
| **shadcn-radix-to-base-ui-migration** | Migration patterns from Radix/shadcn to Base UI               |

---

# Repository Structure

```
skills/
  better-auth-plugin/
    SKILL.md
    references/

  better-t-stack-development/
    SKILL.md
    references/

  hono-orpc-endpoints/
    SKILL.md
    references/

  tanstack-router-orpc/
    SKILL.md
    references/

  tanstack-form-architecture/
    SKILL.md

  shadcn-radix-to-base-ui-migration/
    SKILL.md
```

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

