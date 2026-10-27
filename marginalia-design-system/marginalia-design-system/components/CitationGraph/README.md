# CitationGraph

Zeigt, welche Quellen der Liste einander zitieren, und hebt Widersprüche zwischen ihnen hervor.

**Markup:** `<figure class="mg-graph">` mit einem `<svg>` und `<figcaption class="mg-graph__legend">`. Kanten als `<line class="mg-graph__edge">` mit Pfeilspitze (`marker-end`) vom zitierenden zum zitierten Werk; `--active` für Kanten der Auswahl, `--conflict` (gestrichelt, `error`) für einen Widerspruch. Knoten als `<circle class="mg-graph__node">` mit `--selected`, `--error`, `--missing` oder `--notice`; Beschriftung „Nachname Jahr“ als `mg-graph__label`. Der Konsument liefert Positionen (Layout-Bibliothek nach Wahl) und Kantenlisten.

- Knotengröße darf zeigen, wie oft eine Quelle innerhalb der Liste zitiert wird; sonst gleiche Größe.
- Beschriftungen dürfen Kanten nicht kreuzen; lieber über oder neben den Knoten setzen.
- Das `aria-label` des SVG beschreibt Auswahl und Widersprüche in Worten; die Legende bleibt sichtbar.
- Die Vorschau zeigt Beispieldaten, kein vollständiges Zitationsnetz dieser Arbeiten.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
