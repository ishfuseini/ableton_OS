"""CLI module for AbletonOS."""

import typer

from abletonos.logging_config import setup_logging

app = typer.Typer(
    name="abletonos",
    help="Ableton project organizer and sample library manager for macOS.",
)


@app.callback()
def callback(debug: bool = typer.Option(False, "--debug", help="Enable debug logging")):
    """AbletonOS - Keep your Ableton projects portable and sample library searchable."""
    setup_logging(debug=debug)


@app.command()
def init_config():
    """Initialize configuration and set up PocketBase."""
    pass


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
def pb(action: str = typer.Argument(..., help="start | stop | status")):
    """Manage PocketBase instance."""
    pass


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
