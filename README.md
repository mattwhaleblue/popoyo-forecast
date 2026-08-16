# Popoyo forecast

Static surf forecast for Beachies, Astillero, and Chacocente. America/Managua.

## Daily update (7pm)

1. Add `data/days/YYYY-MM-DD.json` (copy an existing day).
2. Run `python3 generate.py` from this folder.
3. Deploy the folder to Vercel (static files, no build).

`generate.py` writes `days.json`, `/index.html` (redirects to today or the latest day), and one `/YYYY-MM-DD/index.html` per day.

## Relatives

Degrees are rounded to the nearest 5 before subtracting the spot facing (Beachies 205°, Astillero 210°, Chacocente 215°).

- Swell 0 = straight. Positive = north of straight, negative = south. Never “on”.
- Wind 0 = onshore, ±180 = offshore. Always labeled “model”.
