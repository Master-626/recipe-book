"""CLI interface."""
import click
from rich.console import Console
from rich.table import Table

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def main():
    """Recipe Book - Manage your recipes and meal plans."""
    pass

@main.command()
@click.argument("name")
def add(name):
    """Add a new recipe."""
    console.print(f"✅ Added recipe: [bold green]{name}[/bold green]")

@main.command()
def list():
    """List all recipes."""
    table = Table(title="Recipes")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Cuisine")
    table.add_row("1", "Pasta Carbonara", "Italian")
    console.print(table)

@main.command()
@click.argument("keyword")
def search(keyword):
    """Search recipes."""
    console.print(f"🔍 Searching for: {keyword}")

if __name__ == "__main__":
    main()
