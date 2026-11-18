"""Tests for recipe storage and shopping lists."""

import json
from pathlib import Path

import pytest

from recipe_book.book import RecipeBook, RecipeBookError, default_data_path


def test_default_data_path(isolated_home: Path) -> None:
    assert default_data_path() == isolated_home / ".recipe-book" / "recipes.json"


def test_add_persists_trims_and_reloads(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    book = RecipeBook(path)
    saved = book.add("  番茄炒蛋  ", "  Chinese  ", ("  tomato  ", "egg", "Egg"))
    assert saved.id == 1
    assert saved.name == "番茄炒蛋"
    assert saved.cuisine == "Chinese"
    assert saved.ingredients == ("tomato", "egg")

    raw = path.read_text(encoding="utf-8")
    assert "番茄炒蛋" in raw
    assert json.loads(raw)["recipes"][0]["ingredients"] == ["tomato", "egg"]

    reloaded = RecipeBook(path)
    assert reloaded.recipes == book.recipes
    assert reloaded.add("Soup").id == 2


def test_ids_continue_after_the_highest_saved_id(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    path.write_text(
        json.dumps({"recipes": [{"id": 5, "name": "Soup"}]}),
        encoding="utf-8",
    )
    assert RecipeBook(path).add("Bread").id == 6


def test_missing_optional_fields_default_to_empty(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    path.write_text(
        json.dumps({"recipes": [{"id": 1, "name": "  Soup  "}]}),
        encoding="utf-8",
    )
    recipe = RecipeBook(path).recipes[0]
    assert recipe.name == "Soup"
    assert recipe.cuisine == ""
    assert recipe.ingredients == ()


def test_blank_duplicate_and_multiline_names_are_rejected(tmp_path: Path) -> None:
    book = RecipeBook(tmp_path / "recipes.json")
    book.add("Soup")
    with pytest.raises(RecipeBookError, match="must not be blank"):
        book.add("   ")
    with pytest.raises(RecipeBookError, match="already exists"):
        book.add("soup")
    with pytest.raises(RecipeBookError, match="single line"):
        book.add("So\nup")
    with pytest.raises(RecipeBookError, match="must not be blank"):
        book.add("Stew", ingredients=[" "])
    assert [recipe.name for recipe in RecipeBook(book.path).recipes] == ["Soup"]


def test_search_matches_name_cuisine_and_ingredient_ignoring_case(tmp_path: Path) -> None:
    book = RecipeBook(tmp_path / "recipes.json")
    book.add("Tomato Egg", "Chinese", ["tomato", "egg"])
    book.add("Rice", "", [])
    assert [recipe.name for recipe in book.search("EGG")] == ["Tomato Egg"]
    assert [recipe.name for recipe in book.search("chinese")] == ["Tomato Egg"]
    assert book.search("pizza") == []
    with pytest.raises(RecipeBookError, match="must not be blank"):
        book.search("  \t  ")


def test_shopping_list_merges_ingredients_and_filters_by_name(tmp_path: Path) -> None:
    book = RecipeBook(tmp_path / "recipes.json")
    book.add("Tomato Egg", "Chinese", ["tomato", "egg"])
    book.add("Omelette", "French", ["Egg", "milk"])
    book.add("Rice")
    assert book.shopping_list() == [
        ("egg", ("Tomato Egg", "Omelette")),
        ("milk", ("Omelette",)),
        ("tomato", ("Tomato Egg",)),
    ]
    assert book.shopping_list(["ome"]) == [
        ("Egg", ("Omelette",)),
        ("milk", ("Omelette",)),
    ]
    assert book.shopping_list(["rice"]) == []
    with pytest.raises(RecipeBookError, match="No recipes matched: nope"):
        book.shopping_list(["nope"])
    with pytest.raises(RecipeBookError, match="must not be blank"):
        book.shopping_list([" "])


def test_failed_save_does_not_keep_the_recipe(tmp_path: Path) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("x", encoding="utf-8")
    book = RecipeBook(blocker / "recipes.json")
    with pytest.raises(RecipeBookError, match="Could not write"):
        book.add("Soup")
    assert book.recipes == []


def test_corrupt_files_raise_and_are_left_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    path.write_bytes(b"\xff")
    with pytest.raises(RecipeBookError, match="not valid UTF-8"):
        RecipeBook(path)

    path.write_text("{", encoding="utf-8")
    with pytest.raises(RecipeBookError, match="invalid JSON"):
        RecipeBook(path)
    assert path.read_text(encoding="utf-8") == "{"

    path.write_text(json.dumps({"recipes": {"name": "Soup"}}), encoding="utf-8")
    with pytest.raises(RecipeBookError, match="recipes list"):
        RecipeBook(path)

    path.write_text(
        json.dumps({"recipes": [{"id": 1, "name": "Soup", "ingredients": [1]}]}),
        encoding="utf-8",
    )
    with pytest.raises(RecipeBookError, match="invalid ingredient"):
        RecipeBook(path)

    path.write_text(
        json.dumps(
            {
                "recipes": [
                    {"id": 1, "name": "Soup"},
                    {"id": 1, "name": "Stew"},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RecipeBookError, match="duplicate id 1"):
        RecipeBook(path)
