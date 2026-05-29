# Agent skills in this directory

## Project-specific skills

These folders existed before vendoring addyosmani/agent-skills (for example `docx`, `pptx`, `xlsx`, `canvas-design`, `frontend-design`, and others). They are maintained in this repository.

## addyosmani/agent-skills (vendored)

The following skill directories and the shared [`references/`](references/) folder were copied from **[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)** (MIT License).

| Field | Value |
|--------|--------|
| Upstream URL | https://github.com/addyosmani/agent-skills |
| Snapshot commit | `6ce029897d2b794940325fc7148774a6ec51111c` |
| License file | [`ADDY_AGENT_SKILLS_LICENSE.txt`](ADDY_AGENT_SKILLS_LICENSE.txt) |

### Shared `references/`

Upstream `SKILL.md` files refer to paths like `references/testing-patterns.md`. Each vendored skill directory contains a symlink `references` → `../references` so those paths resolve without editing upstream text.

### How to update

1. Clone or pull the latest upstream: `git clone https://github.com/addyosmani/agent-skills.git` (or `git pull` in an existing clone).
2. Copy `skills/*` into `.agents/skills/` (merge/replace as you intend).
3. Replace `.agents/skills/references/` with upstream `references/`.
4. Recreate per-skill symlinks if needed:

   ```bash
   SRC=/path/to/agent-skills
   for d in "$SRC/skills"/*; do
     name=$(basename "$d")
     ln -sfn ../references ".agents/skills/$name/references"
   done
   ```

5. Record the new upstream commit hash in this README.

### Agent personas (Cursor rules)

Upstream specialist prompts from `agents/` are copied into [`.cursor/rules/`](../.cursor/rules) with the prefix `addy-agent-skills-`:

- `addy-agent-skills-code-reviewer.md`
- `addy-agent-skills-test-engineer.md`
- `addy-agent-skills-security-auditor.md`

Overview of those personas: [`ADDY_AGENTS_README.md`](ADDY_AGENTS_README.md).

### Context note

The upstream pack contains many long workflows. Prefer invoking a specific skill by name in chat rather than expecting every file to load at once.
