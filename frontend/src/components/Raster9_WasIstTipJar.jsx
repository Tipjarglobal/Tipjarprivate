import React from "react";

// ============================================================
// RASTER 9 — WAS IST TIPJAR? (System-Modus + Vorteil-Box + CTA)
// VON: Headline "Was ist TipJar?"
// BIS: Ende CTA "Bereit vom Gruppen-Chaos in den System-Modus zu wechseln?..."
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 760, margin: "0 auto" };
const H = { fontSize: 24, fontWeight: 900, color: "#fff", margin: "0 0 12px" };
const P = { fontSize: 14, color: "#a1a1aa", lineHeight: 1.7, margin: "0 0 20px" };

export default function Raster9_WasIstTipJar() {
  return (
    <section style={{ padding: "32px 16px" }} data-testid="raster9-was-ist-tipjar">
      <div style={WRAP}>
        <h2 style={H}>Was ist TipJar?</h2>
        <p style={P}>
          TipJar ist der Ort, an dem clevere Köpfe aus aller Welt ihre Sportwetten teilen. Mach einen Screenshot deines Scheins oder tippe deinen Tipp —
          Über 2,5, ein Banker vor dem Spiel, ein Live-Lock — und TipJar liest sofort die Teams, den Anstoß, das Land und die Liga und bewertet den Value von 1 bis 10.
          Jeder offene Tipp landet auf der Bewertungswand, Ergebnisse werden automatisch abgerechnet, Münzen fließen zwischen Fans, und sobald du 10.000 Coins sammelst, kassierst du echtes Geld.
        </p>
        <h3 style={{ ...H, fontSize: 18 }}>Warum Anwender TipJar wählen — statt Telegram, Discord &amp; Co.</h3>
        <p style={P}>
          Tipps in Telegram-Gruppen gehen im Lärm unter: kein Überblick, nichts nachvollziehbar, jeder Schein von Hand geprüft. TipJar ist anders.
          Jeder Tipp wird von der KI gelesen, von der Community bewertet und das Ergebnis vollautomatisch abgerechnet.
        </p>
        <div style={{ border: "1px solid rgba(0,255,148,0.3)", background: "rgba(0,255,148,0.05)", borderRadius: 16, padding: 16, marginBottom: 20 }} data-testid="r9-vorteil">
          <p style={{ fontSize: 14, color: "#d4d4d8", lineHeight: 1.7, margin: 0 }}>
            Dein Vorteil: Du sparst Zeit, hast absolute Klarheit über jede Wette und entscheidest mit Daten statt Bauchgefühl.
            Du nutzt ein System, das für dich mitdenkt. Willkommen im System-Modus.
          </p>
        </div>
        <p style={{ ...P, marginBottom: 20 }}>
          Was wir NICHT sind: TipJar ist keine laute Wettgruppe und kein Tipp-Dienst, der Gewinne verspricht — sondern ein Werkzeug für Menschen, die Wert auf Struktur, Daten und Automatisierung legen.
        </p>
        <p style={{ fontSize: 15, fontWeight: 700, color: "#fff", lineHeight: 1.6, margin: 0 }}>
          Bereit, vom Gruppen-Chaos in den System-Modus zu wechseln? Erstelle dein kostenloses Konto, wirf deinen ersten Tipp in den Jar — und lass die Automatik den Rest erledigen.
        </p>
      </div>
    </section>
  );
}
