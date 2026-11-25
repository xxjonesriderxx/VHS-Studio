# VHS Studio: Lizenzcheckliste

Stand: 25. November 2026. Zwei GPT-6.2-Astra-Agents haben unabhängig die gesamte
Auslieferung geprüft. Die Detailtabellen listen Bibliothek, Version, Zweck,
Originalquelle/Lizenz und getrennte Bewertungen für EXE, Offline-ZIP und Direktbezug.

**Ein echter Nachlade-Build ist grundsätzlich veröffentlichbar.** Die GUI,
Python und zulässig eingebettete Bibliotheken können bleiben. Komponenten, deren
Weitergabe zusätzliche Arbeit erfordert, lassen sich unmittelbar vom unabhängigen
Originalanbieter auf den Nutzer-PC beziehen. Die heutige EXE ist noch kein solcher
Build: Sie enthält bereits GPL-Python-Code, den GPU-Wrapper und Modellgewichte.

## Die wichtigsten Einträge

**✅** Mitlieferung grundsätzlich erlaubt, übliche zugeordnete Lizenzhinweise
beibehalten. **🟨** Mitlieferung erlaubt bzw. umsetzbar, genannte Auflage im aktuellen
Build noch zu erledigen. **❓** Konkrete Integrations-/Rechtefrage offen.
Ein Haken bei einer Bibliothek ist keine Freigabe der gesamten EXE.

| Bibliothek / Bestandteil | Zweck | Lizenz | Veröffentlichung mit dieser Komponente | Direkter Originalbezug beim Nutzer |
| --- | --- | --- | --- | --- |
| VHS Studio, eigener Code | GUI, Abläufe, MCP, Datenbank | MIT | ✅ Eigener vollständiger Quelltext und MIT-Lizenz | ✅ |
| CPython / Standardbibliothek | Python ausführen | PSF und beigefügte Einzellizenzen | ✅ Originalbedingungen mitführen; Microsoft-Dateien gesondert prüfen | ✅ |
| CustomTkinter / Darkdetect | GUI | MIT / BSD-3 | ✅ Zugeordnete Hinweise mitführen; Schriften gesondert | ✅ |
| Pillow | Bilder / Vorschau | MIT-CMU und Codec-Lizenzen | ✅ Hauptteil; erforderliche Codec-/Urheberhinweise im Detailbericht | ✅ |
| NumPy / SciPy | Arrays / numerische Filter | BSD und native Einzellizenzen | ✅ Hauptteile; BLAS, GCC-Ausnahme und Microsoft-Dateien separat zugeordnet | ✅ |
| Python MCP SDK / Pydantic / HTTP-Komponenten | KI-Schnittstelle, Validierung, HTTP | überwiegend MIT / BSD / Apache | ✅ Hauptpakete; native und mitkopierte Teilbibliotheken einzeln in den Detailtabellen | ✅ |
| psutil / PyWin32 | Prozesse, Windows-Shell, Benachrichtigungen | BSD / komponentenspezifisch | ✅ Benutzte Teile mit ihren Originalhinweisen | ✅ |
| PyWinRT, sieben Pakete | Windows-OCR | MIT | 🟨 Zugehörigen Microsoft-MIT-Text ergänzen und zuordnen | ✅ |
| siphash24 | Hash-Funktion | Apache-2.0 ODER LGPL-2.1+ | 🟨 Apache-Alternative wählen, zugehörige Hinweise ergänzen | ✅ |
| vs-jetpack / QTempGaussMC | QTGMC-Ablauf in Python | MIT | ✅ Eigener Projektanteil; aufgerufene Plugins separat | ✅ |
| FFmpeg / ffprobe von Gyan | Video lesen / schreiben | GPLv3-Build | 🟨 Passende Quellen-/Buildzugänge und Hinweise vollständig zuordnen | ✅ |
| VapourSynth | Frameserver | LGPL-2.1+ | 🟨 Quellen und anwendbaren Austausch-/Neubindungsweg dokumentieren | ✅ |
| MVUtensils v9 | Bewegungsanalyse | GPL-2.0-oder-später | 🟨 Mit Quellen möglich; der zuvor behauptete v2-only-Blocker ist durch die Owner-Klarstellung korrigiert | ✅ |
| znedi3 3.3 | NNEDI3-Interpolation | GPLv2 laut Projekt | ❓ Einzelverteilung unter GPLv2 möglich; konkrete integrierte Kombination mit GPLv3-Code klären | ✅ Für lokale Nutzung; kein eigener Plugin-Vertrieb durch den reinen Starter |
| dfttest2 Python / CPU-Plugin | Rauschfilter | GPLv3-Texte; abweichende CPU-Metadaten | 🟨 GPL-Pfad, passende Quellen und Bedingungen der Kombination sauber ausweisen | ✅ |
| BestSource 23 | Videodecoder für QTGMC | MIT-Plugin plus enthaltenes GPLv3-FFmpeg | 🟨 Quellen und Hinweise für diesen zweiten FFmpeg-Build zuordnen | ✅ |
| upscale-ncnn-py | GPU-Inferenz | GPLv3-Text, widersprechende BSD-Metadaten | 🟨 GPLv3-Pfad samt Quellen erfüllen; nicht als belegtes BSD-Paket ausgeben | ✅ |
| NCNN / pybind11 | Inferenz / Python-Bindung | BSD-3 | 🟨 Native Originalhinweise zusätzlich zum Wrapper zuordnen | ✅ |
| OpenProteus-Gewichte | KI-Upscaling | CC BY-NC 4.0 | 🟨 Nichtkommerzielle Weitergabe mit Attribution möglich; Modellrechte vom App-Code trennen | ✅ Nutzungsbeschränkung bleibt bestehen |
| Microsoft-C-/C++-Laufzeiten | Native DLLs ausführen | Microsoft-Bedingungen | 🟨 Berechtigte Quelle / Weitergaberecht der konkreten Dateien belegen oder Hersteller-/Systembezug verwenden | ✅ Unter den Herstellerbedingungen |
| Roboto-Schriften | GUI-Schrift | Apache-2.0 | 🟨 Originalcopyright und Apache-Zuordnung eindeutig mitführen | ✅ |
| PyInstaller | Ein-Datei-EXE / Laufzeit-Hooks | GPL mit Einbettungsausnahme / Apache | ✅ Ausnahme erlaubt die App-Auslieferung unter passender eigener Lizenz | ✅ |

