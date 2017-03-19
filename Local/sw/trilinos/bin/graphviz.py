import io
import os
import re
import sys
import errno
import codecs
import platform
import subprocess
PY2 = sys.version_info[0] == 2
if PY2:  # pragma: no cover
    text_type = unicode

    def iteritems(d):
        return d.iteritems()

    def makedirs(name, mode=0o777, exist_ok=False):
        try:
            os.makedirs(name, mode)
        except OSError:
            if not exist_ok or not os.path.isdir(name):
                raise


else:  # pragma: no cover
    text_type = str

    def iteritems(d):
        return iter(d.items())

    makedirs = os.makedirs

# tools.py

def mkdirs(filename, mode=0o777):
    """Recursively create directories up to the path of filename as needed."""
    dirname = os.path.dirname(filename)
    if not dirname:
        return
    makedirs(dirname, mode=mode, exist_ok=True)


def mapping_items(mapping, _iteritems=iteritems):
    """Return an iterator over the mapping items, sort if it's a plain dict.
    """
    if type(mapping) is dict:
        return iter(sorted(_iteritems(mapping)))
    return _iteritems(mapping)

# backend.py - execute rendering

ENGINES = set([  # http://www.graphviz.org/cgi-bin/man?dot
    'dot', 'neato', 'twopi', 'circo', 'fdp', 'sfdp', 'patchwork', 'osage',
])

FORMATS = set([  # http://www.graphviz.org/doc/info/output.html
    'bmp',
    'canon', 'dot', 'gv', 'xdot', 'xdot1.2', 'xdot1.4',
    'cgimage',
    'cmap',
    'eps',
    'exr',
    'fig',
    'gd', 'gd2',
    'gif',
    'gtk',
    'ico',
    'imap', 'cmapx',
    'imap_np', 'cmapx_np',
    'ismap',
    'jp2',
    'jpg', 'jpeg', 'jpe',
    'pct', 'pict',
    'pdf',
    'pic',
    'plain', 'plain-ext',
    'png',
    'pov',
    'ps',
    'ps2',
    'psd',
    'sgi',
    'svg', 'svgz',
    'tga',
    'tif', 'tiff',
    'tk',
    'vml', 'vmlz',
    'vrml',
    'wbmp',
    'webp',
    'xlib',
    'x11',
])

PLATFORM = platform.system().lower()

STARTUPINFO = None

if PLATFORM == 'windows':  # pragma: no cover
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = subprocess.SW_HIDE


def command(engine, format, filepath=None):
    """Return args list for subprocess.Popen and name of the rendered file."""
    if engine not in ENGINES:
        raise ValueError('unknown engine: %r' % engine)
    if format not in FORMATS:
        raise ValueError('unknown format: %r' % format)

    args, rendered = [engine, '-T%s' % format], None
    if filepath is not None:
        args.extend(['-O', filepath])
        rendered = '%s.%s' % (filepath, format)

    return args, rendered


def render(engine, format, filepath):
    """Render file with Graphviz engine into format,  return result filename.

    Args:
        engine: The layout commmand used for rendering ('dot', 'neato', ...).
        format: The output format used for rendering ('pdf', 'png', ...).
        filepath: Path to the DOT source file to render.
    Returns:
        The (possibly relative) path of the rendered file.
    Raises:
        RuntimeError: If the Graphviz executable is not found.
    """
    args, rendered = command(engine, format, filepath)

    try:
        subprocess.call(args, startupinfo=STARTUPINFO)
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise RuntimeError('failed to execute %r, '
                'make sure the Graphviz executables '
                'are on your systems\' path' % args)
        else:  # pragma: no cover
            raise

    return rendered


# lang.py - dot language creation helpers

"""Quote strings to be valid DOT identifiers, assemble attributes."""

# http://www.graphviz.org/doc/info/lang.html

ID = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*|-?(\.\d+|\d+(\.\d*)?))$')

KEYWORD = re.compile(r'((node)|(edge)|(graph)|(digraph)|(subgraph)|(strict))$', re.IGNORECASE)

