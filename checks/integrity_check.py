"""Integrity checks for EPUB files (ZIP, CRC, and essential package files).

The standalone ``check_path`` method works even if EPUBContext cannot load.
The standard ``check(ctx)`` method is compatible with BaseChecker/Runner,
but Runner must invoke ``check_path`` before EPUBContext.load() to detect
all corrupted files through the GUI.
"""

from __future__ import annotations

import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from checks.base_checker import BaseChecker


class IntegrityChecker(BaseChecker):
    name = "Integrity"

    def check(self, ctx):
        return self.check_path(ctx.path)

    def check_path(self, path: str | Path):
        path = Path(path)
        if not path.is_file():
            return [self.critical("EPUB file does not exist", str(path))]

        try:
            with zipfile.ZipFile(path, "r") as archive:
                entries = archive.infolist()
                names = set(archive.namelist())
                if not entries:
                    return [self.critical("EPUB ZIP archive is empty", str(path))]

                # testzip reads and decompresses every member and checks CRC.
                try:
                    bad_member = archive.testzip()
                except (RuntimeError, EOFError, OSError, ValueError,
                        zipfile.BadZipFile, NotImplementedError) as exc:
                    return [self.critical(
                        f"ZIP content cannot be fully read: {type(exc).__name__}: {exc}",
                        str(path),
                    )]
                if bad_member is not None:
                    return [self.critical(
                        f"ZIP CRC/decompression failed: {bad_member}",
                        bad_member,
                    )]

                results = []
                if "mimetype" not in names:
                    results.append(self.critical("Missing mimetype file", "mimetype"))
                else:
                    mime = archive.read("mimetype")
                    if mime != b"application/epub+zip":
                        results.append(self.error("Invalid mimetype content", "mimetype"))
                    first = entries[0]
                    if first.filename != "mimetype" or first.compress_type != zipfile.ZIP_STORED:
                        results.append(self.warning(
                            "mimetype should be the first uncompressed ZIP entry", "mimetype"
                        ))

                container_name = "META-INF/container.xml"
                if container_name not in names:
                    results.append(self.critical("Missing container.xml", container_name))
                else:
                    try:
                        root = ET.fromstring(archive.read(container_name))
                        rootfiles = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "rootfile"]
                        paths = [e.get("full-path", "").strip() for e in rootfiles]
                        paths = [p for p in paths if p]
                        if not paths:
                            results.append(self.critical("container.xml has no rootfile full-path", container_name))
                        else:
                            opf_path = paths[0]
                            normalized = posixpath.normpath(opf_path)
                            if (normalized.startswith("../") or normalized.startswith("/") or normalized == ".."):
                                results.append(self.critical("Unsafe OPF path in container.xml", container_name))
                            elif normalized not in names:
                                results.append(self.critical("OPF file referenced by container.xml is missing", normalized))
                            else:
                                try:
                                    opf_root = ET.fromstring(archive.read(normalized))
                                    if opf_root.tag.rsplit("}", 1)[-1] != "package":
                                        results.append(self.error("OPF root element is not package", normalized))
                                except ET.ParseError as exc:
                                    results.append(self.critical(f"OPF XML cannot be parsed: {exc}", normalized))
                    except ET.ParseError as exc:
                        results.append(self.critical(f"container.xml cannot be parsed: {exc}", container_name))

                if not results:
                    results.append(self.ok())
                return results
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            return [self.critical(f"Invalid ZIP archive: {exc}", str(path))]
        except (PermissionError, OSError) as exc:
            return [self.critical(f"Cannot read EPUB: {type(exc).__name__}: {exc}", str(path))]
        except Exception as exc:
            return [self.critical(f"Unexpected integrity check error: {type(exc).__name__}: {exc}", str(path))]
