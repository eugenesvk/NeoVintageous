from __future__ import annotations

import dataclasses
import re
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from . import printing, t

if t.TYPE_CHECKING:
    VT = t.TypeVar("VT")
    LooseEntry = tuple[str | None, t.Any]


@dataclass
class Document:
    nodes: list[Node] = dataclasses.field(default_factory=list)
    printConfig: t.PrintConfig | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        config = config or self.printConfig or printing.defaults
        s = ""
        for node in self.nodes:
            node = toKdlNode(node)
            s += node.print(config, 0)
        if s == "":
            # always end a kdl doc with a newline
            s = "\n"
        return s

    @t.overload
    def get(self, key: t.NodeKey) -> Node | None:  # noqa: F811
        ...

    @t.overload
    def get(self, key: t.NodeKey, default: VT) -> Node | VT:  # noqa: F811
        ...

    def get(  # noqa: F811
        self,
        key: t.NodeKey,
        default: VT | None = None,
    ) -> Node | VT | None:
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key: t.NodeKey) -> Node:
        for node in self.nodes:
            if node.matchesKey(key):
                return node
        raise KeyError(key)

    def getAll(
        self,
        key: t.NodeKey,
    ) -> t.Iterable[Node]:
        for node in self.nodes:
            if nodeMatchesKey(node, key):
                yield node

    def __str__(self) -> str:
        return self.print()


@dataclass
class Node:
    name: str
    tag: str | None = None
    entries: list[LooseEntry] = dataclasses.field(default_factory=list)
    nodes: list[Node] = dataclasses.field(default_factory=list)

    def print(
        self,
        config: t.PrintConfig | None = None,
        indentLevel: int = 0,
    ) -> str:
        if config is None:
            config = printing.defaults

        s = config.indent * indentLevel

        if self.tag is not None:
            s += f"({printIdent(self.tag)})"

        s += printIdent(self.name)

        entries: t.Iterable[tuple[str | None, t.Any]]
        if config.sortEntries:
            entries = sorted(self.entries, key=lambda x: x[0] or "")
        else:
            entries = self.entries
        for name, value in entries:
            value = toKdlValue(value)
            if not config.printNulls and isinstance(value, Null):
                continue
            if name is None:
                s += f" {value.print(config)}"
            else:
                s += f" {printIdent(name)}={value.print(config)}"

        if self.nodes:
            childrenText = ""
            for child in self.nodes:
                child = toKdlNode(child)
                childrenText += child.print(config=config, indentLevel=indentLevel + 1)
            if childrenText:
                s += " {\n"
                s += childrenText
                s += config.indent * indentLevel + "}"
        if config.semicolons:
            s += ";\n"
        else:
            s += "\n"
        return s

    @t.overload
    def get(self, key: t.NodeKey) -> Node | None:  # noqa: F811
        ...

    @t.overload
    def get(self, key: t.NodeKey, default: VT) -> Node | VT:  # noqa: F811
        ...

    def get(  # noqa: F811
        self,
        key: t.NodeKey,
        default: VT | None = None,
    ) -> Node | VT | None:
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key: t.NodeKey) -> Node:
        for node in self.nodes:
            if node.matchesKey(key):
                return node
        raise KeyError(key)

    def getAll(
        self,
        key: t.NodeKey,
    ) -> t.Iterable[Node]:
        for node in self.nodes:
            if nodeMatchesKey(node, key):
                yield node

    def matchesKey(self, key: t.NodeKey) -> bool:
        return nodeMatchesKey(self, key)

    def getEntries(self, key: t.ValueKey) -> t.Iterable[LooseEntry]:
        for name, val in self.entries:
            if valueMatchesKey(val, key):
                yield name, val

    def getProps(self, key: t.ValueKey) -> t.Iterable[tuple[str, t.Any]]:
        for name, val in self.entries:
            if name is not None and valueMatchesKey(val, key):
                yield name, val

    def getArgs(self, key: t.ValueKey) -> t.Iterable[t.Any]:
        for name, val in self.entries:
            if name is None and valueMatchesKey(val, key):
                yield val

    def __str__(self) -> str:
        return self.print()

    def ttt(self) -> str:
        print('ttt')


class Value(metaclass=ABCMeta):
    value: t.Any
    tag: str | None

    @abstractmethod
    def print(self, config: t.PrintConfig | None = None) -> str:
        pass

    def matchesKey(self, key: t.ValueKey) -> bool:
        return valueMatchesKey(self, key)


@dataclass
class ExactValue(Value):
    # Not produced by anything in the parser,
    # but used when a native type needs a precise output
    # not captured by the native semantics,
    # like precise number formatting.
    # .chars *must* be a valid KDL value
    chars: str
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        return printTag(self.tag) + self.chars

    def __str__(self) -> str:
        return self.print()


class Numberish(Value, metaclass=ABCMeta):
    pass


@dataclass
class Binary(Numberish):
    value: int
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        s = printTag(self.tag)
        if config.respectRadix:
            s += bin(self.value)
        else:
            s += str(self.value)
        return s

    def __str__(self) -> str:
        return self.print()


