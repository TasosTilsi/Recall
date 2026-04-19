"""Health command — check LLM provider and database connectivity."""
import asyncio

import typer

from src.cli.output import console, print_error


def health_command() -> None:
    """Check LLM provider and database status.

    Verifies connectivity to the configured LLM provider and embeddings
    service. Completes within 5 seconds.

    Examples:
        recall health
    """
    try:
        from src.config import load_config
        from src.llm.health import check_health

        config = load_config()

        with console.status("Checking health..."):
            result = asyncio.run(check_health(config))

        # Provider line
        llm_status = result.status
        console.print(
            f"Provider  : {result.provider}  model={result.model}  [{llm_status}]"
        )

        # Embeddings line
        emb_status = result.embeddings_status
        if emb_status == "not configured":
            console.print("Embeddings: not configured")
        else:
            console.print(f"Embeddings: [{emb_status}]")

        # Error detail (if any)
        if result.error:
            console.print(f"[dim]Error detail: {result.error}[/dim]")
        if result.embeddings_error:
            console.print(f"[dim]Embeddings error: {result.embeddings_error}[/dim]")

        # Exit code: 0 if LLM reachable, 1 if not
        if result.status != "OK":
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Health check failed: {str(e)}")
        raise typer.Exit(code=1)
