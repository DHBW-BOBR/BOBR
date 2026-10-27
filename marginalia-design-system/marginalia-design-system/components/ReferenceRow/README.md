# ReferenceRow

Eine Quelle in der Liste: Nummer, Werktitel, Autoren, Erscheinungsort und Status.

**Markup:** `<ul class="mg-reflist" role="listbox">` mit `<li class="mg-ref" role="option" aria-selected="…">`. Kinder in dieser Reihenfolge: `mg-ref__index` („[2]“), `<h3 class="mg-ref__title work-title">`, `mg-ref__status` (ein bis zwei StatusBadges), `mg-ref__authors`, `mg-ref__meta` mit `mg-ref__venue` (Zeitschrift oder Konferenz, kursiv) und weiteren `<span>` für Band(Heft), Seiten und Jahr.

- Die Liste zeigt die Angaben, wie sie im Eintrag stehen — auch falsche (hier „1986“). Korrekturen erscheinen erst im Detail.
- Titel höchstens zwei Zeilen, Autorenzeile eine Zeile mit Auslassung; das vollständige Zitat steht im Detail.
- Auswahl über `aria-selected="true"` (Fläche `accent-soft`), nicht über Fettdruck.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
