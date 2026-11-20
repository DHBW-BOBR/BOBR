/**
 * format.js — Hilfsfunktionen für die Anzeige.
 */

/**
 * Wandelt einen Zeitstempel des Backends in deutsche Ortszeit um.
 * Was: "2026-11-20 10:47:21" (UTC) -> "20.11.26, 11:47".
 * Warum: Das Backend speichert alle Zeiten in UTC (Vorgabe aus dem Datenbankschema),
 * der Nutzer erwartet aber seine eigene Uhrzeit.
 * Alternativen: Zeit unverändert anzeigen (verwirrend, eine Stunde "falsch") oder
 * eine Bibliothek wie date-fns (neue Abhängigkeit für eine Zeile).
 * @param {string|null} utc - Zeitstempel im Format "YYYY-MM-DD HH:MM:SS" (UTC)
 * @returns {string} Formatiertes Datum oder "–" wenn kein Wert vorhanden
 */
export const formatDate = (utc) => {
  if (!utc) return '–'
  const date = new Date(utc.replace(' ', 'T') + 'Z')
  if (Number.isNaN(date.getTime())) return utc
  return date.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
}

/**
 * Beschreibt den Stand der letzten Prüfung in einem Satz.
 * Ist nur der Start gesetzt (oder liegt das Ende vor dem Start), wurde die Prüfung abgebrochen.
 * @param {{last_check_started_at: string|null, last_check_finished_at: string|null}} upload
 * @returns {string} z. B. "Zuletzt geprüft am 20.11.26, 11:47"
 */
export const checkStatusText = (upload) => {
  const started = upload.last_check_started_at
  const finished = upload.last_check_finished_at
  if (!started) return 'Noch nicht geprüft'
  if (!finished || finished < started) return 'Letzte Prüfung wurde abgebrochen'
  return `Zuletzt geprüft am ${formatDate(finished)}`
}
