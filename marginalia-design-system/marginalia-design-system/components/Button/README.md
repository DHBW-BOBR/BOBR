# Button

Löst eine Aktion aus; pro Bereich höchstens ein Primär-Button.

**Markup:** `<button class="mg-btn mg-btn--primary">Liste prüfen</button>`. Varianten `mg-btn--primary` (Tintenblau, die eine Hauptaktion), `mg-btn--secondary` (Fläche mit Rahmen, z. B. Importieren, Exportieren), `mg-btn--quiet` (ohne Fläche, z. B. Ignorieren, Abbrechen). Größe `mg-btn--lg` für die Hauptaktion einer leeren Seite; `mg-btn--icon` für reine Icon-Buttons — dann `aria-label` setzen. Icon als `<svg class="mg-icon">` vor dem Label.

- Label ist ein Verb, ohne Punkt und ohne Ausrufezeichen: „Korrektur übernehmen“.
- Destruktive Aktionen (Quelle entfernen) sind `mg-btn--secondary` und fragen nach; es gibt keinen roten Button — `error` ist für Befunde reserviert.
- Deaktiviert über `disabled`; besser ist oft, den Button gar nicht zu zeigen.

[Vorschau öffnen](index.html) · Dunkel: `index.html?theme=dark` · Styles in [`css/marginalia.css`](../../css/marginalia.css)
