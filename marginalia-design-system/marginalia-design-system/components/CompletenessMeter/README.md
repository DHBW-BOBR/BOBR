# CompletenessMeter

Fasst den Zustand eines Literaturverzeichnisses als segmentierten Balken zusammen.

**Markup:** `<div class="mg-meter">` mit Kopf (`mg-meter__head`, Label und `mg-meter__value`), dem Balken `mg-meter__bar` aus `mg-meter__seg--verified|notice|missing|error` (Breite über `flex: <Anzahl>`) und der Legende `mg-meter__legend` mit `mg-meter__key--…`. Der Konsument liefert die Anzahlen je Status; jede Quelle zählt einmal, mit ihrem schwersten Befund.

- Der Wert ist eine Anzahl („4 von 9“), keine Prozentzahl mit Nachkommastellen und keine Schulnote.
- Reihenfolge der Segmente fest: Geprüft, Hinweis, Fehlt, Fehler.
- Der Balken braucht `role="img"` und ein `aria-label`, das die Zahlen ausschreibt; die Legende bleibt sichtbar.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
