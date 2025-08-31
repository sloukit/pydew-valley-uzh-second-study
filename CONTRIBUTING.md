# Contributing

Before contributing a [new idea/feature](#feature-requests) or signaling a bug, please check [the known issues and refused ideas](know_issues_or_refused_ideas/known_issues_or_refused_ideas.md).

## Feature Requests

If you want to suggest a new feature, please open an issue first to discuss the idea.


## Contributing Code

For the initial creation phase of the game, tasks for main features will be assigned using the [Tasklist](https://github.com/users/sloukit/projects/1) in GitHub.

For code contributions outside of the tasklist, please open an issue first to discuss the idea.

Please note that Python 3.12 is required to run and develop the project.

It is strongly recommended to comment your code or, when adding functions, to use docstrings in order to explain steps, arguments, expected results and overall your implementation.


### Linting and Formatting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. Run `pip install -r requirements-dev.txt` to install it and other relevant dependencies.


<--! The bold text above can be put into a GitHub markdown info callout like this: -->

> [!IMPORTANT]
> **Before opening a PR, please run the following command to ensure that your code is formatted and doesn't upset the Ruff linter:**
>
> ```bash
> python formatlint.py
> ```
>
> Or, alternatively, run the following commands individually:
>
> On Linux/MacOS:
> ```bash
> ruff format . && ruff check --select I --fix . # format code and sort imports
> ruff check . # Run linting and perform fixes accordingly, or use '# noqa: <RULE>' followed by a comment justifying why the rule is ignored
> ```
> 
> On Windows:
> ```powershell
> ruff format . # format code
> ruff check --select I --fix . # Sort Imports
> ruff check .  # Run linting and perform fixes accordingly, or use '# noqa: <RULE>' followed by a comment justifying why the rule is ignored
> ```

## Translations

The game supports, for now, English 🇬🇧 (abbreviated to `en` ) and German 🇩🇪 (abbreviated to `de` )

Now, all strings that are displayed need to be kept in 2 files:

- `data/translations/en.txt`
- `data/translations/de.txt`

Also, dialogues and tutorial json files have 2 versions:

- `data/textboxes/en/tutorial.json`
- `data/textboxes/de/tutorial.json`

- `data/textboxes/en/dialogues.json`
- `data/textboxes/de/dialogues.json`

They need to be kept in sync - every change in one language must be reflected in another. You don't need to provide the actual German translations - someone else will do it, just add your new/changed string in the German file version, prefixed with `EN: `.

### How to use it:

Instead of writing something like this:

`print("This is hardcoded messages")`

do this:

`print(_("This is hardcoded messages"))`

If this hardcoded string is in a python file that has not used translations so far, add this import:
`from src.support import get_translated_string as _`

You can read more about this functionality in the [extract_translations.sh](extract_translations.sh) script.

To run the game in a given language, set the environment variable `GAME_LANGUAGE` to either `en` or `de`. See [run_game.sh](run_game.sh) for example in Linux/MacOS. On Windows, the command is `set GAME_LANGUAGE=en`. English is used as default.

If there is a text starting `N/A: ` visible in the game, it means the string is missing in `data/translations/en.txt` or `data/translations/de.txt` file - this needs to be fixed.

If the text starts with `EN: ` it means it's not translated yet - nothing to worry.

## Adding new Assets

### Characters
All the imports happen in the `Game.load_assets()` method in [main.py](./main.py) and the `Game.character_importer()` method imports the content of [images/characters/](images/characters/). The name of the subfolder will be a key in the dictionary
and the files within that subfolder should be tileset images with each tile being 48x48. Each of these images will be stored in a sub dictionary attached to the subfolder key; the first row
should be the up animation, the second one the down animation and the third row the left animation; animations for the right side will be a flipped copy of the left side.
If you want to add more character animations, just check out the rabbit folder in characters to understand how it works.

In sprites.py, there is a Player class that currently controls the rabbit in the game. You could inherit from that and overwrite methods, or use the Entity class as a parent and add more to it.
(The Player class currently has too many methods; quite a few of those could be stored in Entity to make the whole setup more flexible)

### Tileset
All maps were created using [Tiled](https://mapeditor.org). The layers are fairly self-explanatory.
Add more things as needed, be it new tiles, objects or even completely new maps. The
[project tasklist](https://github.com/users/sloukit/projects/1) shows what, and with what priority, is still needed.

The [images](images) folder contains a few more graphics that could be used to decorate the maps.

#### Object Collisions
If you would like to add custom collisions to a new object that you have created, feel free to add them in Tiled's tile collision editor.
To do this, simply open the corresponding tileset and click on the tile you want to edit. In the window on the right, you can then insert a rectangle that will then be used as hitbox for the object.

(If you don't see the Tile Collision Editor, open it under `View -> Views and Toolbars -> Tile Collision Editor` while in the tileset overview)

## Extracting Data
In the [Level](./src/screens/level.py) class, there is an `apply_tool()` method that lets an entity interact with the world (i.e. use a tool or plant a seed); if you want to measure what's going on in the game, this should be a good starting point.
