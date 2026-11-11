# Recipe Book

## 摘要

Recipe Book 是一个保存在本机的命令行菜谱本。每道菜记录名称、菜系和食材，默认写入 `~/.recipe-book/recipes.json`（也可用 `--data` 或环境变量 `RECIPE_BOOK_DATA` 指定文件）。`list` 查看全部菜谱，`search` 按名称、菜系或食材查找，`shopping-list` 把选定菜谱的食材合并成一份购物清单。下面是英文说明。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/Master-626/recipe-book/actions/workflows/ci.yml/badge.svg)](https://github.com/Master-626/recipe-book/actions/workflows/ci.yml)

A local command-line recipe book. Save a name, cuisine, and ingredients for each recipe, then list them, search them, and build a shopping list.

## Installation

Python 3.8 or newer is required.

```bash
git clone https://github.com/Master-626/recipe-book.git
cd recipe-book
python -m pip install .
```

This installs the `recipe-book` command. To work on the project, install the development tools as well:

```bash
python -m pip install -e ".[dev]"
```

## Usage

```bash
recipe-book add "Pasta Carbonara" \
  --cuisine Italian \
  --ingredient spaghetti \
  --ingredient egg \
  --ingredient pecorino

recipe-book list
recipe-book search egg
recipe-book shopping-list
recipe-book shopping-list Carbonara
```

`list` prints every saved recipe. `search` prints recipes whose name, cuisine, or ingredients contain the keyword. `shopping-list` prints ingredients. With one or more extra words, it only includes recipes whose names contain one of those words.

Matching ignores case. `egg` and `Egg` are the same ingredient and the same search. A recipe name can be saved once; a second `add` with the same name, ignoring case, is rejected. Blank names and ingredients are rejected. Leading and trailing whitespace is removed.

Text you enter is shown as entered. Characters such as `[` and `]` are recipe text, not terminal formatting.

## Options

Global options come before the command:

| Option | Description |
| --- | --- |
| `--data PATH` | JSON file used to store recipes. Overrides `RECIPE_BOOK_DATA`. |
| `--version` | Print the version and exit. |
| `--help` | Print help and exit. |

The default file is `~/.recipe-book/recipes.json`. The directory is created when the first recipe is saved.

| Command | Arguments and options |
| --- | --- |
| `add NAME` | `--cuisine TEXT` sets the cuisine. Repeat `--ingredient TEXT` for each ingredient. |
| `list` | List saved recipes. |
| `search KEYWORD` | Case-insensitive substring of the name, cuisine, or any ingredient. |
| `shopping-list [SELECTOR ...]` | Ingredients for every recipe, or for names containing a selector. |

`shopping-list` with a selector that matches nothing exits with an error. A recipe that matches but has no ingredients prints `No ingredients recorded.`

Saved file:

```json
{
  "recipes": [
    {
      "id": 1,
      "name": "Pasta Carbonara",
      "cuisine": "Italian",
      "ingredients": ["spaghetti", "egg", "pecorino"]
    }
  ]
}
```

Ids are assigned automatically. You can edit the file, then use it again, as long as it stays valid UTF-8 JSON in this shape.

## Running tests

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

GitHub Actions runs those commands on Python 3.8, 3.9, 3.10, 3.11, 3.12, and 3.13.

## License

MIT License. See [LICENSE](LICENSE).
