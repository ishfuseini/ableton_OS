# AbletonOS

## Project Overview

AbletonOS is a CLI tool for organizing Ableton projects and managing a sample library with PocketBase backend. PocketBase is hosted externally (not embedded in CLI).

## Key Paths

- **Worktree for development**: `.worktrees/` (hidden directory, already in .gitignore)
- **AbletonOS config**: `~/.abletonOS/config/config.yaml` (XDG-style, not in project)
- **PocketBase**: User-hosted at `https://ableton.ish.place/api` (configured in config.yaml)
- **Logs**: `~/.abletonOS/logs/`

## Development Workflow

1. **Worktrees for isolation**: Use `.worktrees/` for feature development
2. **Phase branches**: Each phase gets its own worktree (e.g., `.worktrees/phase-4`)
3. **Test before commit**: Always run `uv run python -m abletonos <command>` to verify

## Running Commands

```bash
# From project root or any worktree
uv sync

# Run the CLI
uv run python -m abletonos --help

# Run tests
uv run pytest
```

## Common Mistakes to Avoid

- **No `uv sync` after changes**: Always run `uv sync` after modifying `pyproject.toml`
- **Don't expand ~ manually**: Use flags with `~` - it expands automatically

## CLI Commands

| Command | Description |
|---------|-------------|
| `init-config` | Interactive wizard (--project-root, --library-root, --pocketbase-url) |
| `pb` | Check PocketBase connection status |
| `add-samples <folder>` | Analyze, preview, and import a sample pack into the organized library |

## Config File Format

```yaml
project_root: /Users/ishmusic/Music/Ableton
library_root: /Users/ishmusic/Music/Samples
pocketbase_url: https://ableton.ish.place/api
```

## Sample Library Structure

```
<library_root>/
  Drums/
    <pack-name>/
      kick_01.wav
      snare_01.wav
  Bass/
    <pack-name>/
      ...
  Synth/ | FX/ | Vocals/ | Guitar/ | Other/
```

Classification: folder-name keywords take priority, then filename keywords, then "Other".