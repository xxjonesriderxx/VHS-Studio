"""Interface translations and explanatory tooltips."""
import re

OCR_PURPOSE = (
    'Wozu Datumsstempel lesen?\n\nAuf einer VHS-Kassette wurde oft an verschiedenen Tagen weitergefilmt – manchmal über Jahre hinweg. Nach der Digitalisierung stecken diese Aufnahmen in einer einzigen Videodatei.\n\nDie optionale Texterkennung (OCR) liest eingeblendete Kameradaten und merkt sich ihre Positionen im Video. Datumswechsel liefern Hinweise darauf, wo unterschiedliche Aufnahmetage beginnen könnten. Das hilft, die Aufnahmen später zu prüfen und gezielt in einzelne Tage aufzuteilen.\n\nVHS Studio schneidet dabei keine Videos automatisch. Im Reiter »Datumsfunde« findest du die Ergebnisse und einen kopierbaren KI-Prüfauftrag, um mögliche Übergänge anhand einzelner Bilder genauer prüfen zu lassen. Ohne lesbaren Datumsstempel kann die OCR den Aufnahmetag nicht bestimmen. Auch OCR-Lesungen und Kameradaten können falsch sein.\n\nBei der ersten Nutzung ist die Funktion ausgeschaltet. Du brauchst sie nur, wenn du Aufnahmetage untersuchen oder eine spätere Trennung vorbereiten möchtest. Deine letzte Auswahl wird gespeichert.',
    'Why read date stamps?\n\nA VHS tape was often reused for more filming on different days, sometimes over several years. After digitisation, these recordings can end up in one video file.\n\nOptional text recognition (OCR) reads visible camera dates and records their positions in the video. Changes in the date provide clues to where a different recording day may begin. This helps you review the footage and prepare to separate it into individual days later.\n\nVHS Studio does not cut videos automatically. The Date findings tab contains the results and a copyable AI review prompt for checking possible transitions more closely using individual frames. Without a readable date stamp, OCR cannot determine the recording date. Both recognised text and camera dates can be incorrect.\n\nThe feature is off on first use. Enable it when you want to investigate recording dates or prepare for splitting the footage later. Your last selection is remembered.'
)

