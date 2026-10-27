# Marginalia — Gestaltungsregeln

Marginalia ist die Oberfläche eines Werkzeugs, das Literaturverzeichnisse wissenschaftlicher Arbeiten prüft: Autoren, Jahr, Titel, Zeitschrift, Seiten und DOI werden mit Referenzquellen wie Crossref abgeglichen, fehlerhafte und fehlende Angaben markiert und Widersprüche zwischen den Quellen einer Liste sichtbar gemacht. Das Vorbild sind Anmerkungen am Seitenrand: ruhig, präzise, hilfreich. Die Oberfläche soll sich anfühlen wie gutes Papier unter einer Leselampe — man kann stundenlang darauf schauen.

## Haltung

- **Papier statt Bildschirm.** Warme, gedämpfte Flächen (`paper`, `surface`), nie reines Weiß oder Schwarz. Kein Farbverlauf, kein Glas, kein Glow.
- **Inhalt vor Bedienung.** Titel von Arbeiten stehen in der Serifenschrift und sind das Lauteste auf der Seite. Bedienelemente bleiben leise, bis man sie braucht.
- **Befunde benennen, nicht alarmieren.** Ein Fehler ist eine Tatsache mit Vorschlag, keine Warnung in Rot über die ganze Breite. Farbe markiert die Stelle, das Wort erklärt sie.
- **Jede Farbe hat eine Bedeutung.** Außer `accent` gibt es keine Schmuckfarbe. Rot, Ocker, Schiefer und Blaugrün sind für Status reserviert.

## Sprache

- Du-Form, sachlich, kurze Sätze. Satzanfang groß, sonst Kleinschreibung wie im Satz — keine Großbuchstaben-Überschriften, keine Ausrufezeichen, keine Emoji.
- Befunde nennen erst die Stelle, dann die Quelle, dann den Vorschlag: „Jahr weicht ab. Crossref nennt 1989.“ — nicht „Achtung: Falsches Jahr!“
- Status-Wörter sind fest: **Fehler**, **Fehlt**, **Hinweis**, **Geprüft**. Für einzelne Felder in Tabellen: **Passt**.
- Aktionen sind Verben: „Korrektur übernehmen“, „Liste prüfen“, „Importieren“, „Ignorieren“.
- Herkunft immer nennen: „Geprüft gegen Crossref · vor 2 Min.“ Niemand soll raten, woher ein Vorschlag kommt.
- Bibliografische Angaben selbst bleiben in der Sprache der Quelle (englische Titel bleiben englisch).

## Farbe

Zwei Themes: **Papier** (`light`, Standard) und **Abend** (`dark`). Beide sind warm; das Abend-Theme ist für lange Sitzungen gedacht, nicht als Effekt.

- Seitenhintergrund `paper`; Karten, Panels und Dialoge `surface`; Seitenleiste, Eingabe-Schienen und Hinweisboxen `surface-sunken`; Hover `surface-hover`.
- Text in drei Stufen: `ink` für Inhalte und Werte, `ink-muted` für Autoren und Labels, `ink-subtle` nur für Metadaten wie Zeitstempel und Zähler — und nie auf Soft-Flächen.
- `accent` (Tintenblau) für genau vier Dinge: Primäraktion, Auswahl, Links, Fokus. Ausgewählte Listenzeile: `accent-soft`. Text auf einer `accent`-Fläche ist `on-accent`, nie Weiß.
- Gliedernde Haarlinien `line`. Rahmen, die ein Bedienelement erkennbar machen (Eingabefeld, Sekundär-Button), `line-control`.
- Textmarker `mark` nur für Suchtreffer und die gerade besprochene Stelle im Zitat.

| Status | Farbe | Fläche | Bedeutung |
| --- | --- | --- | --- |
| Fehler | `error` | `error-soft` | Angabe widerspricht der Referenzquelle |
| Fehlt | `missing` | `missing-soft` | Pflichtfeld leer |
| Hinweis | `notice` | `notice-soft` | uneinheitlich, aber nicht falsch |
| Geprüft | `verified` | `verified-soft` | abgeglichen und vollständig |

Statusfarben erscheinen nie ohne Wort oder Icon. `verified` ist bewusst Blaugrün statt Grasgrün, damit es sich auch bei Rot-Grün-Sehschwäche von `error` abhebt.

## Typografie

Drei Schriften, alle unter SIL Open Font License und als Dateien enthalten:

- **Newsreader** (`serif`) für alles, was zum Werk gehört: `display` für den Seitentitel (einer pro Ansicht), `headline` für Abschnitte und den Titel im Detailpanel, `work-title` für Titel von Arbeiten in Listen. Zeitschriften- und Buchtitel kursiv in Newsreader, wie im Zitierstil.
- **Instrument Sans** (`sans`) für die Bedienung: `body` als Standard, `label` für Buttons, Feldlabels und Navigation, `caption` für Badges und Zeitstempel.
- **IBM Plex Mono** (`mono`) im Stil `identifier` für alles, was man kopiert: DOI, ISBN, ISSN, arXiv-ID, BibTeX-Schlüssel.