HTML_STRING = re.compile(r'<.*?>$', re.DOTALL)

COMPASS = re.compile(r'((n)|(ne)|(e)|(se)|(s)|(sw)|(w)|(nw)|(c)|(_))$')


def quote(identifier,
          valid_id=ID.match, dot_keyword=KEYWORD.match, html=HTML_STRING.match):
    """Return DOT identifier from string, quote if needed.

    >>> quote('')
    '""'

    >>> quote('spam')
    'spam'

    >>> quote('spam spam')
    '"spam spam"'

    >>> quote('-4.2')
    '-4.2'

    >>> quote('.42')
    '.42'

    >>> quote('<<b>spam</b>>')
    '<<b>spam</b>>'
    """
    if html(identifier):
        pass
    elif not valid_id(identifier) or dot_keyword(identifier):
        return '"%s"' % identifier.replace('"', '\\"')
    return identifier


def quote_edge(identifier):
    """Return DOT edge statement node_id from string, quote if needed.

    >>> quote_edge('spam')
    'spam'

    >>> quote_edge('spam spam:eggs eggs')
    '"spam spam":"eggs eggs"'

    >>> quote_edge('spam:eggs:s')
    'spam:eggs:s'
    """
    node, _, rest = identifier.partition(':')
    parts = [quote(node)]
    if rest:
        port, _, compass = rest.partition(':')
        parts.append(quote(port))
        if compass:
            parts.append(compass)
    return ':'.join(parts)


def attributes(label=None, kwargs=None, attributes=None, raw=None):
    """Return assembled DOT attributes string.

    Sorts kwargs and attributes if they are plain dicts (to avoid
    unpredictable order from hash randomization in Python 3.3+).

    >>> attributes()
    ''

    >>> attributes('spam spam', kwargs={'eggs':'eggs', 'ham': 'ham ham'})
    ' [label="spam spam" eggs=eggs ham="ham ham"]'

    >>> attributes(kwargs={'spam': None, 'eggs': ''})
    ' [eggs=""]'
    """
    if label is None:
        result = []
    else:
        result = ['label=%s' % quote(label)]

    if kwargs:
        items = ['%s=%s' % (quote(k), quote(v))
            for k, v in mapping_items(kwargs) if v is not None]
        result.extend(items)

    if attributes:
        if hasattr(attributes, 'items'):
            attributes = mapping_items(attributes)
        items = ['%s=%s' % (quote(k), quote(v))
            for k, v in attributes if v is not None]
        result.extend(items)

    if raw:
        result.append(raw)

    if not result:
        return ''
    return ' [%s]' % ' '.join(result)

# files.py - save, render

"""Save DOT code objects, render with Graphviz dot"""

class Base(object):

    _format = 'pdf'
    _engine = 'dot'
    _encoding = 'utf-8'

    @property
    def format(self):
        """The output format used for rendering ('pdf', 'png', ...)."""
        return self._format

    @format.setter
    def format(self, format):
        format = format.lower()
        if format not in FORMATS:
            raise ValueError('unknown format: %r' % format)
        self._format = format

    @property
    def engine(self):
        """The layout commmand used for rendering ('dot', 'neato', ...)."""
        return self._engine

    @engine.setter
    def engine(self, engine):
        engine = engine.lower()
        if engine not in ENGINES:
            raise ValueError('unknown engine: %r' % engine)
        self._engine = engine

    @property
    def encoding(self):
        """The encoding for the saved source file."""
        return self._encoding

    @encoding.setter
    def encoding(self, encoding):
        if encoding is not None:
            codecs.lookup(encoding)
        self._encoding = encoding