EN = {
"VHS Studio · Familienaufnahmen aufbereiten":"VHS Studio · Restore family recordings",
"Familienaufnahmen erhalten und aufbereiten":"Preserve and restore family recordings",
"Ausgabe öffnen":"Open output",
"So funktioniert’s":"How it works",
"Aufnahmen":"Recordings",
"Ordner mit digitalisierten VHS-Aufnahmen auswählen":"Choose a folder with digitised VHS recordings",
"Ordner wählen":"Choose folder",
"Ablage":"Save to",
"In Ausgabeordner exportieren":"Export to an output folder",
"Familienarchiv fortführen":"Update family archive",
"Ziel":"Destination",
"Ausgabeordner":"Output folder",
"Unterordner einbeziehen":"Include subfolders",
"Geprüfte MP4s werden im Ausgabeordner abgelegt.":"Verified MP4s are saved in the output folder.",
"Geprüfte MP4s im Ausgabeordner.":"Verified MP4s in the output folder.",
"Frühere Fassungen werden archiviert.":"Previous versions are archived.",
"Halbbilder korrigieren":"Correct interlacing",
"Ruhigere Bewegung, weniger Kammstreifen":"Smoother movement, fewer comb artefacts",
"Alte BWDIF-Fassungen auf QTGMC erneuern":"Upgrade old BWDIF versions to QTGMC",
"Details vergrößern":"Enhance details",
"OpenProteus · zweifache Bildgröße":"OpenProteus · double the resolution",
"KI-Modell inklusive":"AI model included",
"Benötigt eine Vulkan-fähige Grafikkarte.\nVHS wird vorab deinterlaced.":"Requires a Vulkan-compatible GPU.\nInterlaced VHS is deinterlaced first.",
"Datumsstempel lesen":"Read date stamps",
"Windows-OCR · oben und unten im Bild":"Windows OCR · top and bottom of the image",
"Fundstellen mit Videosekunde":"Findings with video timestamps",
"Ein Bild pro Sekunde. Datumslesungen\nwerden in SQLite protokolliert.":"One frame per second. Readings\nare recorded in SQLite.",
"Warteschlange":"Queue",
"Dateien pro Lauf":"Files per run",
"0 = alle":"0 = all",
"PC schonen":"Limit CPU load",
"Dateien":"Files",
"Protokoll":"Log",
"Datumsfunde":"Date findings",
"Aufnahme":"Recording",
"Dauer":"Duration",
"Bearbeitung":"Processing",
"Datum im Bild":"On-screen date",
"Gelesener Stempel":"Recognised text",
"Quelle wählen und Dateien prüfen.":"Choose a source and check the files.",
"QTGMC und FFmpeg sind enthalten. Ergebnisse werden vor der Ablage geprüft.":"QTGMC and FFmpeg are included. Outputs are verified before publishing.",
"Dateien prüfen":"Check files",
"Aufbereitung starten":"Start restoration",
"Abbrechen":"Cancel",
"Einstellungen geändert · Dateien prüfen.":"Settings changed · check the files.",
"Ordner mit VHS-Aufnahmen":"Folder with VHS recordings",
"Bitte einen vorhandenen Aufnahmeordner wählen.":"Please choose an existing source folder.",
"Bitte einen Ausgabeordner wählen.":"Please choose an output folder.",
"Für den Export bitte einen anderen Ausgabeordner wählen.":"Please choose a different folder for export.",
"Der Archivmodus benötigt die Familienarchiv-Struktur mit _Originalschnitte.":"Archive mode requires a family archive with an _Originalschnitte folder.",
"Die ursprünglichen VHS-Quellen sind als Lesequelle geschützt.":"The original VHS source folder is protected as a read-only source.",
"Dateibegrenzung muss 0 oder größer sein.":"The file limit must be 0 or greater.",
"Bitte mindestens eine Bearbeitung aktivieren.":"Please enable at least one processing step.",
"Aufnahmen werden geprüft …":"Checking recordings …",
"Quelle prüfen: ":"Checking source: ",
"Ordner prüfen":"Check folder",
"Aufbereitung":"Restoration",
"Aufbereitung gestartet · ":"Restoration started · ",
"Bereit":"Ready",
"Läuft":"Running",
"Fertig":"Complete",
"Fehler":"Error",
"Abgebrochen":"Cancelled",
"Keine passenden Aufnahmen gefunden.":"No matching recordings found.",
" Aufnahmen gefunden …":" recordings found …",
" Aufnahmen bereit.":" recordings ready.",
"Datei ":"File ",
" Dateien":" files",
"Prüfsumme und Ablage":"Checksum verification and publishing",
"QTGMC · Halbbilder rekonstruieren":"QTGMC · reconstructing fields",
"VHS · MP4 erstellen":"VHS · creating MP4",
"OpenProteus · Details aufarbeiten":"OpenProteus · enhancing details",
"OCR · Datumsstempel lesen":"OCR · reading date stamps",
" erfolgreich, ":" successful, ",
" Fehler.":" errors.",
"Ausgabe und Laufprotokoll liegen im Zielordner.":"Output and run log are saved in the destination folder.",
"Lauf abgebrochen.":"Run cancelled.",
"Bereits fertiggestellte Ausgaben bleiben im Zielordner.":"Completed outputs are available in the destination folder.",
"Bearbeitung konnte nicht abgeschlossen werden.":"Processing could not be completed.",
"Bearbeitung beendet · Details im Protokoll.":"Processing ended · see the log for details.",
"Aufbereitung abbrechen":"Cancel restoration",
"Die laufende Ausgabe verwerfen und den Lauf beenden?":"Discard the current temporary output and stop the run?",
"Lauf wird sicher beendet …":"Stopping the run safely …",
"Abbruch angefordert. Laufende Dateioperationen werden beendet.":"Cancellation requested. Current file operations are finishing.",
"Ablage läuft":"Publishing in progress",
"Die geprüfte Ausgabe wird gerade abgelegt. Bitte kurz warten.":"The verified output is being published. Please wait.",
"Ausgabe":"Output",
"Bitte zuerst einen Ausgabeordner wählen.":"Please choose an output folder first.",
"VHS-Aufnahmen aufbereiten":"Restore VHS recordings",
"Oberfläche startbereit.":"Interface ready.",
"Deinterlacing":"Deinterlacing",
"MP4 erstellen":"Create MP4",
"QTGMC-Austausch":"QTGMC replacement",
"Datums-OCR":"Date OCR",
"Datumsfunde exportieren":"Export date findings",
"Funddaten kopieren":"Copy findings",
"KI-Prüfauftrag kopieren":"Copy AI review prompt",
"Scan-Raster":"Scan frequency",
"JSON und CSV werden im Zielordner gespeichert.":"JSON and CSV are saved in the destination folder.",
"Nur OCR-Funde · Datumsstempel können falsch sein.":"OCR findings only · camera dates can be incorrect.",
"Funddaten kopiert.":"Findings copied.",
"KI-Prüfauftrag kopiert.":"AI review prompt copied.",
"Noch keine OCR-Daten vorhanden. Erst einen Lauf mit Datums-OCR abschließen.":"No OCR data yet. Complete a run with date OCR enabled first.",
}

