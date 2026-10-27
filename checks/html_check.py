import posixpath
import xml.etree.ElementTree as ET

from checks.base_checker import BaseChecker
from models import CheckResult

class HTMLChecker(BaseChecker):

    name = "HTML"

    def check(self, ctx):
        results = []

        for html in ctx.html_files:
            html_path = html["path"]

            try:

                data = ctx.read_bytes(
            html_path
                )

            except Exception:

                results.append(

                    CheckResult(

                        self.name,

                        False,

                        "Cannot read XHTML",

                        html_path

                    )

                )

                continue

            try:

                text = data.decode("utf-8", errors="ignore")

                # XML không hiểu entity HTML này
                text = text.replace("&nbsp;", "&#160;")

                root = ET.fromstring(text)

            except ET.ParseError as e:

                results.append(

                    CheckResult(

                        self.name,

                        False,

                        f"XML Parse Error : {e}",

                        html_path

                    )

                )

                continue

            # -------------------------
            # Image
            # -------------------------

            results.extend(

                self._check_images(

                    ctx,

                    html_path,

                    root

                )

            )

            # -------------------------
            # CSS
            # -------------------------

            results.extend(

                self._check_css(
                    ctx,
                    html_path,
                    root
                )

            )

            # -------------------------
            # Hyperlink
            # -------------------------

            results.extend(

                self._check_links(
                    ctx,
                    html_path,
                    root
                )

            )

            results.extend(
            
                self._check_anchor(
                    ctx,
                    html_path,
                    root
                )
            )
            
            results.extend(
                
                self._check_duplicate_ids(
                    ctx,
                    html_path,
                    root
                )
            )

            results.extend(

                self._check_title(
                    ctx,
                    html_path,
                    root
                )
            )

        if not results:

            results.append(

                CheckResult(

                    self.name,

                    True,

                    ""

                )

            )

        return results

    def _check_images(self, ctx, html_file, root):

        results = []

        for node in root.iter():

            if node.tag.split("}")[-1] != "img":
                continue

            src = node.attrib.get("src")

            if not src:
                continue

            resolved = ctx.resolve_path(
                html_file,
                src
            )

            ctx.used_images.add(resolved)

            if not ctx.exists(resolved):

                results.append(

                    self.error(

                        "Missing image",

                        html_file,

                        src

                    )

                )

        return results

    def _check_css(self, ctx, html_file, root):

        results = []

        for node in root.iter():

            tag = node.tag.split("}")[-1]

            if tag != "link":
                continue

            href = node.attrib.get("href")

            if not href:
                continue

            full_path = ctx.resolve_path(
                html_file,
                href
            )
            
            ctx.used_css.add(full_path)

            if not ctx.exists(full_path):

                results.append(

                    CheckResult(

                        self.name,

                        False,

                        "Missing CSS",

                        html_file,

                        href

                    )

                )

        return results
    
    def _check_links(self, ctx, html_file, root):

        results = []

        for node in root.iter():

            tag = node.tag.split("}")[-1]

            if tag != "a":
                continue

            href = node.attrib.get("href")

            if not href:
                continue

            if href.startswith("#"):
                continue

            if "://" in href:
                continue

            target = href.split("#")[0]

            if not target:
                continue

            full_path = ctx.resolve_path(
                html_file,
                target
            )

            if not ctx.exists(full_path):

                results.append(

                    CheckResult(

                        self.name,

                        False,

                        "Broken hyperlink",

                        html_file,

                        href

                    )

                )

        return results
    
    def _collect_ids(self, root):

        ids = set()

        for node in root.iter():

            value = node.attrib.get("id")

            if value:

                ids.add(value)

        return ids
    
    def _check_anchor(self, ctx, html_file, root):

        results = []

        for node in root.iter():

            tag = node.tag.split("}")[-1]

            if tag != "a":
                continue

            href = node.attrib.get("href")

            if not href:
                continue

            if "#" not in href:
                continue

            file_part, anchor = href.split("#", 1)

            # ---------------------------------
            # Anchor trong chính file
            # ---------------------------------

            if file_part == "":

                ids = self._collect_ids(root)

                if anchor not in ids:

                    results.append(

                        CheckResult(

                            self.name,

                            False,

                            "Broken anchor",

                            html_file,

                            href

                        )

                    )

                continue

            # ---------------------------------
            # Anchor sang file khác
            # ---------------------------------

            target = ctx.resolve_path(
                html_file,
                file_part
            )

            if not ctx.exists(target):

                continue

            try:

                target_root = ctx.read_xml(target)

            except Exception:

                continue

            ids = self._collect_ids(target_root)

            if anchor not in ids:

                results.append(

                    CheckResult(

                        self.name,

                        False,

                        "Broken anchor",

                        html_file,

                        href

                    )

                )

        return results
    
    def _check_duplicate_ids(self, ctx, html_file, root):

        results = []

        used = set()

        for node in root.iter():

            node_id = node.attrib.get("id")

            if not node_id:
                continue

            if node_id in used:

                results.append(

                    CheckResult(

                        self.name,

                        False,

                        "Duplicate id",

                        html_file,

                        node_id

                    )

                )

            else:

                used.add(node_id)

        return results
    
    def _check_title(self, ctx, html_file, root):

        results = []
        title = None

        for node in root.iter():

            if node.tag.split("}")[-1] == "title":

                title = node

                break

        if title is None:
            results.append(
                CheckResult(
                    self.name,
                    False,
                    "Missing title",
                    html_file
                )

            )

        elif not (title.text or "").strip():
            results.append(
                CheckResult(
                    self.name,
                    False,

                    "Empty title",

                    html_file

                )

            )

        return results