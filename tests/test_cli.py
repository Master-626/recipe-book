"""Tests for the recipe-book command."""

from pathlib import Path

from click.testing import CliRunner

from recipe_book import __version__
from recipe_book.cli import main


def output_text(result) -> str:
    """Return stdout plus any stderr that is not already included.

    Click 8.1 mixes the streams and refuses to read stderr on its own.
    Click 8.2 and newer keep stderr separate, including error messages.
    """
    stdout = result.output or ""
    try:
        stderr = result.stderr or ""
    except ValueError:
        stderr = ""
    if stderr and stderr not in stdout:
        return stdout + stderr
    return stdout


def test_version_does_not_create_a_recipe_file(isolated_home: Path) -> None:
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in output_text(result)
    assert not (isolated_home / ".recipe-book").exists()


def test_help_lists_commands_and_data_option() -> None:
    result = CliRunner().invoke(main, ["--help"])
    text = output_text(result)
    assert result.exit_code == 0
    for snippet in ("add", "list", "search", "shopping-list", "--data", "RECIPE_BOOK_DATA"):
        assert snippet in text


def test_add_list_and_search_use_saved_recipes(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "recipes.json"
    runner = CliRunner()
    added = runner.invoke(
        main,
        [
            "--data",
            str(path),
            "add",
            "  Tomato Soup  ",
            "--cuisine",
            "American",
            "--ingredient",
            "tomato",
            "--ingredient",
            "stock",
        ],
    )
    assert added.exit_code == 0, output_text(added)
    assert "Added recipe:" in output_text(added)
    assert "Tomato Soup" in output_text(added)

    listed = runner.invoke(main, ["--data", str(path), "list"])
    listed_text = output_text(listed)
    assert listed.exit_code == 0, listed_text
    assert "Tomato Soup" in listed_text
    assert "American" in listed_text
    assert "tomato, stock" in listed_text
    assert "Pasta Carbonara" not in listed_text

    found = runner.invoke(main, ["--data", str(path), "search", "STOCK"])
    assert found.exit_code == 0, output_text(found)
    assert "Tomato Soup" in output_text(found)
    assert "Searching for:" in output_text(found)

    missing = runner.invoke(main, ["--data", str(path), "search", "pizza"])
    assert missing.exit_code == 0
    assert "No recipes matched:" in output_text(missing)
    assert "Tomato Soup" not in output_text(missing)


def test_empty_list_has_no_placeholder_recipe(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["--data", str(tmp_path / "recipes.json"), "list"])
    text = output_text(result)
    assert result.exit_code == 0
    assert "No recipes yet." in text
    assert "Pasta Carbonara" not in text
    assert "Italian" not in text


def test_markup_in_names_and_queries_is_literal(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    runner = CliRunner()
    name = "Soup [/] [red]hot[/red]"
    added = runner.invoke(main, ["--data", str(path), "add", name, "--cuisine", "[/]"])
    assert added.exit_code == 0, output_text(added)
    assert name in output_text(added)
    assert result_has_no_traceback(added)

    listed = runner.invoke(main, ["--data", str(path), "list"])
    assert listed.exit_code == 0, output_text(listed)
    assert name in output_text(listed)
    assert "[/]" in output_text(listed)

    found = runner.invoke(main, ["--data", str(path), "search", "[/]"])
    assert found.exit_code == 0, output_text(found)
    assert "Searching for:" in output_text(found)
    assert "[/]" in output_text(found)
    assert name in output_text(found)


def test_blank_name_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    result = CliRunner().invoke(main, ["--data", str(path), "add", "   "])
    assert result.exit_code != 0
    assert "must not be blank" in output_text(result)
    assert not path.exists()


def test_duplicate_name_is_rejected_without_rewriting_the_file(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    runner = CliRunner()
    first = runner.invoke(main, ["--data", str(path), "add", "Soup"])
    assert first.exit_code == 0, output_text(first)
    before = path.read_text(encoding="utf-8")
    second = runner.invoke(main, ["--data", str(path), "add", "soup"])
    assert second.exit_code != 0
    assert "already exists" in output_text(second)
    assert path.read_text(encoding="utf-8") == before


def test_invalid_json_is_reported_without_a_traceback(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    path.write_text("{", encoding="utf-8")
    result = CliRunner().invoke(main, ["--data", str(path), "list"])
    text = output_text(result)
    assert result.exit_code != 0
    assert "invalid JSON" in text
    assert "Traceback" not in text
    assert path.read_text(encoding="utf-8") == "{"


def test_data_option_overrides_environment_variable(tmp_path: Path) -> None:
    env_path = tmp_path / "env.json"
    flag_path = tmp_path / "flag.json"
    result = CliRunner().invoke(
        main,
        ["--data", str(flag_path), "add", "Soup"],
        env={"RECIPE_BOOK_DATA": str(env_path)},
    )
    assert result.exit_code == 0, output_text(result)
    assert flag_path.is_file()
    assert not env_path.exists()


def test_environment_variable_sets_the_data_file(tmp_path: Path) -> None:
    path = tmp_path / "from-env.json"
    result = CliRunner().invoke(
        main,
        ["add", "Soup"],
        env={"RECIPE_BOOK_DATA": str(path)},
    )
    assert result.exit_code == 0, output_text(result)
    assert "Soup" in path.read_text(encoding="utf-8")


def test_default_path_is_under_home(isolated_home: Path) -> None:
    result = CliRunner().invoke(main, ["add", "Soup"])
    assert result.exit_code == 0, output_text(result)
    saved = isolated_home / ".recipe-book" / "recipes.json"
    assert "Soup" in saved.read_text(encoding="utf-8")


def test_shopping_list_command(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    runner = CliRunner()
    base = ["--data", str(path)]
    assert runner.invoke(main, [*base, "shopping-list"]).exit_code == 0
    assert "No recipes yet." in output_text(runner.invoke(main, [*base, "shopping-list"]))

    for args in (
        ["add", "Tomato Egg", "--ingredient", "tomato", "--ingredient", "egg"],
        ["add", "Omelette", "--ingredient", "Egg", "--ingredient", "milk"],
        ["add", "Rice"],
    ):
        added = runner.invoke(main, [*base, *args])
        assert added.exit_code == 0, output_text(added)

    combined = runner.invoke(main, [*base, "shopping-list"])
    combined_text = output_text(combined)
    assert combined.exit_code == 0, combined_text
    assert "egg" in combined_text
    assert "Tomato Egg, Omelette" in combined_text
    assert "milk" in combined_text

    filtered = runner.invoke(main, [*base, "shopping-list", "Omelette"])
    filtered_text = output_text(filtered)
    assert filtered.exit_code == 0, filtered_text
    assert "milk" in filtered_text
    assert "tomato" not in filtered_text

    empty = runner.invoke(main, [*base, "shopping-list", "Rice"])
    assert empty.exit_code == 0
    assert "No ingredients recorded." in output_text(empty)

    missing = runner.invoke(main, [*base, "shopping-list", "nope"])
    assert missing.exit_code != 0
    assert "No recipes matched: nope" in output_text(missing)


def result_has_no_traceback(result) -> bool:
    return "Traceback" not in output_text(result)