Zähler und Fortschrittswerte mit `font-variant-numeric: tabular-nums` (Klasse `mg-num`). Newsreader ist variabel mit optischer Größe — `font-optical-sizing: auto` lassen. Die Familien `Newsreader Ext` und `Instrument Sans Ext` decken erweiterte lateinische Zeichen ab (Ł, ř, ő …), damit Autorennamen aus aller Welt in derselben Schrift stehen; sie sind in den Stacks schon enthalten.

## Abstände und Layout

- 4px-Raster: `space-1` bis `space-8`. Eng innerhalb einer Gruppe (`space-2`, `space-3`), großzügig zwischen Gruppen (`space-5` bis `space-7`).
- Arbeitsansicht dreispaltig: Seitenleiste 232px (`mg-sidebar`), Liste flexibel (`mg-main`), Detailpanel 400px (`mg-panel`) im Rahmen `mg-app`.
- Lesbare Zeilen: Fließtext höchstens 72 Zeichen, Befundtexte höchstens 44.
- Rohzitate mit hängendem Einzug (2em), wie im Literaturverzeichnis.

## Flächen, Linien, Schatten, Radien

- Haarlinien zuerst. Listen trennen Zeilen mit `line`, Karten haben eine `line`-Kontur statt Schatten.
- Schatten nur für Schwebendes: `shadow-sm` für das aktive Segment, `shadow-md` für Menüs und Popover, `shadow-lg` für Dialoge.
- Radien verschachtelt: innen = außen minus Abstand. `radius-md` für Buttons, Felder und Listenzeilen; `radius-lg` für Karten und Panels; `radius-xl` für Dialoge; `radius-full` nur für Fortschrittsbalken und Knoten im Zitationsnetz.
- Keine Karten mit farbiger Randleiste. Hervorhebung geschieht über Fläche (`accent-soft`, `surface-sunken`), nicht über Streifen.

## Befunde darstellen

- In Listen: Status-Badges rechts, maximal zwei pro Zeile — der schwerste zuerst (Fehler vor Fehlt vor Hinweis).
- Im Detail: Feldprüfung als Tabelle „Feld · Eintrag · Referenz · Status“; nur abweichende Felder zeigen, der Rest als ein Satz („Autor, Titel … stimmen überein.“).
- Im Rohzitat: die betroffene Stelle markieren (`mg-flag`) und die Erklärung als Randnotiz daneben (`mg-notes`) — das namensgebende Muster.
- Kreuzreferenzen: Widersprüche zwischen zwei Einträgen als gestrichelte `error`-Kante im Zitationsnetz und als Hinweisbox im Detail, mit beiden Quellen beim Namen.

## Ikonografie

Linienicons im Stil von Lucide: 24er-Raster, 1,5px Strich (1,75px bei 14px), runde Enden, Farbe über `currentColor`. Größe 16px in Bedienelementen, 14px in Badges. Status-Icons sind fest: Kreis mit Kreuz (Fehler), gestrichelter Kreis mit Strich (Fehlt), Kreis mit i (Hinweis), Kreis mit Haken (Geprüft). Keine Emoji, keine gefüllten oder zweifarbigen Icons. Ein Logo gibt es noch nicht: den Namen in Newsreader 500 setzen (`mg-brand`).

## Bewegung

Kurz und ohne Federn: 120ms ease-out für Hover und Auswahl, 200ms für Panels und Sheets. Nichts blinkt, nichts pulsiert — auch nicht bei Fehlern. `prefers-reduced-motion` schaltet Übergänge ab.

## Zugänglichkeit

- Jeder Text erreicht mindestens 4,5:1 auf den Flächen, die seine Notiz nennt, in beiden Themes; Rahmen von Bedienelementen und Statusfarben als Fläche mindestens 3:1.
- Fokus ist der Token `focus-ring`: 2px Abstand in `surface`, dann 2px durchgehendes `accent`, als box-shadow. Nie entfernen, nie durch Farbwechsel allein ersetzen.
- Status nie nur über Farbe: immer Wort und Icon.

## Komponenten verwenden

Die Komponenten sind reines CSS ([`css/marginalia.css`](../css/marginalia.css), Präfix `mg-`) und funktionieren mit jedem Framework. Erst [`tokens/tokens.css`](../tokens/tokens.css) laden, dann `css/marginalia.css`; das Theme über `data-theme="light"` oder `data-theme="dark"` am `html`-Element setzen. Schriftgrößen kommen aus den Typstil-Klassen von `tokens.css` (`display`, `headline`, `work-title`, `body`, `label`, `caption`, `identifier`), Farben und Abstände ausschließlich aus Tokens. Das Markup jeder Komponente steht in ihrem README unter [`components/`](../components/) und in ihrer Vorschau (`index.html` im selben Ordner).
