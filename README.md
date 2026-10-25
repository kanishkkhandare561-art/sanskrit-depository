# Rebuilding the word analysis

You only need this folder if you want to correct an analysis, improve a meaning, or add a new text. The website itself (in the folder above) is already built and runs without any of this.

## One-time setup

```bash
cd build
pip install -r requirements.txt
python3 -c "import vidyut; vidyut.download_data('vdata')"          # Sanskrit morphology data (~80 MB)
curl -L -o mw.txt https://raw.githubusercontent.com/sanskrit-lexicon/csl-orig/master/v02/mw/mw.txt   # Monier-Williams (~50 MB)
python3 mw_index.py mw.txt mw_index.json
```

`vdata/`, `mw.txt` and `mw_index.json` are large; keep them out of the repository (they are listed in `.gitignore`).

## Build

```bash
python3 parse_text.py source/nyayasutra-bhashya-gretil.txt parsed.json
python3 build_data.py          # writes ../data/*.json
```

## Fixing things

- **A meaning is wrong or too dictionary-like** — add or edit the word in `curated.json` (key in IAST, dictionary form):
  `"vyāpti": {"m": "invariable concomitance", "n": "Not used by Gautama himself; central in later Nyāya."}`
- **A word is split wrongly** — add it to `overrides.json`, keyed by the exact form in the text (IAST). Each part is `[form, dictionary form, grammar]`:
  ```json
  "saṃyogāvyucchedaḥ": {"p": [["saṃyoga", "saṃyoga", "compound member (stem)"],
                              ["avyucchedaḥ", "avyuccheda", "nom. sg. m."]]}
  ```
  Overridden words are marked as verified on the site.
- **A typo in the source text** — add it to the `TYPO` table at the top of `parse_text.py`.

Then run the two build commands again and commit the changed files in `data/`.
