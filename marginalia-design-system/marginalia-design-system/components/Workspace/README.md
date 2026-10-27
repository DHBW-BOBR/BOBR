# Workspace

Die Arbeitsansicht: Seitenleiste, Quellenliste und Detailpanel der ausgewählten Quelle.

**Markup:** `<div class="mg-app">` mit `<aside class="mg-sidebar">` (Name in `mg-brand`, Navigation `mg-nav` mit `mg-nav__item`, aktive Seite per `aria-current="page"`, Zähler in `mg-nav__count`), `<main class="mg-main">` (Eyebrow, `display`-Titel, CompletenessMeter, Werkzeugleiste mit SegmentedControl und Suche, Liste aus ReferenceRow) und `<section class="mg-panel">` (Titel in `headline`, StatusBadges, FieldCheck, Kreuzreferenz in `mg-callout`, Aktionen).

- Das Detailpanel zeigt immer genau eine Quelle; ohne Auswahl bleibt es leer mit einem Satz („Wähle eine Quelle, um ihre Befunde zu sehen.“).
- Die Zusammenfassung über der Liste ist ein Satz in Worten, keine Kennzahlen-Kacheln.
- Die Vorschau verwendet Beispieldaten; die eingebauten Fehler (Jahr 1986, fehlende DOI und Seiten) sind absichtlich.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
