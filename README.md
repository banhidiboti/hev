# H5 FIGYELŐ

Valós idejű HÉV H5 járatkövetés a BKK Futár API alapján. Tisztán frontend, backend nélkül — GitHub Pages-en fut.

## Funkciók

- Valós idejű vonatpozíciók a térképen (10 másodpercenként frissül)
- Iránymutató nyíl minden vonaton
- Klímás HÉV kocsi arany színnel jelölve
- Kattintásra megjelenő alsó lap: célállomás, kocsi számok, következő megálló menetrendidővel
- Teljes menetrend — már elhagyott megállók halvány szürkével, jövőbeli megállók zölddel kiemelve
- Sötét/világos téma váltó
- Mobilbarát, húzható alsó lap

## API kulcs

A BKK Futár API kulcs a `index.html`-be van égetein. Saját kulcs az [opendata.bkk.hu/keys](https://opendata.bkk.hu/keys) oldalon igényelhető ingyenesen.

## Technológiák

- [Leaflet.js](https://leafletjs.com/) — térkép
- [BKK Futár API](https://opendata.bkk.hu/) — valós idejű menetrend és pozíció
- [CartoDB Dark Matter](https://carto.com/basemaps/) — térkép csempék