@dataclass
class Octal(Numberish):
    value: int
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        s = printTag(self.tag)
        if config.respectRadix:
            s += oct(self.value)
        else:
            s += str(self.value)
        return s

    def __str__(self) -> str:
        return self.print()


@dataclass
class Decimal(Numberish):
    mantissa: int | float
    exponent: int = 0
    tag: str | None = None

    @property
    def value(self) -> float:
        return self.mantissa * (10.0**self.exponent)

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        s = printTag(self.tag) + str(self.mantissa)
        if self.exponent != 0:
            s += config.exponent
            if self.exponent > 0:
                s += "+"
            s += str(self.exponent)
        return s

    def __str__(self) -> str:
        return self.print()


@dataclass
class Infinity(Numberish):
    value: float
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        if self.value == float("inf"):
            return printTag(self.tag) + "#inf"
        else:
            return printTag(self.tag) + "#-inf"

    def __str__(self) -> str:
        return self.print()


@dataclass
class NaN(Numberish):
    value: float = float("nan")
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        return printTag(self.tag) + "#nan"

    def __str__(self) -> str:
        return self.print()


@dataclass
class Hex(Numberish):
    value: int
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        s = printTag(self.tag)
        if config.respectRadix:
            s += hex(self.value)
        else:
            s += str(self.value)
        return s

    def __str__(self) -> str:
        return self.print()


@dataclass
class Bool(Value):
    value: bool
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        if self.value:
            return printTag(self.tag) + "#true"
        else:
            return printTag(self.tag) + "#false"

    def __str__(self) -> str:
        return self.print()


@dataclass
class Null(Value):
    tag: str | None = None

    @property
    def value(self) -> None:
        return None

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        return printTag(self.tag) + "#null"

    def __str__(self) -> str:
        return self.print()


class Stringish(Value, metaclass=ABCMeta):
    pass


@dataclass
class RawString(Stringish):
    value: str
    tag: str | None = None

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        if config.respectStringType:
            hashes = "#" * findRequiredHashCount(self.value)
            return f'{printTag(self.tag)}r{hashes}"{self.value}"{hashes}'
        else:
            return f'{printTag(self.tag)}"{escapedFromRaw(self.value)}"'

    def __str__(self) -> str:
        return self.print()


def findRequiredHashCount(chars: str) -> int:
    for i in range(0, 100):
        ender = '"' + ("#" * i)
        if ender not in chars:
            return i
    assert False, "A raw string requires more than 100 hashes???"


@dataclass
class String(Stringish):
    value: str
    tag: str | None = None
    multiline: bool = False

    def print(self, config: t.PrintConfig | None = None) -> str:
        if config is None:
            config = printing.defaults
        if self.multiline:
            return ""
        elif isBareIdent(self.value):
            return printTag(self.tag) + self.value
        else:
            return f'{printTag(self.tag)}"{escapedFromRaw(self.value)}"'

    def __str__(self) -> str:
        return self.print()


def toKdlNode(val: t.Any) -> Node:
    if isinstance(val, Node):
        return val
    if not callable(getattr(val, "to_kdl", None)):
        msg = f"Can't convert object to KDL for serialization. Got:\n{val!r}"
        raise Exception(
            msg,
        )
    node = val.to_kdl()
    if not isinstance(node, Node):
        msg = f"Expected object to convert to KDL Node. Got:\n{val!r}"
        raise Exception(msg)
    return node


def toKdlValue(val: t.Any) -> t.KDLValue:
    """
    Converts any KDLish value (a KDLValue, a primitive,
    an object corresponding to a built-in tag,
    or an object with .to_kdl() that returns one of the above)
    into a KDLValue
    """
    import base64
    import datetime
    import decimal
    import ipaddress
    import urllib
    import uuid

    if isinstance(val, Value):
        return val
    if val is None:
        return Null()
    if isinstance(val, bool):
        return Bool(val)
    if isinstance(val, str):
        return String(val)
    if isinstance(val, (int, float)):
        return Decimal(val)
    if isinstance(val, decimal.Decimal):
        return String(str(val), "decimal")
    if isinstance(val, datetime.datetime):
        return String(val.isoformat(), "date-time")
    if isinstance(val, datetime.time):
        return String(val.isoformat(), "time")
    if isinstance(val, datetime.date):
        return String(val.isoformat(), "date")
    if isinstance(val, ipaddress.IPv4Address):
        return String(str(val), "ipv4")
    if isinstance(val, ipaddress.IPv6Address):
        return String(str(val), "ipv6")
    if isinstance(val, urllib.parse.ParseResult):
        return String(urllib.parse.urlunparse(val), "url")
    if isinstance(val, uuid.UUID):
        return String(str(val), "uuid")
    if isinstance(val, re.Pattern):
        return RawString(val.pattern, "regex")
    if isinstance(val, bytes):
        return String(base64.b64encode(val).decode("utf-8"), "base-64")

    if not callable(getattr(val, "to_kdl", None)):
        msg = f"Can't convert object to KDL for serialization. Got:\n{val!r}"
        raise Exception(
            msg,
        )

    convertedVal = val.to_kdl()
    if isKdlishValue(convertedVal):
        return toKdlValue(convertedVal)
    else:
        msg = f"Expected object to convert to KDL value or compatible primitive. Got:\n{val!r}"
        raise Exception(msg)


