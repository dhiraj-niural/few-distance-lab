# Interactive playground

Buildless, browser-local geometry challenges. Serve this directory with any static HTTP server:

```sh
python3 -m http.server 8765 --directory web
```

Open `http://localhost:8765`. No package installation, backend, analytics, cookies or model calls are required.

Run the JavaScript scoring, validation and saved-certificate checks from the repository root:

```sh
node --test web/math.test.mjs
```

Each of the four boards has a target that is the proven minimum for that board and point count; free play shows the proven minimum for whatever number of points is placed. The table of minima in `math.mjs` is tested against `results/2026-11-16-exact/minima.json`, and the search figures shown beside each board against `baselines.json` in the same directory. Browser exports use the certificate v1 schema and can be checked with `python3 -m few_distance verify witness.json`.

Grid positions show physical coordinates `(x, √2 y)`; labels and exports use integer indices `(x, y)`. Distance bars are squared lengths, taller when more pairs share them. With move costs on, each empty site shows how many new distances a point there would add. Arrow keys navigate the grid; Enter or Space toggles a point. URL fragments encode the board and points; malformed or out-of-range input is rejected. A complete board opened from a link, a revealed optimal board and an untouched bot board do not count as the visitor's solve. Solved boards and the cost toggle are kept in `localStorage` when available.

“Post result” shares the score and a bar picture of the distance counts, with a link that opens the board empty.

The interface works without external fonts or assets. Browser QA should cover a narrow mobile viewport and desktop, selection/removal, keyboard navigation, highlighted pairs, board switching, free play, the local-search run, the stretch demo, reveal/undo/reset, malformed state, share-link reload and exported certificate verification.

The optional link-preview renderer is `tools/render_social_card.py` and uses Pillow. The game itself has no dependencies.
