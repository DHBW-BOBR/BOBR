# SegmentedControl

Filtert eine Liste nach Status; genau ein Segment ist aktiv.

**Markup:** `<div class="mg-seg" role="group" aria-label="…">` mit `<button class="mg-seg__item" aria-pressed="true|false">Fehler <span class="mg-seg__count">1</span></button>`. Der Konsument liefert die Segmente, die Zähler und setzt `aria-pressed` beim Wechsel.

- Zwei bis fünf Segmente, Label ein Wort. Reihenfolge: Alle, dann nach Schwere (Fehler, Fehlt, Hinweise), Geprüft zuletzt.
- Zähler zählen Quellen, nicht Befunde — sie müssen zur Summe in „Alle“ passen.
- Für Navigation zwischen Ansichten nicht verwenden; dafür ist die Seitenleiste da.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
