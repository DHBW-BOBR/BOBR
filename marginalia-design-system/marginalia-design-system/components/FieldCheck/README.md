# FieldCheck

Stellt die Felder eines Eintrags den Werten der Referenzquelle gegenüber.

**Markup:** `<table class="mg-fields">` mit den Spalten Feld · Eintrag · Referenz · Status. Feldname in `mg-fields__label`; ein falscher Eintrag in `mg-fields__wrong` (durchgestrichen), ein leerer in `mg-fields__empty` („nicht angegeben“); der Vorschlag in `mg-fields__suggest`, die Herkunft darunter in `mg-fields__source`. Status als StatusBadge, passende Felder als `mg-status--plain mg-status--verified` mit „Passt“.

- Im Detailpanel nur abweichende Felder zeigen; die passenden in einem Satz darunter zusammenfassen.
- Kennungen im Vorschlag mit der Klasse `identifier`.
- Durchstreichen nur für einen Wert, der durch einen Vorschlag ersetzt wird — nie für fehlende Werte.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
