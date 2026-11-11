"""Command-line interface for Recipe Book."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn, Sequence

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from recipe_book import __version__
from recipe_book.book import Recipe, RecipeBook, RecipeBookError, default_data_path

console = Console()


def _plain(text: str) -> Text:
    """Return text Rich will print literally, not as markup."""
    return Text(text)


def _fail(exc: RecipeBookError) -> NoReturn:
    raise click.ClickException(str(exc)) from exc


def _open_book(ctx: click.Context) -> RecipeBook:
    try:
        return RecipeBook(ctx.obj["data_path"])
    except RecipeBookError as exc:
        _fail(exc)


def _print_recipes(title: str, recipes: Sequence[Recipe]) -> None:
    table = Table(title=_plain(title))
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Cuisine")
    table.add_column("Ingredients")
    for recipe in recipes:
        ingredients = ", ".join(recipe.ingredients) if recipe.ingredients else "—"
        table.add_row(
            str(recipe.id),
            _plain(recipe.name),
            _plain(recipe.cuisine or "—"),
            _plain(ingredients),
        )
    console.print(table)


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--data",
    "data_path",
    type=click.Path(dir_okay=False),
    envvar="RECIPE_BOOK_DATA",
    show_envvar=True,
    help="Recipe JSON file. Defaults to ~/.recipe-book/recipes.json.",
)
@click.pass_context
def main(ctx: click.Context, data_path: str | None) -> None:
    """Save recipes, search them, and build a shopping list."""
    ctx.ensure_object(dict)
    ctx.obj["data_path"] = Path(data_path) if data_path else default_data_path()


@main.command()
@click.argument("name")
@click.option("--cuisine", default="", help="Cuisine, such as Italian or Sichuan.")
@click.option(
    "--ingredient",
    "ingredients",
    multiple=True,
    help="One ingredient. Repeat the option for each ingredient.",
)
@click.pass_context
def add(
    ctx: click.Context,
    name: str,
    cuisine: str,
    ingredients: tuple[str, ...],
) -> None:
    """Add a recipe."""
    book = _open_book(ctx)
    try:
        recipe = book.add(name, cuisine, ingredients)
    except RecipeBookError as exc:
        _fail(exc)
    console.print(Text.assemble("✅ Added recipe: ", (recipe.name, "bold green")))


@main.command("list")
@click.pass_context
def list_recipes(ctx: click.Context) -> None:
    """List saved recipes."""
    book = _open_book(ctx)
    if not book.recipes:
        console.print("No recipes yet.")
        return
    _print_recipes("Recipes", book.recipes)


@main.command()
@click.argument("keyword")
@click.pass_context
def search(ctx: click.Context, keyword: str) -> None:
    """Search recipes by name, cuisine, or ingredient."""
    book = _open_book(ctx)
    try:
        matches = book.search(keyword)
    except RecipeBookError as exc:
        _fail(exc)
    shown = keyword.strip()
    console.print(Text.assemble("🔍 Searching for: ", (shown, "bold")))
    if not matches:
        console.print(Text.assemble("No recipes matched: ", (shown, "bold")))
        return
    _print_recipes("Recipes", matches)


@main.command("shopping-list")
@click.argument("selectors", nargs=-1)
@click.pass_context
def shopping_list(ctx: click.Context, selectors: tuple[str, ...]) -> None:
    """List ingredients for every recipe, or for names matching SELECTORS."""
    book = _open_book(ctx)
    try:
        rows = book.shopping_list(selectors)
    except RecipeBookError as exc:
        _fail(exc)
    if not selectors and not book.recipes:
        console.print("No recipes yet.")
        return
    if not rows:
        console.print("No ingredients recorded.")
        return
    table = Table(title="Shopping List")
    table.add_column("Ingredient", style="green")
    table.add_column("Recipes")
    for ingredient, names in rows:
        table.add_row(_plain(ingredient), _plain(", ".join(names)))
    console.print(table)


if __name__ == "__main__":
    main()