## Vollständige Einzelprüfungen

- [Prüfung B: sämtliche identifizierten Pakete und Unterbibliotheken](license-checklist-b.md)
- [Prüfung C: unabhängiger Gegencheck mit versionsbezogenen Originallizenz-Links, Rust-Bestandteilen und nativer Dateiliste](license-checklist-c.md)
- [Exaktes Artefaktinventar und Prüfsummen](artifact-inventory.json)
- [Zusätzlicher Live-Abruf offizieller GitHub-Lizenzdateien für alle 63 Python-Pakete](upstream-license-check.json)
- [Originalantworten der Maintainer](upstream-clarifications.json)

Die Tabellen erfassen 63 direkt zugeordnete Python-Distributionen, sieben gesondert
zugeordnete WinRT-Pakete, 13 native QTGMC-Pakete und identifizierte Unterbibliotheken.
Prüfung C nennt zusätzlich 77 im nativen Code identifizierte Rust-Paketversionen.
Unbekannte Versionsstände statisch eingebauter Bestandteile sind als solche markiert.
Eine gestrippt vorliegende DLL erlaubt keine ehrliche Garantie, dass sich daraus
sämtliche statischen Teilbibliotheken rekonstruieren lassen.

## Wichtige Korrektur und Originalquellen

Der MVUtensils-Maintainer bestätigt ausdrücklich GPLv2 oder später für v9:
[offizielle Klarstellung](https://github.com/myrsloik/mvutensils/issues/17#issuecomment-6954012372).
Die frühere Einordnung als v2-only-Sperre ist damit korrigiert. Für znedi3 verweist
der Maintainer auf die Lizenz im Repository und die Rechte des ursprünglichen Autors:
[offizielle Antwort](https://github.com/sekrit-twc/znedi3/issues/28).

Die GNU-Texte unterscheiden die private Nutzung von der Weitergabe und beurteilen
bei Plugins die konkrete Verbindung:
[GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html),
[Plugin-FAQ](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins).
Ein echter Direktdownload vom unabhängigen Originalanbieter beseitigt unsere
Weitergabe dieser konkreten Bytes. Er ersetzt keine Nutzungsrechte, etwa beim
[nichtkommerziellen Modell](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en).

**Diese Prüfung verändert oder veröffentlicht keine Binärdateien.** Die alten
Auditberichte A/B/C dokumentieren Zwischenstände; für die Bewertung gelten die
neueren Checklisten einschließlich der oben genannten Korrektur.