def translate(language, text):
    text=str(text)
    if language=="de":
        return text
    if text in EN:
        return EN[text]
    keys=[key for key in EN if len(key)>3]
    pattern=re.compile("|".join(re.escape(key) for key in sorted(keys,key=len,reverse=True)))
    return pattern.sub(lambda m:EN[m.group()],text)

HELP_EN = """1. Choose a folder with digitised VHS recordings.
2. Choose the output folder or the family archive, and enable the desired steps.
3. Check files, review the queue, then start restoration.

QTGMC reconstructs interlaced fields with high quality. BWDIF is faster.
OpenProteus doubles the image resolution and needs Vulkan graphics drivers.
OCR reads visible dates at the selected frame frequency. Its findings are saved as SQLite, JSON and CSV. Camera dates can be incorrect.

The Date findings tab lets you copy either the data or an AI review prompt. The prompt asks an AI with local file access to verify the dates and locate the actual scene boundaries frame by frame. Copying a prompt does not run an AI.

Archive mode keeps the year/quarter folder structure and saves the prior versions in _Originalschnitte, _Deinterlaced or _Deinterlaced/_BWDIF.

The EXE includes the tools and the model and temporarily extracts them at launch. Windows 10/11 x64 with AVX2 is required. Enable Limit CPU load to leave more resources for other apps."""

TOOLTIPS = {
"source": (
"Ordner mit bereits digitalisierten VHS-Dateien. MKV, MP4, AVI, MPEG, VOB und weitere Videoformate werden erkannt.",
"Folder with already digitised VHS files. MKV, MP4, AVI, MPEG, VOB and other video formats are recognised."),
"output": (
"Beim Export bleiben die Aufnahmen im Quellordner erhalten. Die Unterordnerstruktur wird in der Ausgabe übernommen.",
"Export keeps the source recordings. The relative folder structure is retained in the output."),
"mode": (
"Export legt neue Dateien im Ausgabeordner ab. Archivmodus verschiebt frühere Fassungen in die Archiv-Unterordner, nachdem die Ausgabe geprüft ist.",
"Export saves new files in the output folder. Archive mode moves prior versions into archive subfolders after verification."),
"deint": (
"VHS besteht meist aus zwei zeitlich versetzten Halbbildern. Deinterlacing erzeugt daraus ruhige Vollbilder, bei PAL normalerweise 50 Bilder/s.",
"VHS usually contains two fields captured at different times. Deinterlacing turns them into progressive frames, typically 50 fps for PAL."),
"method": (
"QTGMC nutzt Bewegungsschätzung und ist aufwendiger. BWDIF ist die schnellere Alternative. Progressive Quellen werden ohne Halbbildfilter in MP4 umgewandelt.",
"QTGMC uses motion estimation and is more demanding. BWDIF is faster. Progressive sources are converted to MP4 without a deinterlacing filter."),
"replace": (
"Sucht alte BWDIF-MP4s mit zugehörigem Original unter _Originalschnitte. Die neue QTGMC-Fassung wird aus dem Original erzeugt. Archivmodus sichert BWDIF unter _Deinterlaced/_BWDIF.",
"Finds old BWDIF MP4s with an original in _Originalschnitte. QTGMC is rendered from that original. Archive mode backs up BWDIF in _Deinterlaced/_BWDIF."),
"upscale": (
"OpenProteus 2× vergrößert Breite und Höhe. Das Modell ist enthalten. Die Verarbeitung benötigt eine Vulkan-Grafikkarte und kann sehr lange dauern.",
"OpenProteus 2× doubles width and height. The model is included. Processing needs a Vulkan GPU and can take a long time."),
"ocr": (
"Eine VHS-Kassette kann Aufnahmen vieler Tage oder Jahre enthalten. OCR liest eingeblendete Kameradaten und sammelt Fundstellen für eine spätere Trennung nach Aufnahmetagen. VHS Studio schneidet nichts automatisch. Ergebnisse und KI-Prüfauftrag: Reiter »Datumsfunde«. Fehlende oder falsche Stempel bleiben unsicher. Bei erster Nutzung ausgeschaltet; die letzte Auswahl wird gespeichert.",
"A VHS tape can contain recordings from many days or years. OCR reads visible camera dates and collects findings to help split footage by recording day later. VHS Studio does not cut videos automatically. Results and AI review prompt: Date findings tab. Missing or incorrect stamps remain uncertain. Off on first use; your last selection is remembered."),
"gentle": (
"Startet die Bearbeitung mit Windows-Priorität »Idle« und begrenzt sie auf höchstens 4 physische Kerne / 8 logische Prozessoren. Der PC bleibt reaktionsfähiger, die Verarbeitung dauert länger. GPU-Last beim Upscaling wird dadurch nicht begrenzt.",
"Runs processing at Windows Idle priority on at most 4 physical cores / 8 logical processors. Other apps remain more responsive, while restoration takes longer. This does not cap GPU use during upscaling."),
"limit": (
"Maximale Zahl von Videos in diesem Lauf. 0 verarbeitet alle passenden Aufnahmen. Nach dem Lauf endet die Bearbeitung.",
"Maximum number of videos in this run. Use 0 for all matching recordings. Processing stops when the batch is complete."),
"rate": (
"Links weniger Last, rechts feinere Suche: 0,25 / 0,5 / 1 / 2 / 4 Bilder pro Sekunde. Die Mitte scannt einmal pro Sekunde. Mehr Bilder finden kurze Stempel eher, ersetzen aber keine visuelle Prüfung.",
"Left reduces load, right samples more closely: 0.25 / 0.5 / 1 / 2 / 4 frames per second. The middle scans once per second. More frames help find brief stamps but still need visual verification."),
"copydata": (
"Kopiert den JSON-Export mit OCR-Rohdaten, vorhandenen KI-Bewertungen und Prüfverlauf. SQLite ist die maßgebliche Datenquelle. Es werden keine Videos hochgeladen.",
"Copies the JSON export with raw OCR findings, existing AI reviews and revision history. SQLite is the authoritative data source. No videos are uploaded."),
"copyprompt": (
"Kopiert einen Prüfauftrag mit Pfaden, SQL-Abfrage und Rückschreib-Anleitung. Eine KI mit lokalem Dateizugriff kann Frames prüfen und Bewertungen mit Anbieter/Modell separat speichern. Das startet keine KI und schneidet keine Videos.",
"Copies a review prompt with paths, an SQL query and write-back instructions. An AI with local file access can inspect frames and separately save reviews with provider/model attribution. This neither starts an AI nor cuts videos."),
}