class File(Base):

    directory = ''

    _default_extension = 'gv'

    def __init__(self, filename=None, directory=None, format=None, engine=None, encoding=None):
        if filename is None:
            name = getattr(self, 'name', None) or self.__class__.__name__
            filename = '%s.%s' % (name, self._default_extension)
        self.filename = filename

        if directory is not None:
            self.directory = directory

        if format is not None:
            self.format = format

        if engine is not None:
            self.engine = engine

        if encoding is not None:
            self.encoding = encoding

    @property
    def filepath(self):
        return os.path.join(self.directory, self.filename)

    def save(self, filename=None, directory=None):
        """Save the DOT source to file.

        Args:
            filename: Filename for saving the source (defaults to name + '.gv')
            directory: (Sub)directory for source saving and rendering.
        Returns:
            The (possibly relative) path of the saved source file.
        """
        if filename is not None:
            self.filename = filename
        if directory is not None:
            self.directory = directory

        filepath = self.filepath
        mkdirs(filepath)

        data = text_type(self.source)

        with io.open(filepath, 'w', encoding=self.encoding) as fd:
            fd.write(data)

        return filepath

    def render(self, filename=None, directory=None, cleanup=False):
        """Save the source to file and render with the Graphviz engine.

        Args:
            filename: Filename for saving the source (defaults to name + '.gv')
            directory: (Sub)directory for source saving and rendering.
            cleanup: Delete the source file after rendering.
        Returns:
            The (possibly relative) path of the rendered file.
        Raises:
            RuntimeError: If the Graphviz executable is not found.
        """
        filepath = self.save(filename, directory)

        rendered = render(self._engine, self._format, filepath)

        if cleanup:
            os.remove(filepath)

        return rendered

class Source(File):
    """Verbatim DOT source code string to be rendered by Graphviz.

    Args:
        source: The verbatim DOT source code string.
        filename: Filename for saving the source (defaults to name + '.gv').
        directory: (Sub)directory for source saving and rendering.
        format: Rendering output format ('pdf', 'png', ...).
        engine: Layout command used ('dot', 'neato', ...).
        encoding: Encoding for saving the source.

    .. note::
        All parameters except source are optional and can be changed under
        their corresponding attribute name after instance creation.
    """

    def __init__(self, source, filename=None, directory=None, format=None, engine=None, encoding=None):
        super(Source, self).__init__(filename, directory, format, engine, encoding)
        self.source = source

# dot.py - create dot code

r"""Assemble DOT source code objects.

>>> dot = Graph(comment=u'M\xf8nti Pyth\xf8n ik den H\xf8lie Grailen')

>>> dot.node(u'M\xf8\xf8se')
>>> dot.node('trained_by', u'trained by')
>>> dot.node('tutte', u'TUTTE HERMSGERVORDENBROTBORDA')

>>> dot.edge(u'M\xf8\xf8se', 'trained_by')
>>> dot.edge('trained_by', 'tutte')

>>> dot.node_attr['shape'] = 'rectangle'

>>> print(dot.source.replace(u'\xf8', '0'))  #doctest: +NORMALIZE_WHITESPACE
// M0nti Pyth0n ik den H0lie Grailen
graph {
    node [shape=rectangle]
        "M00se"
        trained_by [label="trained by"]
        tutte [label="TUTTE HERMSGERVORDENBROTBORDA"]
            "M00se" -- trained_by
            trained_by -- tutte
}

'test-output/m00se.gv.pdf'
"""

