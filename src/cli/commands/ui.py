"""UI command — launch the graph explorer UI server."""
import typer

from src.cli.output import console, print_error
from src.cli.utils import EXIT_ERROR


def ui_command(
    host: str = typer.Option("127.0.0.1", help="Host to bind the UI server"),
    port: int = typer.Option(8765, help="Port to listen on"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open browser automatically"),
) -> None:
    """Launch the graph explorer UI.

    Starts the FastAPI UI server and opens the browser to the graph explorer.

    Examples:
        recall ui
        recall ui --port 9000
        recall ui --no-browser
    """
    try:
        import uvicorn
        from pathlib import Path
        from src.ui_server.app import create_app

        app = create_app()

        url = f"http://{host}:{port}"
        console.print(f"Starting Recall UI at [link={url}]{url}[/link]")

        if not no_browser:
            import webbrowser
            webbrowser.open(url)

        uvicorn.run(app, host=host, port=port, log_level="warning")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to start UI server: {str(e)}")
        raise typer.Exit(EXIT_ERROR)