EN.update({"Schonend":"Gentle","Ausgewogen":"Balanced","Volle Leistung":"Full speed","Scan-Raster":"Scan frequency","Bild/s":"fps"})

EN.update({"Hintergrund / Spielen":"Background / Gaming", "KI-Prüfauftrag ansehen":"View AI review prompt", "Arbeitsbereich":"Workspace"})
EN.update({"Restaurierung starten":"Start restoration", "Restaurierung gestartet":"Restoration started", "Autostart einrichten":"Set up auto-start", "Autostart":"Auto-start", "Autostart ist aktiv":"Auto-start is enabled", "Autostart ist ausgeschaltet":"Auto-start is disabled", "Deaktivieren":"Disable", "Profil übernehmen":"Apply profile", "Autostart aktivieren":"Enable auto-start", "Autostartprofil gespeichert.":"Auto-start profile saved.", "Autostart ausgeschaltet.":"Auto-start disabled.", "Letzte Einstellungen geladen · Dateien prüfen.":"Previous settings loaded · check files."})
EN.update({"Ressourcen":"Resources", "Noch keine Dateien geprüft.\nQuelle wählen und »Dateien prüfen« starten.":"No files checked yet.\nChoose a source and select Check files.", "Noch keine Datumsfunde.\nOCR aktivieren und einen Lauf starten.":"No date findings yet.\nEnable OCR and start a run."})
EN.update({"Mehrere Aufnahmetage auf einer Kassette?\nHinweise für eine spätere Trennung finden.":"Several recording days on one tape?\nFind clues for splitting the footage later.", "Nur Fundstellen · kein automatischer Schnitt.":"Findings only · no automatic cutting."})
EN.update({'OCR-Datum':'OCR date','Geprüftes Datum':'Reviewed date','Grenze (s)':'Boundary (s)','Prüfstatus':'Review status','Prüfer / Modell':'Reviewer / model','Bestätigt':'Verified','Korrigiert':'Corrected','Unklar':'Uncertain','Fehlfund':'Rejected','Ungeprüft':'Unreviewed','Prüfdetails':'Review details','Prüfverlauf':'Review history','Doppelklick: Prüfdetails · Prüferangaben sind Selbstauskünfte.':'Double-click: review details · attribution is self-reported.'})
EN.update({'Unsicherheit (s)':'Uncertainty (s)','Begründung':'Evidence and reasoning','Geprüft am':'Reviewed at','Quelle verändert / fehlt':'Source changed / missing'})
