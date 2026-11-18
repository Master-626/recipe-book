"""Load, save, and query recipes stored in a JSON file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


class RecipeBookError(Exception):
    """A recipe could not be read, validated, or saved."""


@dataclass(frozen=True)
class Recipe:
    """One saved recipe."""

    id: int
    name: str
    cuisine: str
    ingredients: tuple[str, ...]


def default_data_path() -> Path:
    """Return the default recipe file, under the user's home directory."""
    return Path.home() / ".recipe-book" / "recipes.json"


class RecipeBook:
    """Recipes stored in one JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.recipes: list[Recipe] = _load(self.path) if self.path.exists() else []

    def add(
        self,
        name: str,
        cuisine: str = "",
        ingredients: Sequence[str] = (),
    ) -> Recipe:
        """Store a recipe and return it. The name must be new, ignoring case."""
        cleaned_name = _required_line(name, "Recipe name")
        cleaned_cuisine = _optional_line(cuisine, "Cuisine")
        cleaned_ingredients = _clean_ingredients(ingredients)
        if any(recipe.name.casefold() == cleaned_name.casefold() for recipe in self.recipes):
            raise RecipeBookError(f"A recipe named {cleaned_name!r} already exists.")
        recipe = Recipe(
            id=_next_id(self.recipes),
            name=cleaned_name,
            cuisine=cleaned_cuisine,
            ingredients=cleaned_ingredients,
        )
        self.recipes.append(recipe)
        try:
            self.save()
        except RecipeBookError:
            self.recipes.pop()
            raise
        return recipe

    def search(self, keyword: str) -> list[Recipe]:
        """Return recipes whose name, cuisine, or ingredients contain keyword."""
        text = _required_line(keyword, "Search text")
        folded = text.casefold()
        matches = []
        for recipe in self.recipes:
            fields = (recipe.name, recipe.cuisine, *recipe.ingredients)
            if any(folded in field.casefold() for field in fields if field):
                matches.append(recipe)
        return matches

    def shopping_list(self, selectors: Sequence[str] = ()) -> list[tuple[str, tuple[str, ...]]]:
        """Combine ingredients from all recipes, or from names matching selectors.

        Selectors are case-insensitive substrings of the recipe name. The same
        ingredient text, ignoring case, is returned once. Recipe names stay in
        the order the recipes were saved.
        """
        chosen = self._select(selectors)
        labels: dict[str, str] = {}
        names_by_key: dict[str, list[str]] = {}
        for recipe in chosen:
            for ingredient in recipe.ingredients:
                key = ingredient.casefold()
                labels.setdefault(key, ingredient)
                names_by_key.setdefault(key, []).append(recipe.name)
        rows = [(labels[key], tuple(names_by_key[key])) for key in labels]
        rows.sort(key=lambda row: (row[0].casefold(), row[0]))
        return rows

    def save(self) -> None:
        """Write recipes to disk, replacing the file only after the write succeeds."""
        payload = {
            "recipes": [
                {
                    "id": recipe.id,
                    "name": recipe.name,
                    "cuisine": recipe.cuisine,
                    "ingredients": list(recipe.ingredients),
                }
                for recipe in self.recipes
            ]
        }
        temporary = self.path.with_name(self.path.name + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)
        except OSError as exc:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass
            raise RecipeBookError(f"Could not write recipe file {self.path}: {exc}") from exc

    def _select(self, selectors: Sequence[str]) -> list[Recipe]:
        if not selectors:
            return list(self.recipes)
        cleaned = [_required_line(selector, "Recipe selector") for selector in selectors]
        matched = [
            recipe
            for recipe in self.recipes
            if any(selector.casefold() in recipe.name.casefold() for selector in cleaned)
        ]
        if not matched:
            joined = ", ".join(cleaned)
            raise RecipeBookError(f"No recipes matched: {joined}")
        return matched


def _next_id(recipes: Sequence[Recipe]) -> int:
    if not recipes:
        return 1
    return max(recipe.id for recipe in recipes) + 1


def _required_line(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise RecipeBookError(f"{label} must be text.")
    cleaned = _optional_line(value, label)
    if not cleaned:
        raise RecipeBookError(f"{label} must not be blank.")
    return cleaned


def _optional_line(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise RecipeBookError(f"{label} must be text.")
    cleaned = value.strip()
    if "\n" in cleaned or "\r" in cleaned:
        raise RecipeBookError(f"{label} must be a single line.")
    return cleaned


def _clean_ingredients(values: Iterable[str]) -> tuple[str, ...]:
    cleaned = []
    seen = set()
    for value in values:
        item = _required_line(value, "Ingredient")
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return tuple(cleaned)


def _load(path: Path) -> list[Recipe]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise _invalid(path, "not valid UTF-8") from exc
    except OSError as exc:
        raise RecipeBookError(f"Could not read recipe file {path}: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _invalid(path, "invalid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("recipes"), list):
        raise _invalid(path, "expected an object with a recipes list")

    recipes = []
    seen_ids = set()
    seen_names = set()
    for index, item in enumerate(payload["recipes"], start=1):
        recipe = _parse_recipe(item, index, path)
        if recipe.id in seen_ids:
            raise _invalid(path, f"duplicate id {recipe.id}")
        folded = recipe.name.casefold()
        if folded in seen_names:
            raise _invalid(path, f"duplicate name {recipe.name}")
        seen_ids.add(recipe.id)
        seen_names.add(folded)
        recipes.append(recipe)
    return recipes


def _parse_recipe(raw: object, index: int, path: Path) -> Recipe:
    if not isinstance(raw, dict):
        raise _invalid(path, f"recipe {index} must be an object")
    recipe_id = raw.get("id")
    name = raw.get("name")
    if isinstance(recipe_id, bool) or not isinstance(recipe_id, int) or recipe_id < 1:
        raise _invalid(path, f"recipe {index} has an invalid id")
    if not isinstance(name, str):
        raise _invalid(path, f"recipe {index} has an invalid name")
    try:
        cleaned_name = _required_line(name, "Recipe name")
        cuisine = raw.get("cuisine", "")
        if not isinstance(cuisine, str):
            raise RecipeBookError("Cuisine must be text.")
        cleaned_cuisine = _optional_line(cuisine, "Cuisine")
    except RecipeBookError as exc:
        raise _invalid(path, f"recipe {index}: {exc}") from exc
    ingredients = _parse_ingredients(raw.get("ingredients", []), index, path)
    return Recipe(
        id=recipe_id,
        name=cleaned_name,
        cuisine=cleaned_cuisine,
        ingredients=ingredients,
    )


def _parse_ingredients(raw: object, index: int, path: Path) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise _invalid(path, f"recipe {index} has invalid ingredients")
    if any(not isinstance(item, str) for item in raw):
        raise _invalid(path, f"recipe {index} has an invalid ingredient")
    try:
        return _clean_ingredients(raw)
    except RecipeBookError as exc:
        raise _invalid(path, f"recipe {index}: {exc}") from exc


def _invalid(path: Path, reason: str) -> RecipeBookError:
    return RecipeBookError(f"Could not read recipe file {path}: {reason}")
