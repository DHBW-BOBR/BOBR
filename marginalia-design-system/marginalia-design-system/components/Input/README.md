# Input

Eingabefeld für bibliografische Angaben und die Suche.

**Markup:** `<div class="mg-field">` mit `<label class="mg-field__label">`, `<input class="mg-input">` und optional `<span class="mg-field__hint">`. Bei einem Befund `aria-invalid="true"` setzen und den Hinweis als `mg-field__hint--error` per `aria-describedby` verknüpfen. Kennungen (DOI, ISBN) mit `mg-input--mono`. Suche: `<label class="mg-search">` mit Icon, Input und optional `<kbd class="mg-kbd">⌘K</kbd>`.

- Labels über dem Feld, nie nur als Platzhalter.
- Der Fehlerhinweis nennt die Referenzquelle und den Vorschlag („Crossref nennt 1989.“), nicht nur „Ungültig“.
- Platzhalter zeigen das Format, nicht ein Beispiel, das wie ein Wert aussieht: „10.xxxx/…“.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
