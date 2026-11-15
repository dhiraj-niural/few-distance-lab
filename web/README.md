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

The three targets come directly from the saved certificates named in `math.mjs`. Only the 8-point, 4×4 target is labelled a proven board optimum. The 10- and 20-point targets are verified constructions with unknown board minima. Browser exports use the existing certificate v1 schema, and can be checked with `python3 -m few_distance verify witness.json`.

Grid positions show physical coordinates `(x, √2 y)` while point labels and exports use integer indices `(x, y)`. Displayed distance chips are squared lengths. Arrow keys navigate the grid; Enter or Space toggles a point. A distance chip supports pointer hover, keyboard focus and tap-to-pin. Changes, construction reveal and reset can be undone. URL fragments encode the current challenge and points; malformed or out-of-range input is rejected.

The interface works without external fonts or assets. Browser QA should cover a narrow mobile viewport and desktop, selection/removal, keyboard navigation, highlighted pairs, challenge switching, reveal/undo/reset, malformed state, share-link reload and exported certificate verification.
