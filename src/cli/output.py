"""CLI output helpers — Rich console and print utilities."""
from rich.console import Console

# Primary console (stdout)
console = Console()

# Error console (stderr)
err_console = Console(stderr=True)


def print_success(message: str) -> None:
    """Print a success message in green."""
    console.print(f"[green]{message}[/green]")


def print_error(message: str, suggestion: str | None = None) -> None:
    """Print an error message in red, optionally with a suggestion."""
    err_console.print(f"[red]Error:[/red] {message}")
    if suggestion:
        err_console.print(f"[dim]Hint: {suggestion}[/dim]")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    console.print(f"[yellow]Warning:[/yellow] {message}")
