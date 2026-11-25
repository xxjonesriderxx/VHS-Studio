# Herkunftsnachweis für die Windows-Runtime

Geprüft am 25. November 2026. Astral veröffentlicht CPython 3.12.16 für Windows x86-64 mit MSVC als Asset des Releases 20261123. Der neue Starter kann diese Runtime direkt von Astral beziehen. [Originalrelease](https://github.com/astral-sh/python-build-standalone/releases/tag/20261123)

| Prüfung | Ergebnis |
| --- | --- |
| Asset | [cpython-3.12.16+20261123-x86_64-pc-windows-msvc-install_only.tar.gz](https://github.com/astral-sh/python-build-standalone/releases/download/20261123/cpython-3.12.16+20261123-x86_64-pc-windows-msvc-install_only.tar.gz) |
| Heruntergeladene Größe | 47,477,423 Byte |
| SHA-256 der heruntergeladenen Bytes | `93584a7bee14bf6b91a03efdbb128419147279a64934fbc95934c9f53e1191e5` |
| SHA-256 aus [Astrals SHA256SUMS](https://github.com/astral-sh/python-build-standalone/releases/download/20261123/SHA256SUMS) | `93584a7bee14bf6b91a03efdbb128419147279a64934fbc95934c9f53e1191e5` |
| Archivstruktur | 3461 reguläre Dateien, 0 Verzeichniseinträge, 0 symbolische Links, 0 Hardlinks, 0 sonstige Nutzlasttypen |

Die exakt benannte Zeile der Original-Prüfsummenliste stimmt mit dem unabhängig berechneten SHA-256 überein. Sämtliche logischen TAR-Pfade liegen unter `python/`; alle Pfadnamen sind eindeutig. Die Prüfung erfolgte am dekomprimierten TAR im Speicher.

Enthaltene Windows-Laufzeitdateien für GUI, Tcl/Tk, venv und pip:

- `python/python.exe`
- `python/pythonw.exe`
- `python/DLLs/_tkinter.pyd`
- `python/tcl/tcl8.6/init.tcl`
- `python/tcl/tk8.6/tk.tcl`
- `python/Lib/venv/__init__.py`
- `python/Lib/site-packages/pip/__init__.py`

Der Nachweis umfasst Archivinhalt und Herkunfts-Hash. Ein Ausführungstest des .NET-Starters oder der entpackten Runtime ist davon getrennt.
