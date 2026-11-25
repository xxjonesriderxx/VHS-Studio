"""Generate a portable prompt pointing to local OCR evidence."""
import json
from pathlib import Path
import sqlite3
import sys
import os
from contextlib import closing

SQL = """SELECT v.id AS video_id, v.path AS video_path, s.second, s.date AS camera_date, s.raw,
       COALESCE(r.id, 0) AS latest_review_id, r.decision, r.confirmed_date
FROM ocr_stamps AS s
JOIN ocr_videos AS v ON v.id = s.video
LEFT JOIN ocr_latest_reviews AS r ON r.video=s.video AND r.second=s.second AND r.camera_date=s.date
ORDER BY v.path, s.second;"""

def review_prompt(directory, language="de"):
    folder=Path(directory)
    export=folder/"OCR-Fundstellen.json"
    database=folder/'VHS-Studio.sqlite3'
    if database.exists():
        from review_store import export as refresh_export
        with closing(sqlite3.connect(database)) as db:
            refresh_export(db,folder)
    data=json.loads(export.read_text("utf8"))
    summary=[]
    for video in data["videos"]:
        groups={}
        for hit in video["hits"]:
            group=groups.setdefault(hit["date"],{"first":hit["second"],"last":hit["second"],"count":0})
            group["first"]=min(group["first"],hit["second"])
            group["last"]=max(group["last"],hit["second"])
            group["count"]+=1
        summary.append({"path":video["path"],"filename_date":video["expected_date"],"readings":groups})
    intro_de=f"""Prüfe meine digitalisierten VHS-Familienaufnahmen anhand vorhandener OCR-Fundstellen.
Die Videos liegen lokal auf dem Rechner. Arbeite mit den Originalpfaden in den Daten.

OCR-Export: {export}
SQLite-Datenbank: {folder/"VHS-Studio.sqlite3"}

Die OCR ist eine grobe Hinweisliste. Ziffern können falsch gelesen sein und Kamerastempel können falsch eingestellt sein. Dateinamen sind ebenfalls keine sichere Datumsquelle.

1. Lies zuerst den Export und vorhandene Projektanweisungen wie AGENTS.md.
2. Prüfe jede abweichende Datumslesung und jeden Wechsel zwischen Datumsgruppen. Gruppiere wiederholte Treffer derselben Szene.
3. Extrahiere mit FFmpeg Bilder mehrere Sekunden vor und nach dem Fund. Vergleiche Kamerastempel, Szene und Personen. Bei Übergängen prüfe bildweise und identifiziere das letzte Bild der alten und das erste Bild der neuen Szene.
4. Gib die Grenze als Sekunden mit Millisekunden an, soweit die Bildrate das erlaubt. Erfinde keine Genauigkeit zwischen zwei Bildern. Notiere Zeitbasis, Bildrate, bestätigte Datierung und verbleibende Unsicherheit. Bei Original und Deinterlaced können sich die Zeitpositionen geringfügig unterscheiden.
5. Prüfe weitere vorhandene Fassungen desselben Tages und die Quellzuordnung. Beachte offene Fragen und Familienhinweise.
6. Ändere im Rahmen dieses Prüfauftrags keine Videos. Dokumentiere bestätigte Grenzen, Fehlablesungen und offene Datumszuordnungen in einer nachvollziehbaren Tabelle. Falls eine passende Prüf-Tabelle in der Datenbank vorhanden ist, erhaltene Rohdaten bewahren und Bewertungen separat eintragen.

SQL-Abfrage:
{SQL}

Zusammenfassung der OCR-Lesungen (die vollständigen Einzelbilder-Zeitpunkte stehen im Export):
"""
    intro_en=f"""Review my digitised VHS family recordings using existing OCR findings.
The videos are local files. Use the original file paths from the data.

OCR export: {export}
SQLite database: {folder/"VHS-Studio.sqlite3"}

OCR is only a coarse list of clues. Digits may be misread and camera clocks may be set incorrectly. File names are not authoritative dates.

1. Read the export and project instructions such as AGENTS.md.
2. Review each conflicting date and transition between date groups. Group repeated readings from the same scene.
3. Extract FFmpeg frames several seconds before and after each finding. Compare the stamp, scene and people. Step frame by frame at transitions to identify the last frame of the old scene and the first frame of the new one.
4. Report seconds with milliseconds to the accuracy supported by the frame rate. Do not invent sub-frame precision. Record time base, frame rate, verified dates and uncertainty. Original and deinterlaced versions can have slightly different timelines.
5. Check existing versions of the same day and their source mapping. Respect unresolved questions and family context.
6. Do not edit videos as part of this review. Document verified boundaries, OCR errors and unresolved dates in a traceable table. If an appropriate review table exists in the database, preserve raw findings and add reviews separately.

SQL query:
{SQL}

OCR reading summary (the export contains all individual sample timestamps):
"""
    command=[sys.executable]
    if not getattr(sys,'frozen',False):
        command.append(str(Path(__file__).with_name('app.py').resolve()))
    contract_de='''

VERBINDLICHER RÜCKKANAL
SQLite ist maßgeblich. OCR-Rohdaten niemals überschreiben. JSON und CSV nicht
von Hand ändern: Sie werden nach Prüfeinträgen automatisch aus SQLite erzeugt.
Lies im JSON video.id sowie hit.second, hit.date und hit.review.id (0, wenn
noch ungeprüft). Schreibe jede visuell geprüfte Fundstelle mit dem Werkzeug
submit_ocr_review über MCP oder den lokalen JSON-Aufruf unten zurück.
decision: verified=Datum bestätigt, corrected=Datum korrigiert,
uncertain=Zuordnung offen, rejected=OCR-Fehlfund ohne bestätigtes Datum.
confirmed_date ist bei verified/corrected Pflicht, sonst null.
boundary_second ist die visuell bestimmte Szenengrenze in Sekunden auf GENAU
dieser Videofassung, nicht automatisch die OCR-Fundsekunde. Wenn unbekannt:
null. Gib uncertainty_second mit an; keine erfundene Millisekundengenauigkeit.
evidence nennt tatsächlich geprüfte Frames, Bildrate/Zeitbasis, Begründung und
Unsicherheit. provider nennt Anbieter/Anwendung, model den tatsächlich bekannten
Modellnamen, sonst null. Diese Angaben werden als Selbstauskunft gespeichert.
expected_review_id muss der zuletzt gelesenen review.id entsprechen, anfangs 0.
Bei Konflikt neu lesen und vergleichen; keine fremde Bewertung blind ersetzen.
Prüfverlauf bleibt erhalten. Verschiebe keine Videos und schneide nichts.
Wenn du keine lokalen Schreibwerkzeuge hast, liefere stattdessen die fertigen
JSON-Anfragen und sage ausdrücklich, dass noch NICHT zurückgeschrieben wurde.
'''
    contract_en='''

REQUIRED WRITE-BACK CONTRACT
SQLite is authoritative. Never overwrite raw OCR. Do not edit JSON/CSV by hand;
they regenerate from SQLite after review submissions. Read video.id, hit.second,
hit.date and hit.review.id (0 if unreviewed) from JSON. Submit each visually
reviewed finding using submit_ocr_review through MCP or the local JSON API.
decision: verified=confirmed date, corrected=corrected date, uncertain=unresolved,
rejected=false OCR finding. confirmed_date is required for verified/corrected;
otherwise null. boundary_second is a visually verified scene boundary in seconds
on THIS video version, not automatically the OCR sample time. Use null if
unknown. Include uncertainty_second; do not invent sub-frame precision.
evidence describes actual frames inspected, frame rate/timebase, reasoning and
uncertainty. provider identifies your provider/application; model is your actual
known model name, otherwise null. Attribution is self-reported, not attested.
expected_review_id must match the last read review.id, initially 0. On conflict,
reload and compare; never blindly overwrite another review. History is retained.
Do not move or cut videos. If you lack local writing tools, return ready-to-save
JSON requests and explicitly report that write-back has NOT happened.
'''
    example=dict(tool='submit_ocr_review',arguments=dict(database=str(database),
        video_id='COPY video.id',second='COPY hit.second',camera_date='COPY hit.date',
        expected_review_id='COPY hit.review.id OR 0',decision='uncertain',provider='YOUR PROVIDER',
        model=None,confirmed_date=None,boundary_second=None,uncertainty_second=None,
        evidence='REPLACE with actual visual evidence; this template is not a completed review'))
    return ((intro_de if language=='de' else intro_en)+json.dumps(summary,ensure_ascii=False,indent=2)
        +(contract_de if language=='de' else contract_en)
        +'\nLocal command (argument array, no shell quoting required):\n'
        +json.dumps(command+['--api','ABSOLUTE-request.json','ABSOLUTE-response.json'],ensure_ascii=False)
        +'\nRequest TEMPLATE (replace placeholders and use numeric IDs/timestamps):\n'
        +json.dumps(example,ensure_ascii=False,indent=2)
        +'\nRead the response: ok=true and result.saved=true mean DB saved. '
        +'If exports_updated=false, SQLite is still saved; exports need refresh. '
        +'The GUI reads SQLite and refreshes the Date findings tab automatically.\n')
