import xml.etree.ElementTree as ET


class HTMLDocument:

    def __init__(self, ctx, item):

        self.ctx = ctx

        self.item = item

        self.path = item["path"]

        self.root = ctx.read_xml(self.path)

        # ----------------------------
        # Cache
        # ----------------------------

        self._title = None
        self._language = None

        self._images = None
        self._links = None
        self._stylesheets = None
        self._headings = None

        self._meta = None
        self._scripts = None
        self._forms = None
        self._iframes = None
        self._objects = None
        self._embeds = None

        self._audio = None
        self._video = None

        self._ids = None

    # -------------------------------------------------

    def find(self, xpath):

        return self.root.find(xpath)

    def findall(self, xpath):

        return self.root.findall(xpath)

    def iter(self, tag=None):

        return self.root.iter(tag)

    # -------------------------------------------------

    @property
    def title(self):

        if self._title is None:

            node = self.root.find(".//{*}title")

            self._title = (

                node.text.strip()

                if node is not None and node.text

                else ""

            )

        return self._title

    # -------------------------------------------------

    @property
    def language(self):

        if self._language is None:

            self._language = (

                self.root.attrib.get(

                    "{http://www.w3.org/XML/1998/namespace}lang"

                )

                or self.root.attrib.get("lang")

                or ""

            )

        return self._language

    # -------------------------------------------------

    @property
    def images(self):

        if self._images is None:

            self._images = list(

                self.root.iter("{*}img")

            )

        return self._images

    # -------------------------------------------------

    @property
    def links(self):

        if self._links is None:

            self._links = list(

                self.root.iter("{*}a")

            )

        return self._links

    # -------------------------------------------------

    @property
    def stylesheets(self):

        if self._stylesheets is None:

            result = []

            for node in self.root.iter("{*}link"):

                if node.attrib.get("rel") == "stylesheet":

                    result.append(node)

            self._stylesheets = result

        return self._stylesheets

    # -------------------------------------------------

    @property
    def headings(self):

        if self._headings is None:

            result = []

            for level in range(1, 7):

                result.extend(

                    self.root.iter(f"{{*}}h{level}")

                )

            self._headings = result

        return self._headings

    # -------------------------------------------------

    @property
    def meta(self):

        if self._meta is None:

            self._meta = list(

                self.root.iter("{*}meta")

            )

        return self._meta

    # -------------------------------------------------

    @property
    def scripts(self):

        if self._scripts is None:

            self._scripts = list(

                self.root.iter("{*}script")

            )

        return self._scripts

    # -------------------------------------------------

    @property
    def forms(self):

        if self._forms is None:

            self._forms = list(

                self.root.iter("{*}form")

            )

        return self._forms

    # -------------------------------------------------

    @property
    def iframes(self):

        if self._iframes is None:

            self._iframes = list(

                self.root.iter("{*}iframe")

            )

        return self._iframes

    # -------------------------------------------------

    @property
    def objects(self):

        if self._objects is None:

            self._objects = list(

                self.root.iter("{*}object")

            )

        return self._objects

    # -------------------------------------------------

    @property
    def embeds(self):

        if self._embeds is None:

            self._embeds = list(

                self.root.iter("{*}embed")

            )

        return self._embeds

    # -------------------------------------------------

    @property
    def audio(self):

        if self._audio is None:

            self._audio = list(

                self.root.iter("{*}audio")

            )

        return self._audio

    # -------------------------------------------------

    @property
    def video(self):

        if self._video is None:

            self._video = list(

                self.root.iter("{*}video")

            )

        return self._video

    # -------------------------------------------------

    @property
    def ids(self):

        if self._ids is None:

            self._ids = []

            for node in self.root.iter():

                value = node.attrib.get("id")

                if value:

                    self._ids.append(value)

        return self._ids