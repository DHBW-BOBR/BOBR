# CitationNotes

Das Rohzitat mit markierten Stellen und den Befunden als Randnotizen daneben — das namensgebende Muster.

**Markup:** `<div class="mg-cite">` mit `<p class="mg-cite__text">` (das Zitat, hängender Einzug, Zeitschrift und Band kursiv) und `<ol class="mg-notes">`. Im Text: falsche Angaben in `<mark class="mg-flag mg-flag--error">`, uneinheitliche in `mg-flag--notice`, fehlende Felder als Platzhalter `<span class="mg-gap">DOI</span>`, jeweils gefolgt von `<sup class="mg-noteref mg-noteref--…">1</sup>`. Die gerade ausgewählte Stelle bekommt zusätzlich `mg-flag--active` (Textmarker `mark`). Jede Notiz: `<li class="mg-note mg-note--…">` mit `mg-note__head` (Icon, Nummer, kurzer Befund) und einem Satz mit Quelle und Vorschlag.

- Notizen in der Reihenfolge der Stellen im Text nummerieren.
- Die Notiz nennt die Quelle des Vorschlags und, wenn vorhanden, die Kreuzreferenz.
- Braucht mindestens 640px Breite; schmaler die Notizen unter das Zitat stellen.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
