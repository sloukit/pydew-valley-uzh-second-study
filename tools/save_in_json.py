# Use this tool to transfer info from the old format into JSON files.
# TODO: remove the old text files once all entries are translated.
import json
import os.path


def load_translations_old(lang: str) -> dict[str, str]:  # noqa
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "translations",
        f"{lang}.txt",
    )
    with open(path, "r", encoding="utf-8") as file:
        text = file.read()

    lines = text.splitlines()
    pairs = [
        tuple(line.split("@@"))
        for line in lines
        # read only not empty lines, skip lines starting with # and without "@@" (comments)
        if line and (line[0] != "#" or "@@" in line)
    ]
    return dict(pairs)


lang_dicts = {}
key_sets = {}

for lang in ("en", "de"):
    lang_dicts[lang] = load_translations_old(lang)
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "translations",
        f"{lang}.json",
    )
    with open(path, "w", encoding="utf-8") as file:
        json.dump(lang_dicts[lang], file, indent=4)  # noqa

    key_sets[lang] = set(lang_dicts[lang].keys())

print(
    f"Entries in English left untranslated in German: {key_sets['en'].difference(key_sets['de'])}"
)
print(
    f"Entries in German left untranslated in English: {key_sets['de'].difference(key_sets['en'])}"
)
