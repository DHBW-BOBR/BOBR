# StatusBadge

Zeigt den Prüfstatus einer Quelle oder eines Feldes mit Icon und Wort.

**Markup:** `<span class="mg-status mg-status--error"><svg class="mg-icon">…</svg>Fehler</span>`. Töne: `--error` (Fehler), `--missing` (Fehlt), `--notice` (Hinweis), `--verified` (Geprüft). `mg-status--plain` ohne Fläche für ruhige Kontexte wie Tabellenzeilen, die passen. Zahlen in `mg-status__count`.

- Immer Icon und Wort — nie nur einen farbigen Punkt.
- Das Wort darf präziser werden („Jahr weicht ab“, „2 Felder fehlen“), bleibt aber unter vier Wörtern.
- In Listen höchstens zwei Badges pro Zeile, der schwerste zuerst. „Geprüft“ als Fläche nur in Listen; in Detailtabellen `--plain`.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