class Dot(File):
    """Assemble, save, and render DOT source code."""

    _comment = '// %s'
    _subgraph = 'subgraph %s{'
    _node = '\t%s%s'
    _tail = '}'

    quote = staticmethod(quote)
    quote_edge = staticmethod(quote_edge)
    attributes = staticmethod(attributes)

    def __init__(self, name=None, comment=None,
            filename=None, directory=None,
            format=None, engine=None, encoding=None,
            graph_attr=None, node_attr=None, edge_attr=None, body=None,
            strict=False):

        self.name = name
        self.comment = comment

        super(Dot, self).__init__(filename, directory, format, engine, encoding)

        self.graph_attr = dict(graph_attr) if graph_attr is not None else {}
        self.node_attr = dict(node_attr) if node_attr is not None else {}
        self.edge_attr = dict(edge_attr) if edge_attr is not None else {}

        self.body = list(body) if body is not None else []

        self.strict = strict

    def __iter__(self, subgraph=False):
        """Yield the DOT source code line by line."""
        if self.comment:
            yield self._comment % self.comment

        head = self._subgraph if subgraph else self._head
        if self.strict:
            head = 'strict %s' % head
        yield head % (self.quote(self.name) + ' ' if self.name else '')

        styled = False
        for kw in ('graph', 'node', 'edge'):
            attr = getattr(self, '%s_attr' % kw)
            if attr:
                styled = True
                yield '\t%s%s' % (kw, self.attributes(None, attr))

        indent = '\t' * styled
        for line in self.body:
            yield indent + line

        yield self._tail

    def __str__(self):
        return '\n'.join(self)

    source = property(__str__, doc='The DOT source code as string.')

    def node(self, name, label=None, _attributes=None, **attrs):
        """Create a node.

        Args:
            name: Unique identifier for the node inside the source.
            label: Caption to be displayed (defaults to the node name).
            attrs: Any additional node attributes (must be strings).
        """
        name = self.quote(name)
        attributes = self.attributes(label, attrs, _attributes)
        self.body.append(self._node % (name, attributes))

    def edge(self, tail_name, head_name, label=None, _attributes=None, **attrs):
        """Create an edge between two nodes.

        Args:
            tail_name: Start node identifier.
            head_name: End node identifier.
            label: Caption to be displayed near the edge.
            attrs: Any additional edge attributes (must be strings).
        """
        tail_name = self.quote_edge(tail_name)
        head_name = self.quote_edge(head_name)
        attributes = self.attributes(label, attrs, _attributes)
        edge = self._edge % (tail_name, head_name, attributes)
        self.body.append(edge)

    def edges(self, tail_head_iter):
        """Create a bunch of edges.

        Args:
            tail_head_iter: Iterable of (tail_name, head_name) pairs.
        """
        edge = self._edge_plain
        quote = self.quote_edge
        self.body.extend(edge % (quote(t), quote(h))
            for t, h in tail_head_iter)

    def attr(self, kw, _attributes=None, **attrs):
        """Add a graph/node/edge attribute statement.

        Args:
            kw: Attributes target ('graph', 'node', or 'edge').
            attrs: Attributes to be set (must be strings, may be empty).
        """
        if kw.lower() not in ('graph', 'node', 'edge'):
            raise ValueError('attr statement must target graph, node, or edge: '
                '%r' % kw)
        if _attributes or attrs:
            line = '\t%s%s' % (kw, self.attributes(None, attrs, _attributes))
            self.body.append(line)

    def subgraph(self, graph):
        """Add the current content of the given graph as subgraph.

        Args:
            graph: An instance of the same kind (Graph, Digraph)
                   as the current graph.
        """
        if not isinstance(graph, self.__class__):
            raise ValueError('%r cannot add subgraphs of different kind: %r '
                % (self, graph))
        lines = ['\t' + line for line in graph.__iter__(subgraph=True)]
        self.body.extend(lines)


class Graph(Dot):
    """Graph source code in the DOT language.

    Args:
        name: Graph name used in the source code.
        comment: Comment added to the first line of the source.
        filename: Filename for saving the source (defaults to name + '.gv').
        directory: (Sub)directory for source saving and rendering.
        format: Rendering output format ('pdf', 'png', ...).
        engine: Layout command used ('dot', 'neato', ...).
        encoding: Encoding for saving the source.
        graph_attr: Mapping of (attribute, value) pairs for the graph.
        node_attr: Mapping of (attribute, value) pairs set for all nodes.
        edge_attr: Mapping of (attribute, value) pairs set for all edges.
        body: Iterable of lines to add to the graph body.
        strict: Rendering should merge multi-edges (default: False).

    .. note::
        All parameters are optional and can be changed under their
        corresponding attribute name after instance creation.
    """

    _head = 'graph %s{'
    _edge = '\t\t%s -- %s%s'
    _edge_plain = '\t\t%s -- %s'


class Digraph(Dot):
    """Directed graph source code in the DOT language."""

    __doc__ += Graph.__doc__.partition('.')[2]

    _head = 'digraph %s{'
    _edge = '\t\t%s -> %s%s'
    _edge_plain = '\t\t%s -> %s'
