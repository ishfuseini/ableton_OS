# AbletonOS

Ableton project organizer and sample library manager for macOS.

## Prerequisites

- **Python 3.11+**
- **PocketBase** instance (self-hosted or hosted service)

## Installation

```bash
uv sync
```

## First-Time Setup

```bash
# Run the configuration wizard
uv run python -m abletonos init-config

# Check PocketBase connection
uv run python -m abletonos pb
```

## Usage

```bash
# Show all commands
uv run python -m abletonos --help

# Create a new project
uv run python -m abletonos new "My Song"

# Check PocketBase status
uv run python -m abletonos pb
```

## Configuration

Config is stored at `~/.abletonOS/config/config.yaml`:

```yaml
project_root: ~/Music/Ableton
pocketbase_url: https://your-pb-instance.com/api
```

## Development

```bash
uv sync --all-extras
uv run black src/
uv run ruff check src/
uv run pytest
```
