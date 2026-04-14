"""CLI module for AbletonOS."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm

from abletonos.logging_config import setup_logging
from abletonos.config import (
    CONFIG_FILE,
    AbletonOSConfig,
    ensure_directories,
    load_config,
    save_config,
)


def expand_path(path: str) -> str:
    """Expand ~ and environment variables in path."""
    return os.path.expanduser(os.path.expandvars(path))


console = Console()
app = typer.Typer(
    name="abletonos",
    help="Ableton project organizer and sample library manager for macOS.",
)


@app.callback()
def callback(debug: bool = typer.Option(False, "--debug", help="Enable debug logging")):
    """AbletonOS - Keep your Ableton projects portable and sample library searchable."""
    setup_logging(debug=debug)


@app.command()
def init_config(
    project_root: str | None = typer.Option(
        None, "--project-root", "-p", help="Project root path (e.g., ~/Music/Ableton)"
    ),
    pocketbase_url: str | None = typer.Option(
        None, "--pocketbase-url", "-u", help="PocketBase API URL (e.g., http://192.168.1.100:8090)"
    ),
) -> None:
    """Initialize configuration for AbletonOS.

    Interactive wizard that:
    - Prompts for project root path (e.g., ~/Music/Ableton)
    - Prompts for PocketBase URL (your hosted instance)

    Use --project-root and --pocketbase-url for non-interactive setup.
    """
    console.print("\n[bold blue]AbletonOS Configuration Wizard[/bold blue]\n")

    # Ensure directory structure exists
    ensure_directories()
    console.print("[green]Created directory structure: ~/.abletonOS/{config,db,logs,templates}/[/green]\n")

    # Check for existing config
    existing = None
    try:
        existing = load_config()
    except FileNotFoundError:
        pass  # No config yet, that's fine

    if existing and project_root is None and pocketbase_url is None:
        console.print(f"[yellow]Existing configuration found at {CONFIG_FILE}[/yellow]")
        console.print(f"  Project root: {existing.project_root}")
        console.print(f"  PocketBase URL: {existing.pocketbase_url}")
        if Confirm.ask("Do you want to reconfigure?"):
            existing = None
        else:
            console.print("[yellow]Keeping existing configuration.[/yellow]\n")
            return

    # Prompt for project root if not provided
    if project_root is None:
        default_root = existing.project_root if existing else None
        if default_root:
            project_root = Prompt.ask(
                "\n[bold]Project Root Path[/bold]\nEnter the root path for your Ableton projects",
                default=default_root,
                console=console,
            )
        else:
            project_root = Prompt.ask(
                "\n[bold]Project Root Path[/bold]\nEnter the root path for your Ableton projects",
                console=console,
            )

    project_root = expand_path(project_root.strip())

    if not project_root:
        console.print("[red]Project root cannot be empty. Aborting.[/red]\n")
        raise typer.Abort()

    # Prompt for PocketBase URL if not provided
    if pocketbase_url is None:
        default_url = existing.pocketbase_url if existing else None
        if default_url:
            pocketbase_url = Prompt.ask(
                "\n[bold]PocketBase URL[/bold]\nEnter your hosted PocketBase URL",
                default=default_url,
                console=console,
            )
        else:
            pocketbase_url = Prompt.ask(
                "\n[bold]PocketBase URL[/bold]\nEnter your hosted PocketBase URL",
                console=console,
            )

    pocketbase_url = pocketbase_url.strip()

    if not pocketbase_url:
        console.print("[red]PocketBase URL cannot be empty. Aborting.[/red]\n")
        raise typer.Abort()

    # Create config object
    config = AbletonOSConfig(
        project_root=project_root,
        pocketbase_url=pocketbase_url,
    )

    # Save config
    save_config(config)
    console.print(f"\n[green]Configuration saved to {CONFIG_FILE}[/green]")
    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"  Project root: [cyan]{project_root}[/cyan]")
    console.print(f"  PocketBase URL: [cyan]{pocketbase_url}[/cyan]\n")
    console.print("[bold green]Configuration complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  • Run [cyan]abletonos new 'Project Name'[/cyan] to create a project")
    console.print("  • Run [cyan]abletonos status[/cyan] to check PB connection")


@app.command()
def new(name: str):
    """Create a new Ableton project folder."""
    pass


@app.command()
def import_project(source: str):
    """Import and standardize an existing Ableton project."""
    pass


@app.command()
def add_samples():
    """Add samples to a project with provenance tracking."""
    pass


@app.command()
def version():
    """Increment .als file version."""
    pass


@app.command()
def export_archive():
    """Export project as a portable ZIP archive."""
    pass


@app.command()
def pb():
    """Check PocketBase connection status.

    Queries the /api/health endpoint of your hosted PocketBase.
    """
    try:
        config = load_config()
    except FileNotFoundError:
        console.print("[red]Not configured. Run 'abletonos init-config' first.[/red]\n")
        raise typer.Exit(1)

    import requests

    # Construct health URL - handle both base URL and full URL cases
    pb_url = config.pocketbase_url.rstrip("/")
    if "/api" in pb_url:
        url = pb_url + "/health"
    else:
        url = pb_url + "/api/health"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            console.print(f"[green]✓[/green] PocketBase is healthy")
            console.print(f"  URL: [cyan]{config.pocketbase_url}[/cyan]")
            if response.json().get("database"):
                console.print(f"  Database: [green]{response.json()['database']}[/green]")
        else:
            console.print(f"[red]✗[/red] PocketBase returned status {response.status_code}")
    except requests.RequestException as e:
        console.print(f"[red]✗[/red] Cannot connect to PocketBase: {e}")
        console.print(f"  URL: [cyan]{config.pocketbase_url}[/cyan]")
        raise typer.Exit(1)


@app.command()
def search():
    """Interactive search across projects."""
    pass


@app.command()
def index():
    """Index or reindex projects in PocketBase."""
    pass


@app.command()
def diagnose():
    """Run diagnostics and collect debugging information."""
    pass


def main():
    """Entry point for the CLI."""
    app()