def isKdlishValue(val: t.Any) -> bool:
    import datetime
    import decimal
    import ipaddress
    import urllib
    import uuid

    if val is None:
        return True
    return isinstance(
        val,
        (
            str,
            int,
            float,
            bool,
            decimal.Decimal,
            datetime.time,
            datetime.date,
            datetime.datetime,
            ipaddress.IPv4Address,
            ipaddress.IPv6Address,
            urllib.parse.ParseResult,
            uuid.UUID,
            re.Pattern,
            bytes,
            Value,
        ),
    )


def printTag(tag: str | None) -> str:
    if tag is not None:
        return f"({printIdent(tag)})"
    else:
        return ""


def nodeMatchesKey(node: t.Any, key: t.NodeKey) -> bool:
    if not isinstance(node, Node):
        node = node.to_kdl()
    if isinstance(key, tuple):
        tagKey, nameKey = key
        return tagMatchesKey(node.tag, tagKey) and nameMatchesKey(node.name, nameKey)
    else:
        return nameMatchesKey(node.name, key)


def valueMatchesKey(value: t.Any, key: t.ValueKey) -> bool:
    # Need to allow for both Value and values that were converted to other types
    # non-Value objects are untagged, by definition
    if isinstance(value, Value):
        tag = value.tag
    else:
        tag = None
    if isinstance(key, tuple):
        tagKey, typeKey = key
        return tagMatchesKey(tag, tagKey) and typeMatchesKey(value, typeKey)
    else:
        return tagMatchesKey(tag, key)


def tagMatchesKey(val: str | None, key: t.TagKey) -> bool:
    if key == Ellipsis:
        return True
    elif key is None:
        return val is None
    elif isinstance(key, str):
        return val == key
    elif isinstance(key, re.Pattern):
        if val is None:
            return False
        return bool(key.match(val))
    elif callable(key):
        return bool(key(val))
    msg = f"Invalid TagKey {key!r}"
    raise Exception(msg)


def nameMatchesKey(val: str, key: t.NameKey) -> bool:
    if key == Ellipsis:
        return True
    elif key is None:
        return True
    elif isinstance(key, str):
        return val == key
    elif isinstance(key, re.Pattern):
        return bool(key.match(val))
    elif callable(key):
        return bool(key(val))
    msg = f"Invalid NameKey {key!r}"
    raise Exception(msg)


def typeMatchesKey(val: Value, key: t.TypeKey) -> bool:
    if key == Ellipsis:
        return True
    try:
        return isinstance(val, t.cast("t._ClassInfo", key))
    except Exception as e:
        msg = f"Invalid TypeKey {key!r}"
        raise Exception(msg) from e


def escapedFromRaw(chars: str) -> str:
    return (
        chars.replace("\\", "\\\\")
        .replace('"', '\\"')
        # don't escape a forward slash when printing
        .replace("\b", "\\b")
        .replace("\f", "\\f")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def printIdent(chars: str) -> str:
    if isBareIdent(chars):
        return chars
    return f'"{escapedFromRaw(chars)}"'


def isBareIdent(chars: str) -> bool:
    if not chars:
        return False
    if any(not isIdentChar(x) for x in chars):
        return False
    if chars[0] in "0123456789":
        return False
    if len(chars) > 1 and chars[0] in "+-" and chars[1] in "0123456789":
        return False
    if chars.lower() in ("true", "false", "null", "inf", "-inf", "nan"):
        return False
    return True


def isIdentChar(ch: str) -> bool:
    if not ch:
        return False
    # reserved characters
    if ch in r"(){}[]/\"#;=":
        return False
    if isWSChar(ch):
        return False
    if isNewline(ch):
        return False
    if isDisallowedLiteral(ch):
        return False
    return True


def isDisallowedLiteral(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    if 0x0 <= cp <= 0x08:
        return True
    if 0xE <= cp <= 0x1F:
        return True
    if cp == 0x7F:
        return True
    if 0xD800 <= cp <= 0xDFFF:
        return True
    if 0x200E <= cp <= 0x200F:
        return True
    if 0x202A <= cp <= 0x202E:
        return True
    if 0x2066 <= cp <= 0x2069:
        return True
    if cp == 0xFEFF:
        return True

    return False


def isWSChar(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    if cp in (0x9, 0xB, 0x20, 0xA0, 0x1680):
        return True
    if 0x2000 <= cp <= 0x200A:
        return True
    if cp in (0x202F, 0x205F, 0x3000):
        return True
    return False


def isNewline(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    if cp in (0xA, 0xD, 0x85, 0xC, 0x2028, 0x2029):
        return True
    return False
