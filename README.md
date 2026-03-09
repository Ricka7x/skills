# skills

Personal Claude skills repository for [@ricka7x](https://github.com/ricka7x).

Skills extend Claude's capabilities for specific tasks — giving it domain knowledge, workflows, and best practices it can reference during conversations.

## Structure

```
skills/
├── README.md
└── ricka7x/
    ├── better-auth-plugin/       # source (editable)
    │   └── SKILL.md
    └── better-auth-plugin.skill  # packaged (installable)
```

Each skill lives as two things:
- **A folder** (`skill-name/`) — the human-editable source, with a `SKILL.md` at its root
- **A `.skill` file** (`skill-name.skill`) — the packaged version you install into Claude via [skills.sh](https://skills.sh)

## Skills

| Skill | Description |
|---|---|
| [better-auth-plugin](./ricka7x/better-auth-plugin/) | Create Better Auth server & client plugins with correct structure, TypeScript types, and best practices |

## Workflow

### Installing a skill
Download the `.skill` file and install it via the skills.sh interface.

### Editing a skill
1. Edit `ricka7x/<skill-name>/SKILL.md` (and any supporting files)
2. Repackage it using the skill-creator tool in Claude
3. Replace the old `.skill` file with the new one
4. Commit and push

### Creating a new skill
Use the **skill-creator** skill inside Claude — it handles drafting, testing, and packaging. Then add both the folder and `.skill` file here.

## Skill Anatomy

A `SKILL.md` file starts with a YAML frontmatter block:

```markdown
---
name: my-skill
description: >
  What this skill does and when Claude should use it.
  Be specific about trigger contexts.
---

# My Skill

Instructions for Claude...
```

Skills can also include optional supporting directories:
- `references/` — additional docs loaded into context as needed
- `scripts/` — executable code for deterministic tasks
- `assets/` — templates, fonts, or other static files