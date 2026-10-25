# Sanskrit Depository

A reading site for Sanskrit texts in Devanagari, where every word can be tapped to see its sandhi split, grammar and English meaning. The first text is the **Nyāyasūtra of Gautama with the Nyāyabhāṣya of Vātsyāyana** — all 528 sūtras and the full commentary.

## What is in this repository

| Path | What it is |
|---|---|
| `index.html`, `assets/` | The website (plain HTML, CSS and JavaScript — no build step) |
| `data/` | The text and the word analyses, one file per āhnika, plus the glossary |
| `build/` | The scripts that produced `data/` — only needed to fix analyses or add texts (see `build/README.md`) |
| `.nojekyll` | Tells GitHub Pages to serve the files exactly as they are |

## Publishing on GitHub Pages

1. On GitHub, create a new **public** repository, for example `sanskrit-depository`. Leave “Add a README” unticked.
2. Open the empty repository, choose **uploading an existing file**, and drag in everything from this folder (`index.html`, `.nojekyll`, `README.md`, and the `assets`, `data` and `build` folders). Click **Commit changes**.
   - `.nojekyll` is a hidden file. On a Mac press <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>.</kbd> in Finder to see it; on Windows tick *View → Hidden items*.
3. Go to **Settings → Pages**. Under *Build and deployment*, set **Source** to *Deploy from a branch*, **Branch** to `main` and folder `/ (root)`, then **Save**.
4. After a minute or two the site is live at `https://YOUR-USERNAME.github.io/sanskrit-depository/`. The address also appears at the top of the Pages settings.

Using git instead of the browser:

```bash
cd sanskrit-depository        # this folder
git init -b main
git add .
git commit -m "Nyāyasūtra with Vātsyāyana-bhāṣya"
git remote add origin https://github.com/YOUR-USERNAME/sanskrit-depository.git
git push -u origin main
```

## Previewing on your own computer

Opening `index.html` by double-clicking will not load the text (browsers block data files opened that way). Run a small local server instead:

```bash
python3 -m http.server 8000
```

and visit <http://localhost:8000>.

## Sources and licence

- **Text**: GRETIL e-text of the Nyāyasūtra with Vātsyāyana’s Bhāṣya (input by the Indology Student Team, University of Tokyo), based on the edition of Taranatha Nyaya-Tarkatirtha, Calcutta Sanskrit Series 18 & 19 (1936–1944). Licensed **CC BY-NC-SA 4.0** — this site must therefore stay non-commercial and keep the same licence. About eighty obvious keying errors have been corrected (listed in `build/parse_text.py`).
- **Dictionary**: Monier-Williams, *A Sanskrit-English Dictionary* (1899), digitised by the Cologne Digital Sanskrit Dictionaries (`sanskrit-lexicon/csl-orig`).
- **Morphology**: the Vidyut Sanskrit toolkit by Ambuda.
- **Fonts**: Tiro Devanagari Sanskrit and Schibsted Grotesk (SIL Open Font Licence), loaded from Google Fonts.

The word analysis is automatic and will sometimes be wrong, especially in the commentary; uncertain words have a dotted underline on the site. Corrections are welcome — see `build/README.md`.
