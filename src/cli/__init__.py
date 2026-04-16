"""CLI entrypoint for recall-kg.

Stub commands — implemented in Phase 29.
"""
import typer

app = typer.Typer(
    name="recall",
    help="Engineering knowledge graph — extracts decisions, patterns, and bugs from git history.",
    no_args_is_help=True,
)


@app.command()
def init():
    """Rebuild knowledge graph from scratch."""
    typer.echo("Not implemented yet — Phase 28")


@app.command()
def sync():
    """Index new commits since last sync."""
    typer.echo("Not implemented yet — Phase 28")


@app.command()
def search(query: str = typer.Argument(..., help="Search query")):
    """Search the knowledge graph."""
    typer.echo("Not implemented yet — Phase 29")


@app.command()
def health():
    """Check LLM provider and database status."""
    typer.echo("Not implemented yet — Phase 29")


@app.command()
def config():
    """Show or edit configuration."""
    typer.echo("Not implemented yet — Phase 29")


@app.command()
def ui():
    """Launch the graph explorer UI."""
    typer.echo("Not implemented yet — Phase 31")


def cli_entry():
    """Console script entrypoint."""
    app()
