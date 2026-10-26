# Anforderungen – BOBR

## Funktionale Anforderungen

### Import

| ID  | Anforderung |
|-----|-------------|
| F1  | Die Anwendung muss Literaturdaten aus `.bib`, `.txt` und `.pdf` importieren können. |

### Vollständigkeitsprüfung

| ID  | Anforderung |
|-----|-------------|
| F2  | Die Anwendung muss fehlende Pflichtfelder je Quellentyp erkennen (z. B. Autor, Titel, Jahr, Verlag, DOI). |

### Konsistenzprüfung

| ID  | Anforderung |
|-----|-------------|
| F3  | Die Anwendung muss inkonsistente Schreibweisen von Autornamen erkennen (z. B. „Müller, Max" vs. „Max Müller"). |
| F4  | Die Anwendung muss inkonsistente Datumsformate erkennen. |

### Korrektheitsprüfung

| ID  | Anforderung |
|-----|-------------|
| F5  | Die Anwendung muss Feldformate validieren (z. B. DOI-Format, ISBN, URL). |
| F6  | Die Anwendung kann Angaben optional über externe APIs verifizieren (z. B. CrossRef). Dabei müssen Limits und Kosten für den Nutzer sichtbar sein. |

### Korrekturvorschläge

| ID  | Anforderung |
|-----|-------------|
| F7  | Die Anwendung muss erkannte Probleme mit verständlichen Korrekturvorschlägen darstellen. |
| F8  | Der Nutzer muss Korrekturvorschläge annehmen oder ablehnen können. |

### Zitiernetzwerk *(Erweiterung)*

| ID  | Anforderung |
|-----|-------------|
| F9  | Die Anwendung soll darstellen, welche Quellen sich gegenseitig zitieren. |
| F10 | Die Anwendung soll zyklische Zitierbeziehungen erkennen (z. B. Quelle A zitiert Quelle B, Quelle B zitiert Quelle A). |
| F11 | Die Anwendung soll mögliche Interessenkonflikte aufzeigen, wenn Autoren oder Reviewer der importierten Quellen selbst zitiert werden. Der Nutzer muss dafür Kontextinformationen (z. B. beteiligte Personen) eingeben können. |

---

## Nicht-funktionale Anforderungen

### Bedienbarkeit

| ID   | Anforderung |
|------|-------------|
| NF1  | Die grafische Oberfläche muss ohne technische Vorkenntnisse bedienbar sein. |

### Plattform

| ID   | Anforderung |
|------|-------------|
| NF2  | Die Anwendung muss unter Windows und macOS lauffähig sein. |
| NF3  | Die Anwendung läuft lokal und benötigt keine permanente Internetverbindung. |

### Technologie

| ID   | Anforderung |
|------|-------------|
| NF4  | Die Anwendung wird in Python entwickelt. |

### Lizenz und Offenheit

| ID   | Anforderung |
|------|-------------|
| NF5  | Die Anwendung wird als Open-Source veröffentlicht (Lizenz: CC BY 4.0 oder alternativ MIT / Apache 2.0, wird mit dem Auftraggeber abgestimmt). |

---

## Randbedingungen

| ID   | Randbedingung |
|------|---------------|
| RB1  | Das Projekt ist im Studiengang Wirtschaftsinformatik – Business Engineering an der DHBW Ravensburg eingebettet (Kurse WWIBE124 und WWIBE224). |
| RB2  | Auftraggeber ist Prof. Dr. Martin Zaefferer. Entscheidungen zu Lizenz und Scope sind mit ihm abzustimmen. |
| RB3  | Abgabetermin ist das Ende des 6. Semesters (Abschlusspräsentation und schriftliche Ausarbeitung). |
| RB4  | Die Anwendung wird in Python entwickelt. |
| RB5  | Die Anwendung wird lokal ausgeführt – keine Cloud- oder Serverlösung. |
| RB6  | Externe APIs dürfen eingebunden werden, sofern Kosten und Limits für den Nutzer transparent dargestellt werden. |
| RB7  | Die Anwendung muss als Open-Source veröffentlicht werden. |
| RB8  | Inhaltliche Prüfung – ob eine Quelle eine Aussage tatsächlich belegt – ist explizit nicht Teil des Projekts. |
| RB9  | Kein dediziertes Budget; das Projekt ist auf kostenlose und Open-Source-Bausteine angewiesen (z. B. GROBID). |

---

## Zielgruppe

Primäre Zielgruppe sind **Gutachter**, die Literaturlisten wissenschaftlicher Arbeiten prüfen. Sekundär richtet sich die Anwendung an Studierende, wissenschaftlich Arbeitende und Lehrende.
