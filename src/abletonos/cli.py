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
    library_root: str | None = typer.Option(
        None,
        "--library-root",
        "-l",
        help="Sample library root path (e.g., ~/Music/Samples)",
    ),
    pocketbase_url: str | None = typer.Option(
        None, "--pocketbase-url", "-u", help="PocketBase API URL (e.g., http://192.168.1.100:8090)"
    ),
) -> None:
    """Initialize configuration for AbletonOS.

    Interactive wizard that prompts for:
    - Project root path (where Ableton projects live)
    - Sample library root (where organized samples are stored)
    - PocketBase URL (your hosted instance)
    """
    console.print("\n[bold blue]AbletonOS Configuration Wizard[/bold blue]\n")

    ensure_directories()
    console.print("[green]Created directory structure: ~/.abletonOS/{config,db,logs,templates}/[/green]\n")

    existing = None
    try:
        existing = load_config()
    except FileNotFoundError:
        pass

    if existing and project_root is None and library_root is None and pocketbase_url is None:
        console.print(f"[yellow]Existing configuration found at {CONFIG_FILE}[/yellow]")
        console.print(f"  Project root:   {existing.project_root}")
        console.print(f"  Library root:   {existing.library_root or '(not set)'}")
        console.print(f"  PocketBase URL: {existing.pocketbase_url or '(not set)'}")
        if not Confirm.ask("Do you want to reconfigure?"):
            console.print("[yellow]Keeping existing configuration.[/yellow]\n")
            return
        existing = None

    # Prompt for project root
    if project_root is None:
        default = existing.project_root if existing else None
        project_root = Prompt.ask(
            "\n[bold]Project Root Path[/bold]\nWhere do your Ableton projects live?",
            default=default,
            console=console,
        )
    project_root = expand_path(project_root.strip())
    if not project_root:
        console.print("[red]Project root cannot be empty. Aborting.[/red]\n")
        raise typer.Abort()

    # Prompt for library root
    if library_root is None:
        default = existing.library_root if existing else None
        library_root = Prompt.ask(
            "\n[bold]Sample Library Root[/bold]\nWhere should organized samples be stored?",
            default=default,
            console=console,
        )
    library_root = expand_path(library_root.strip()) if library_root else None
    if not library_root:
        console.print("[red]Library root cannot be empty. Aborting.[/red]\n")
        raise typer.Abort()

    # Prompt for PocketBase URL
    if pocketbase_url is None:
        default = existing.pocketbase_url if existing else None
        pocketbase_url = Prompt.ask(
            "\n[bold]PocketBase URL[/bold]\nEnter your hosted PocketBase URL",
            default=default,
            console=console,
        )
    pocketbase_url = pocketbase_url.strip() if pocketbase_url else None

    config = AbletonOSConfig(
        project_root=project_root,
        library_root=library_root,
        pocketbase_url=pocketbase_url,
    )
    save_config(config)

    console.print(f"\n[green]Configuration saved to {CONFIG_FILE}[/green]")
    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"  Project root:   [cyan]{project_root}[/cyan]")
    console.print(f"  Library root:   [cyan]{library_root}[/cyan]")
    console.print(f"  PocketBase URL: [cyan]{pocketbase_url or '(not set)'}[/cyan]\n")
    console.print("[bold green]Configuration complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  • Run [cyan]abletonos add-samples <folder>[/cyan] to import a sample pack")


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
