from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import posixpath
from urllib.parse import unquote, urlsplit
from core.html_document import HTMLDocument

class EPUBContext:

    def __init__(self, path: Path):

        self.path = path
        self.zip = None
        self.names = set()
        
        self.opf_path = None
        self.opf_tree = None
        self.opf_ns = {}
        self.manifest = {}
        self.spine = []
        self.metadata = {}
        self.xml_cache = {}

        self.html_files = []
        self.css_files = []
        self.image_files = []
        self.font_files = []
        self.audio_files = []
        self.video_files = []
        self.nav_file = None
        self.ncx_file = None
        self.html_cache = {}

    def load(self):
        self.zip = zipfile.ZipFile(self.path)
        self.names = set(self.zip.namelist())
        self._load_container()
        self._load_opf()
        self._build_manifest()
        self._build_spine()
        self._build_metadata()
        self._build_file_index()

    def close(self):

        if self.zip:
            self.zip.close()
            
    def exists(self, name: str):
        return name in self.names

    def _build_manifest(self):

        self.manifest = {}

        manifest = self.opf_tree.find(
            "opf:manifest",
            self.opf_ns
        )

        if manifest is None:
            return

        opf_dir = posixpath.dirname(self.opf_path)

        for item in manifest.findall(
            "opf:item",
            self.opf_ns
        ):

            href = item.attrib.get("href", "")

            # OPF href is a URI reference, while ZIP entries use decoded
            # filenames. Resolve only its path (not query or fragment).
            # Decode AFTER splitting the URI so encoded ?/# in filenames
            # remain part of the filename.
            href_path = unquote(urlsplit(href).path)
            path = posixpath.normpath(
                posixpath.join(opf_dir, href_path)
            )

            self.manifest[item.attrib["id"]] = {

                "id": item.attrib.get("id", ""),

                "href": href,

                "path": path,

                "media-type": item.attrib.get(
                    "media-type",
                    ""
                ),

                "properties": item.attrib.get(
                    "properties",
                    ""
                ),

                "fallback": item.attrib.get(
                    "fallback",
                    ""
                )

            }
        
    def _build_spine(self):

        self.spine = []

        spine = self.opf_tree.find(
        "opf:spine",
        self.opf_ns
        )

        if spine is None:
            return

        for item in spine.findall(
            "opf:itemref",
            self.opf_ns            
        ):

            self.spine.append(
                item.attrib.get("idref")
            )
    def _load_opf(self):

        opf_xml = self.read_bytes(self.opf_path)

        self.opf_tree = ET.fromstring(opf_xml)

        self.opf_ns = {
        "opf": self.opf_tree.tag.split("}")[0][1:]
    }
    def _build_metadata(self):

        self.metadata = {}

        metadata_node = self.opf_tree.find(
        "opf:metadata",
        self.opf_ns
        )

        if metadata_node is None:
            return

        for child in metadata_node:

            tag = child.tag.split("}")[-1]

            text = child.text or ""

            self.metadata[tag] = text.strip()

    def _load_container(self):

        container_xml = self.read_bytes(
            "META-INF/container.xml"
        )

        root = ET.fromstring(container_xml)

        ns = {
        "c": "urn:oasis:names:tc:opendocument:xmlns:container"
    }

        rootfile = root.find(
        ".//c:rootfile",
        ns
    )

        self.opf_path = rootfile.attrib["full-path"]
    
    def _build_file_index(self):
        self.html_files = []
        self.css_files = []
        self.image_files = []
        self.font_files = []
        self.audio_files = []
        self.video_files = []
        self.used_images = set()
        self.used_css = set()
        self.used_fonts = set()

        self.nav_file = None
        self.ncx_file = None

        for item in self.manifest.values():

            media = item["media-type"]

            # ------------------------
            # HTML
            # ------------------------

            if media == "application/xhtml+xml":

                self.html_files.append(item)

                if "nav" in item.get("properties",""):

                    self.nav_file = item

            # ------------------------
            # CSS
            # ------------------------

            elif media == "text/css":

                self.css_files.append(item)

            # ------------------------
            # Images
            # ------------------------

            elif media.startswith("image/"):

                self.image_files.append(item)

            # ------------------------
            # Fonts
            # ------------------------

            elif (

                media.startswith("font/")

                or media in (

                    "application/font-sfnt",

                    "application/font-woff",

                    "application/font-woff2",

                    "application/vnd.ms-opentype",

                    "application/x-font-truetype",

                    "application/x-font-opentype",

                )

            ):

                self.font_files.append(item)

            # ------------------------
            # Audio
            # ------------------------

            elif media.startswith("audio/"):

                self.audio_files.append(item)

            # ------------------------
            # Video
            # ------------------------

            elif media.startswith("video/"):

                self.video_files.append(item)

            # ------------------------
            # NCX
            # ------------------------

            elif media == "application/x-dtbncx+xml":

                self.ncx_file = item



    
    def resolve_path(self, base_file: str, target: str) -> str:

        """
        base_file : file đang chứa link
            VD: OEBPS/Text/ch001.xhtml

        target : href hoặc src trong file
            VD: ../Images/cover.jpg

        return:
            OEBPS/Images/cover.jpg
        """

        return posixpath.normpath(
            posixpath.join(
                posixpath.dirname(base_file),
                target
            )
        )
    def read_bytes(self, path: str):

        return self.zip.read(path)


    def read_text(
        self,
        path: str,
        encoding="utf-8",
        errors="replace"
    ):

        return self.read_bytes(path).decode(
            encoding,
            errors=errors
    )


    def read_xml(self, path: str):

        if path not in self.xml_cache:

            self.xml_cache[path] = ET.fromstring(
                self.read_bytes(path)
            )

        return self.xml_cache[path]

    def get_html(self, item):

        path = item["path"]

        if path not in self.html_cache:

            self.html_cache[path] = HTMLDocument(

                self,

                item

            )

        return self.html_cache[path]