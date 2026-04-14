# AbletonOS

## Project Overview

AbletonOS is a CLI tool for organizing Ableton projects and managing a sample library with PocketBase backend. PocketBase is hosted externally (not embedded in CLI).

## Key Paths

- **Worktree for development**: `.worktrees/` (hidden directory, already in .gitignore)
- **Phase 1 worktree**: `.worktrees/phase-1/` - Active development for Phase 1
- **AbletonOS config**: `~/.abletonOS/config/config.yaml` (XDG-style, not in project)
- **PocketBase**: User-hosted at `https://ableton.ish.place/api` (configured in config.yaml)
- **Logs**: `~/.abletonOS/logs/`

## Development Workflow

1. **Worktrees for isolation**: Use `.worktrees/` for feature development
2. **Phase branches**: Each phase gets its own worktree (e.g., `.worktrees/phase-1`)
3. **Test before commit**: Always run `uv run python -m abletonos <command>` to verify

## Running Commands

```bash
# From worktree directory
cd .worktrees/phase-1

# Install dependencies
uv sync

# Run the CLI
uv run python -m abletonos init-config --help

# Run tests
uv run pytest
```

## Phase 1 Tasks (completed)

1. [DONE] init-config interactive wizard - prompts for project root and PB URL
2. [DONE] config.yaml read/write module - atomic writes, XDG paths
3. [DONE] pb status command - HTTP health-check to hosted PB

## Common Mistakes to Avoid

- **No `uv sync` after changes**: Always run `uv sync` after modifying `pyproject.toml`
- **Wrong worktree**: Phase 1 worktree is `.worktrees/phase-1`, not `phase-1/`
- **Don't expand ~ manually**: Use `--project-root` flag with `~` - it expands automatically

## CLI Commands

| Command | Description |
|---------|-------------|
| `init-config` | Interactive wizard for initial setup (--project-root, --pocketbase-url) |
| `pb` | Check PocketBase connection status |
| `new` | Create new Ableton project |
| `import` | Import existing project |

## Config File Format

```yaml
project_root: /Users/ishmusic/Music/Ableton
pocketbase_url: https://ableton.ish.place/api
```