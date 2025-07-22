import dataclasses
import enum
import typing

import fltk.fegen.pyrt.terminalsrc


@dataclasses.dataclass
class Formatter:
    class Label(enum.Enum):
        STATEMENT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Statement", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Statement", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[typing.Union["Statement", "Trivia"]], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Statement", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_statement(self, child: "Statement") -> None:
        self.children.append((Formatter.Label.STATEMENT, child))

    def extend_statement(self, children: typing.Iterable["Statement"]) -> None:
        self.children.extend((Formatter.Label.STATEMENT, child) for child in children)

    def children_statement(self) -> typing.Iterator["Statement"]:
        return (typing.cast("Statement", child) for label, child in self.children if label == Formatter.Label.STATEMENT)

    def child_statement(self) -> "Statement":
        children = list(self.children_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_statement(self) -> typing.Optional["Statement"]:
        children = list(self.children_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Statement:
    class Label(enum.Enum):
        AFTER = enum.auto()
        BEFORE = enum.auto()
        DEFAULT = enum.auto()
        GROUP = enum.auto()
        JOIN = enum.auto()
        NEST = enum.auto()
        OMIT = enum.auto()
        RENDER = enum.auto()
        RULE_CONFIG = enum.auto()
        TRIVIA_PRESERVE = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[
            Label | None,
            typing.Union[
                "After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render", "RuleConfig", "TriviaPreserve"
            ],
        ]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: typing.Union[
            "After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render", "RuleConfig", "TriviaPreserve"
        ],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[
            typing.Union[
                "After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render", "RuleConfig", "TriviaPreserve"
            ]
        ],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[
        Label | None,
        typing.Union[
            "After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render", "RuleConfig", "TriviaPreserve"
        ],
    ]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_after(self, child: "After") -> None:
        self.children.append((Statement.Label.AFTER, child))

    def extend_after(self, children: typing.Iterable["After"]) -> None:
        self.children.extend((Statement.Label.AFTER, child) for child in children)

    def children_after(self) -> typing.Iterator["After"]:
        return (typing.cast("After", child) for label, child in self.children if label == Statement.Label.AFTER)

    def child_after(self) -> "After":
        children = list(self.children_after())
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> typing.Optional["After"]:
        children = list(self.children_after())
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_before(self, child: "Before") -> None:
        self.children.append((Statement.Label.BEFORE, child))

    def extend_before(self, children: typing.Iterable["Before"]) -> None:
        self.children.extend((Statement.Label.BEFORE, child) for child in children)

    def children_before(self) -> typing.Iterator["Before"]:
        return (typing.cast("Before", child) for label, child in self.children if label == Statement.Label.BEFORE)

    def child_before(self) -> "Before":
        children = list(self.children_before())
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> typing.Optional["Before"]:
        children = list(self.children_before())
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_default(self, child: "Default") -> None:
        self.children.append((Statement.Label.DEFAULT, child))

    def extend_default(self, children: typing.Iterable["Default"]) -> None:
        self.children.extend((Statement.Label.DEFAULT, child) for child in children)

    def children_default(self) -> typing.Iterator["Default"]:
        return (typing.cast("Default", child) for label, child in self.children if label == Statement.Label.DEFAULT)

    def child_default(self) -> "Default":
        children = list(self.children_default())
        if (n := len(children)) != 1:
            msg = f"Expected one default child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_default(self) -> typing.Optional["Default"]:
        children = list(self.children_default())
        if (n := len(children)) > 1:
            msg = f"Expected at most one default child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: "Group") -> None:
        self.children.append((Statement.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable["Group"]) -> None:
        self.children.extend((Statement.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator["Group"]:
        return (typing.cast("Group", child) for label, child in self.children if label == Statement.Label.GROUP)

    def child_group(self) -> "Group":
        children = list(self.children_group())
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> typing.Optional["Group"]:
        children = list(self.children_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join(self, child: "Join") -> None:
        self.children.append((Statement.Label.JOIN, child))

    def extend_join(self, children: typing.Iterable["Join"]) -> None:
        self.children.extend((Statement.Label.JOIN, child) for child in children)

    def children_join(self) -> typing.Iterator["Join"]:
        return (typing.cast("Join", child) for label, child in self.children if label == Statement.Label.JOIN)

    def child_join(self) -> "Join":
        children = list(self.children_join())
        if (n := len(children)) != 1:
            msg = f"Expected one join child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join(self) -> typing.Optional["Join"]:
        children = list(self.children_join())
        if (n := len(children)) > 1:
            msg = f"Expected at most one join child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: "Nest") -> None:
        self.children.append((Statement.Label.NEST, child))

    def extend_nest(self, children: typing.Iterable["Nest"]) -> None:
        self.children.extend((Statement.Label.NEST, child) for child in children)

    def children_nest(self) -> typing.Iterator["Nest"]:
        return (typing.cast("Nest", child) for label, child in self.children if label == Statement.Label.NEST)

    def child_nest(self) -> "Nest":
        children = list(self.children_nest())
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> typing.Optional["Nest"]:
        children = list(self.children_nest())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_omit(self, child: "Omit") -> None:
        self.children.append((Statement.Label.OMIT, child))

    def extend_omit(self, children: typing.Iterable["Omit"]) -> None:
        self.children.extend((Statement.Label.OMIT, child) for child in children)

    def children_omit(self) -> typing.Iterator["Omit"]:
        return (typing.cast("Omit", child) for label, child in self.children if label == Statement.Label.OMIT)

    def child_omit(self) -> "Omit":
        children = list(self.children_omit())
        if (n := len(children)) != 1:
            msg = f"Expected one omit child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_omit(self) -> typing.Optional["Omit"]:
        children = list(self.children_omit())
        if (n := len(children)) > 1:
            msg = f"Expected at most one omit child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_render(self, child: "Render") -> None:
        self.children.append((Statement.Label.RENDER, child))

    def extend_render(self, children: typing.Iterable["Render"]) -> None:
        self.children.extend((Statement.Label.RENDER, child) for child in children)

    def children_render(self) -> typing.Iterator["Render"]:
        return (typing.cast("Render", child) for label, child in self.children if label == Statement.Label.RENDER)

    def child_render(self) -> "Render":
        children = list(self.children_render())
        if (n := len(children)) != 1:
            msg = f"Expected one render child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_render(self) -> typing.Optional["Render"]:
        children = list(self.children_render())
        if (n := len(children)) > 1:
            msg = f"Expected at most one render child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule_config(self, child: "RuleConfig") -> None:
        self.children.append((Statement.Label.RULE_CONFIG, child))

    def extend_rule_config(self, children: typing.Iterable["RuleConfig"]) -> None:
        self.children.extend((Statement.Label.RULE_CONFIG, child) for child in children)

    def children_rule_config(self) -> typing.Iterator["RuleConfig"]:
        return (
            typing.cast("RuleConfig", child) for label, child in self.children if label == Statement.Label.RULE_CONFIG
        )

    def child_rule_config(self) -> "RuleConfig":
        children = list(self.children_rule_config())
        if (n := len(children)) != 1:
            msg = f"Expected one rule_config child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_config(self) -> typing.Optional["RuleConfig"]:
        children = list(self.children_rule_config())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_config child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_trivia_preserve(self, child: "TriviaPreserve") -> None:
        self.children.append((Statement.Label.TRIVIA_PRESERVE, child))

    def extend_trivia_preserve(self, children: typing.Iterable["TriviaPreserve"]) -> None:
        self.children.extend((Statement.Label.TRIVIA_PRESERVE, child) for child in children)

    def children_trivia_preserve(self) -> typing.Iterator["TriviaPreserve"]:
        return (
            typing.cast("TriviaPreserve", child)
            for label, child in self.children
            if label == Statement.Label.TRIVIA_PRESERVE
        )

    def child_trivia_preserve(self) -> "TriviaPreserve":
        children = list(self.children_trivia_preserve())
        if (n := len(children)) != 1:
            msg = f"Expected one trivia_preserve child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trivia_preserve(self) -> typing.Optional["TriviaPreserve"]:
        children = list(self.children_trivia_preserve())
        if (n := len(children)) > 1:
            msg = f"Expected at most one trivia_preserve child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Default:
    class Label(enum.Enum):
        SPACING = enum.auto()
        WS_ALLOWED = enum.auto()
        WS_REQUIRED = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Spacing", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["Spacing", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Spacing", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["Spacing", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_spacing(self, child: "Spacing") -> None:
        self.children.append((Default.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable["Spacing"]) -> None:
        self.children.extend((Default.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator["Spacing"]:
        return (typing.cast("Spacing", child) for label, child in self.children if label == Default.Label.SPACING)

    def child_spacing(self) -> "Spacing":
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> typing.Optional["Spacing"]:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_allowed(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Default.Label.WS_ALLOWED, child))

    def extend_ws_allowed(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Default.Label.WS_ALLOWED, child) for child in children)

    def children_ws_allowed(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Default.Label.WS_ALLOWED
        )

    def child_ws_allowed(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_ws_allowed())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_allowed(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_ws_allowed())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_required(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Default.Label.WS_REQUIRED, child))

    def extend_ws_required(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Default.Label.WS_REQUIRED, child) for child in children)

    def children_ws_required(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Default.Label.WS_REQUIRED
        )

    def child_ws_required(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_ws_required())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_required(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_ws_required())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class RuleConfig:
    class Label(enum.Enum):
        RULE_NAME = enum.auto()
        RULE_STATEMENT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Identifier", "RuleStatement", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["Identifier", "RuleStatement", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Identifier", "RuleStatement", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Identifier", "RuleStatement", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_rule_name(self, child: "Identifier") -> None:
        self.children.append((RuleConfig.Label.RULE_NAME, child))

    def extend_rule_name(self, children: typing.Iterable["Identifier"]) -> None:
        self.children.extend((RuleConfig.Label.RULE_NAME, child) for child in children)

    def children_rule_name(self) -> typing.Iterator["Identifier"]:
        return (
            typing.cast("Identifier", child) for label, child in self.children if label == RuleConfig.Label.RULE_NAME
        )

    def child_rule_name(self) -> "Identifier":
        children = list(self.children_rule_name())
        if (n := len(children)) != 1:
            msg = f"Expected one rule_name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_name(self) -> typing.Optional["Identifier"]:
        children = list(self.children_rule_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule_statement(self, child: "RuleStatement") -> None:
        self.children.append((RuleConfig.Label.RULE_STATEMENT, child))

    def extend_rule_statement(self, children: typing.Iterable["RuleStatement"]) -> None:
        self.children.extend((RuleConfig.Label.RULE_STATEMENT, child) for child in children)

    def children_rule_statement(self) -> typing.Iterator["RuleStatement"]:
        return (
            typing.cast("RuleStatement", child)
            for label, child in self.children
            if label == RuleConfig.Label.RULE_STATEMENT
        )

    def child_rule_statement(self) -> "RuleStatement":
        children = list(self.children_rule_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one rule_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_statement(self) -> typing.Optional["RuleStatement"]:
        children = list(self.children_rule_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class RuleStatement:
    class Label(enum.Enum):
        AFTER = enum.auto()
        BEFORE = enum.auto()
        DEFAULT = enum.auto()
        GROUP = enum.auto()
        JOIN = enum.auto()
        NEST = enum.auto()
        OMIT = enum.auto()
        RENDER = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[
            Label | None,
            typing.Union["After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render"],
        ]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: typing.Union["After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[
            typing.Union["After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render"]
        ],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["After", "Before", "Default", "Group", "Join", "Nest", "Omit", "Render"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_after(self, child: "After") -> None:
        self.children.append((RuleStatement.Label.AFTER, child))

    def extend_after(self, children: typing.Iterable["After"]) -> None:
        self.children.extend((RuleStatement.Label.AFTER, child) for child in children)

    def children_after(self) -> typing.Iterator["After"]:
        return (typing.cast("After", child) for label, child in self.children if label == RuleStatement.Label.AFTER)

    def child_after(self) -> "After":
        children = list(self.children_after())
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> typing.Optional["After"]:
        children = list(self.children_after())
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_before(self, child: "Before") -> None:
        self.children.append((RuleStatement.Label.BEFORE, child))

    def extend_before(self, children: typing.Iterable["Before"]) -> None:
        self.children.extend((RuleStatement.Label.BEFORE, child) for child in children)

    def children_before(self) -> typing.Iterator["Before"]:
        return (typing.cast("Before", child) for label, child in self.children if label == RuleStatement.Label.BEFORE)

    def child_before(self) -> "Before":
        children = list(self.children_before())
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> typing.Optional["Before"]:
        children = list(self.children_before())
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_default(self, child: "Default") -> None:
        self.children.append((RuleStatement.Label.DEFAULT, child))

    def extend_default(self, children: typing.Iterable["Default"]) -> None:
        self.children.extend((RuleStatement.Label.DEFAULT, child) for child in children)

    def children_default(self) -> typing.Iterator["Default"]:
        return (typing.cast("Default", child) for label, child in self.children if label == RuleStatement.Label.DEFAULT)

    def child_default(self) -> "Default":
        children = list(self.children_default())
        if (n := len(children)) != 1:
            msg = f"Expected one default child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_default(self) -> typing.Optional["Default"]:
        children = list(self.children_default())
        if (n := len(children)) > 1:
            msg = f"Expected at most one default child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: "Group") -> None:
        self.children.append((RuleStatement.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable["Group"]) -> None:
        self.children.extend((RuleStatement.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator["Group"]:
        return (typing.cast("Group", child) for label, child in self.children if label == RuleStatement.Label.GROUP)

    def child_group(self) -> "Group":
        children = list(self.children_group())
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> typing.Optional["Group"]:
        children = list(self.children_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join(self, child: "Join") -> None:
        self.children.append((RuleStatement.Label.JOIN, child))

    def extend_join(self, children: typing.Iterable["Join"]) -> None:
        self.children.extend((RuleStatement.Label.JOIN, child) for child in children)

    def children_join(self) -> typing.Iterator["Join"]:
        return (typing.cast("Join", child) for label, child in self.children if label == RuleStatement.Label.JOIN)

    def child_join(self) -> "Join":
        children = list(self.children_join())
        if (n := len(children)) != 1:
            msg = f"Expected one join child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join(self) -> typing.Optional["Join"]:
        children = list(self.children_join())
        if (n := len(children)) > 1:
            msg = f"Expected at most one join child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: "Nest") -> None:
        self.children.append((RuleStatement.Label.NEST, child))

    def extend_nest(self, children: typing.Iterable["Nest"]) -> None:
        self.children.extend((RuleStatement.Label.NEST, child) for child in children)

    def children_nest(self) -> typing.Iterator["Nest"]:
        return (typing.cast("Nest", child) for label, child in self.children if label == RuleStatement.Label.NEST)

    def child_nest(self) -> "Nest":
        children = list(self.children_nest())
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> typing.Optional["Nest"]:
        children = list(self.children_nest())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_omit(self, child: "Omit") -> None:
        self.children.append((RuleStatement.Label.OMIT, child))

    def extend_omit(self, children: typing.Iterable["Omit"]) -> None:
        self.children.extend((RuleStatement.Label.OMIT, child) for child in children)

    def children_omit(self) -> typing.Iterator["Omit"]:
        return (typing.cast("Omit", child) for label, child in self.children if label == RuleStatement.Label.OMIT)

    def child_omit(self) -> "Omit":
        children = list(self.children_omit())
        if (n := len(children)) != 1:
            msg = f"Expected one omit child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_omit(self) -> typing.Optional["Omit"]:
        children = list(self.children_omit())
        if (n := len(children)) > 1:
            msg = f"Expected at most one omit child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_render(self, child: "Render") -> None:
        self.children.append((RuleStatement.Label.RENDER, child))

    def extend_render(self, children: typing.Iterable["Render"]) -> None:
        self.children.extend((RuleStatement.Label.RENDER, child) for child in children)

    def children_render(self) -> typing.Iterator["Render"]:
        return (typing.cast("Render", child) for label, child in self.children if label == RuleStatement.Label.RENDER)

    def child_render(self) -> "Render":
        children = list(self.children_render())
        if (n := len(children)) != 1:
            msg = f"Expected one render child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_render(self) -> typing.Optional["Render"]:
        children = list(self.children_render())
        if (n := len(children)) > 1:
            msg = f"Expected at most one render child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Group:
    class Label(enum.Enum):
        FROM_SPEC = enum.auto()
        TO_SPEC = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["FromSpec", "ToSpec", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["FromSpec", "ToSpec", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["FromSpec", "ToSpec", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["FromSpec", "ToSpec", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_from_spec(self, child: "FromSpec") -> None:
        self.children.append((Group.Label.FROM_SPEC, child))

    def extend_from_spec(self, children: typing.Iterable["FromSpec"]) -> None:
        self.children.extend((Group.Label.FROM_SPEC, child) for child in children)

    def children_from_spec(self) -> typing.Iterator["FromSpec"]:
        return (typing.cast("FromSpec", child) for label, child in self.children if label == Group.Label.FROM_SPEC)

    def child_from_spec(self) -> "FromSpec":
        children = list(self.children_from_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> typing.Optional["FromSpec"]:
        children = list(self.children_from_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: "ToSpec") -> None:
        self.children.append((Group.Label.TO_SPEC, child))

    def extend_to_spec(self, children: typing.Iterable["ToSpec"]) -> None:
        self.children.extend((Group.Label.TO_SPEC, child) for child in children)

    def children_to_spec(self) -> typing.Iterator["ToSpec"]:
        return (typing.cast("ToSpec", child) for label, child in self.children if label == Group.Label.TO_SPEC)

    def child_to_spec(self) -> "ToSpec":
        children = list(self.children_to_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> typing.Optional["ToSpec"]:
        children = list(self.children_to_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Nest:
    class Label(enum.Enum):
        FROM_SPEC = enum.auto()
        INDENT = enum.auto()
        TO_SPEC = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["FromSpec", "Integer", "ToSpec", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self, child: typing.Union["FromSpec", "Integer", "ToSpec", "Trivia"], label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["FromSpec", "Integer", "ToSpec", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["FromSpec", "Integer", "ToSpec", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_from_spec(self, child: "FromSpec") -> None:
        self.children.append((Nest.Label.FROM_SPEC, child))

    def extend_from_spec(self, children: typing.Iterable["FromSpec"]) -> None:
        self.children.extend((Nest.Label.FROM_SPEC, child) for child in children)

    def children_from_spec(self) -> typing.Iterator["FromSpec"]:
        return (typing.cast("FromSpec", child) for label, child in self.children if label == Nest.Label.FROM_SPEC)

    def child_from_spec(self) -> "FromSpec":
        children = list(self.children_from_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> typing.Optional["FromSpec"]:
        children = list(self.children_from_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_indent(self, child: "Integer") -> None:
        self.children.append((Nest.Label.INDENT, child))

    def extend_indent(self, children: typing.Iterable["Integer"]) -> None:
        self.children.extend((Nest.Label.INDENT, child) for child in children)

    def children_indent(self) -> typing.Iterator["Integer"]:
        return (typing.cast("Integer", child) for label, child in self.children if label == Nest.Label.INDENT)

    def child_indent(self) -> "Integer":
        children = list(self.children_indent())
        if (n := len(children)) != 1:
            msg = f"Expected one indent child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_indent(self) -> typing.Optional["Integer"]:
        children = list(self.children_indent())
        if (n := len(children)) > 1:
            msg = f"Expected at most one indent child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: "ToSpec") -> None:
        self.children.append((Nest.Label.TO_SPEC, child))

    def extend_to_spec(self, children: typing.Iterable["ToSpec"]) -> None:
        self.children.extend((Nest.Label.TO_SPEC, child) for child in children)

    def children_to_spec(self) -> typing.Iterator["ToSpec"]:
        return (typing.cast("ToSpec", child) for label, child in self.children if label == Nest.Label.TO_SPEC)

    def child_to_spec(self) -> "ToSpec":
        children = list(self.children_to_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> typing.Optional["ToSpec"]:
        children = list(self.children_to_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Join:
    class Label(enum.Enum):
        DOC_LITERAL = enum.auto()
        FROM_SPEC = enum.auto()
        TO_SPEC = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["DocLiteral", "FromSpec", "ToSpec", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self, child: typing.Union["DocLiteral", "FromSpec", "ToSpec", "Trivia"], label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["DocLiteral", "FromSpec", "ToSpec", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["DocLiteral", "FromSpec", "ToSpec", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_doc_literal(self, child: "DocLiteral") -> None:
        self.children.append((Join.Label.DOC_LITERAL, child))

    def extend_doc_literal(self, children: typing.Iterable["DocLiteral"]) -> None:
        self.children.extend((Join.Label.DOC_LITERAL, child) for child in children)

    def children_doc_literal(self) -> typing.Iterator["DocLiteral"]:
        return (typing.cast("DocLiteral", child) for label, child in self.children if label == Join.Label.DOC_LITERAL)

    def child_doc_literal(self) -> "DocLiteral":
        children = list(self.children_doc_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> typing.Optional["DocLiteral"]:
        children = list(self.children_doc_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_from_spec(self, child: "FromSpec") -> None:
        self.children.append((Join.Label.FROM_SPEC, child))

    def extend_from_spec(self, children: typing.Iterable["FromSpec"]) -> None:
        self.children.extend((Join.Label.FROM_SPEC, child) for child in children)

    def children_from_spec(self) -> typing.Iterator["FromSpec"]:
        return (typing.cast("FromSpec", child) for label, child in self.children if label == Join.Label.FROM_SPEC)

    def child_from_spec(self) -> "FromSpec":
        children = list(self.children_from_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> typing.Optional["FromSpec"]:
        children = list(self.children_from_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: "ToSpec") -> None:
        self.children.append((Join.Label.TO_SPEC, child))

    def extend_to_spec(self, children: typing.Iterable["ToSpec"]) -> None:
        self.children.extend((Join.Label.TO_SPEC, child) for child in children)

    def children_to_spec(self) -> typing.Iterator["ToSpec"]:
        return (typing.cast("ToSpec", child) for label, child in self.children if label == Join.Label.TO_SPEC)

    def child_to_spec(self) -> "ToSpec":
        children = list(self.children_to_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> typing.Optional["ToSpec"]:
        children = list(self.children_to_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class FromSpec:
    class Label(enum.Enum):
        AFTER = enum.auto()
        FROM_ANCHOR = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_after(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((FromSpec.Label.AFTER, child))

    def extend_after(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((FromSpec.Label.AFTER, child) for child in children)

    def children_after(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == FromSpec.Label.AFTER
        )

    def child_after(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_after())
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_after())
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_from_anchor(self, child: "Anchor") -> None:
        self.children.append((FromSpec.Label.FROM_ANCHOR, child))

    def extend_from_anchor(self, children: typing.Iterable["Anchor"]) -> None:
        self.children.extend((FromSpec.Label.FROM_ANCHOR, child) for child in children)

    def children_from_anchor(self) -> typing.Iterator["Anchor"]:
        return (typing.cast("Anchor", child) for label, child in self.children if label == FromSpec.Label.FROM_ANCHOR)

    def child_from_anchor(self) -> "Anchor":
        children = list(self.children_from_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one from_anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_anchor(self) -> typing.Optional["Anchor"]:
        children = list(self.children_from_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class ToSpec:
    class Label(enum.Enum):
        BEFORE = enum.auto()
        TO_ANCHOR = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["Anchor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_before(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((ToSpec.Label.BEFORE, child))

    def extend_before(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((ToSpec.Label.BEFORE, child) for child in children)

    def children_before(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == ToSpec.Label.BEFORE
        )

    def child_before(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_before())
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_before())
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_anchor(self, child: "Anchor") -> None:
        self.children.append((ToSpec.Label.TO_ANCHOR, child))

    def extend_to_anchor(self, children: typing.Iterable["Anchor"]) -> None:
        self.children.extend((ToSpec.Label.TO_ANCHOR, child) for child in children)

    def children_to_anchor(self) -> typing.Iterator["Anchor"]:
        return (typing.cast("Anchor", child) for label, child in self.children if label == ToSpec.Label.TO_ANCHOR)

    def child_to_anchor(self) -> "Anchor":
        children = list(self.children_to_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one to_anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_anchor(self) -> typing.Optional["Anchor"]:
        children = list(self.children_to_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Anchor:
    class Label(enum.Enum):
        LABEL = enum.auto()
        LITERAL = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Identifier", "Literal"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Identifier", "Literal"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[typing.Union["Identifier", "Literal"]], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Identifier", "Literal"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_label(self, child: "Identifier") -> None:
        self.children.append((Anchor.Label.LABEL, child))

    def extend_label(self, children: typing.Iterable["Identifier"]) -> None:
        self.children.extend((Anchor.Label.LABEL, child) for child in children)

    def children_label(self) -> typing.Iterator["Identifier"]:
        return (typing.cast("Identifier", child) for label, child in self.children if label == Anchor.Label.LABEL)

    def child_label(self) -> "Identifier":
        children = list(self.children_label())
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> typing.Optional["Identifier"]:
        children = list(self.children_label())
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_literal(self, child: "Literal") -> None:
        self.children.append((Anchor.Label.LITERAL, child))

    def extend_literal(self, children: typing.Iterable["Literal"]) -> None:
        self.children.extend((Anchor.Label.LITERAL, child) for child in children)

    def children_literal(self) -> typing.Iterator["Literal"]:
        return (typing.cast("Literal", child) for label, child in self.children if label == Anchor.Label.LITERAL)

    def child_literal(self) -> "Literal":
        children = list(self.children_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_literal(self) -> typing.Optional["Literal"]:
        children = list(self.children_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class After:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        POSITION_SPEC_STATEMENT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Anchor", "PositionSpecStatement", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self, child: typing.Union["Anchor", "PositionSpecStatement", "Trivia"], label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Anchor", "PositionSpecStatement", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Anchor", "PositionSpecStatement", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_anchor(self, child: "Anchor") -> None:
        self.children.append((After.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable["Anchor"]) -> None:
        self.children.extend((After.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator["Anchor"]:
        return (typing.cast("Anchor", child) for label, child in self.children if label == After.Label.ANCHOR)

    def child_anchor(self) -> "Anchor":
        children = list(self.children_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> typing.Optional["Anchor"]:
        children = list(self.children_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_position_spec_statement(self, child: "PositionSpecStatement") -> None:
        self.children.append((After.Label.POSITION_SPEC_STATEMENT, child))

    def extend_position_spec_statement(self, children: typing.Iterable["PositionSpecStatement"]) -> None:
        self.children.extend((After.Label.POSITION_SPEC_STATEMENT, child) for child in children)

    def children_position_spec_statement(self) -> typing.Iterator["PositionSpecStatement"]:
        return (
            typing.cast("PositionSpecStatement", child)
            for label, child in self.children
            if label == After.Label.POSITION_SPEC_STATEMENT
        )

    def child_position_spec_statement(self) -> "PositionSpecStatement":
        children = list(self.children_position_spec_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_position_spec_statement(self) -> typing.Optional["PositionSpecStatement"]:
        children = list(self.children_position_spec_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Before:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        POSITION_SPEC_STATEMENT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Anchor", "PositionSpecStatement", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self, child: typing.Union["Anchor", "PositionSpecStatement", "Trivia"], label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Anchor", "PositionSpecStatement", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Anchor", "PositionSpecStatement", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_anchor(self, child: "Anchor") -> None:
        self.children.append((Before.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable["Anchor"]) -> None:
        self.children.extend((Before.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator["Anchor"]:
        return (typing.cast("Anchor", child) for label, child in self.children if label == Before.Label.ANCHOR)

    def child_anchor(self) -> "Anchor":
        children = list(self.children_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> typing.Optional["Anchor"]:
        children = list(self.children_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_position_spec_statement(self, child: "PositionSpecStatement") -> None:
        self.children.append((Before.Label.POSITION_SPEC_STATEMENT, child))

    def extend_position_spec_statement(self, children: typing.Iterable["PositionSpecStatement"]) -> None:
        self.children.extend((Before.Label.POSITION_SPEC_STATEMENT, child) for child in children)

    def children_position_spec_statement(self) -> typing.Iterator["PositionSpecStatement"]:
        return (
            typing.cast("PositionSpecStatement", child)
            for label, child in self.children
            if label == Before.Label.POSITION_SPEC_STATEMENT
        )

    def child_position_spec_statement(self) -> "PositionSpecStatement":
        children = list(self.children_position_spec_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_position_spec_statement(self) -> typing.Optional["PositionSpecStatement"]:
        children = list(self.children_position_spec_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Omit:
    class Label(enum.Enum):
        ANCHOR = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Anchor", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Anchor", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[typing.Union["Anchor", "Trivia"]], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Anchor", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_anchor(self, child: "Anchor") -> None:
        self.children.append((Omit.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable["Anchor"]) -> None:
        self.children.extend((Omit.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator["Anchor"]:
        return (typing.cast("Anchor", child) for label, child in self.children if label == Omit.Label.ANCHOR)

    def child_anchor(self) -> "Anchor":
        children = list(self.children_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> typing.Optional["Anchor"]:
        children = list(self.children_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Render:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        SPACING = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Anchor", "Spacing", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["Anchor", "Spacing", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Anchor", "Spacing", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Anchor", "Spacing", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_anchor(self, child: "Anchor") -> None:
        self.children.append((Render.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable["Anchor"]) -> None:
        self.children.extend((Render.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator["Anchor"]:
        return (typing.cast("Anchor", child) for label, child in self.children if label == Render.Label.ANCHOR)

    def child_anchor(self) -> "Anchor":
        children = list(self.children_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> typing.Optional["Anchor"]:
        children = list(self.children_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_spacing(self, child: "Spacing") -> None:
        self.children.append((Render.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable["Spacing"]) -> None:
        self.children.extend((Render.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator["Spacing"]:
        return (typing.cast("Spacing", child) for label, child in self.children if label == Render.Label.SPACING)

    def child_spacing(self) -> "Spacing":
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> typing.Optional["Spacing"]:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class PositionSpecStatement:
    class Label(enum.Enum):
        SPACING = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Spacing", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Spacing", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[typing.Union["Spacing", "Trivia"]], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Spacing", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_spacing(self, child: "Spacing") -> None:
        self.children.append((PositionSpecStatement.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable["Spacing"]) -> None:
        self.children.extend((PositionSpecStatement.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator["Spacing"]:
        return (
            typing.cast("Spacing", child)
            for label, child in self.children
            if label == PositionSpecStatement.Label.SPACING
        )

    def child_spacing(self) -> "Spacing":
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> typing.Optional["Spacing"]:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Spacing:
    class Label(enum.Enum):
        BLANK = enum.auto()
        BSP = enum.auto()
        HARD = enum.auto()
        NBSP = enum.auto()
        NIL = enum.auto()
        NUM_BLANKS = enum.auto()
        SOFT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Integer", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["Integer", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Integer", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["Integer", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_blank(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Spacing.Label.BLANK, child))

    def extend_blank(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Spacing.Label.BLANK, child) for child in children)

    def children_blank(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Spacing.Label.BLANK
        )

    def child_blank(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_blank())
        if (n := len(children)) != 1:
            msg = f"Expected one blank child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_blank(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_blank())
        if (n := len(children)) > 1:
            msg = f"Expected at most one blank child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_bsp(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Spacing.Label.BSP, child))

    def extend_bsp(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Spacing.Label.BSP, child) for child in children)

    def children_bsp(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Spacing.Label.BSP
        )

    def child_bsp(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_bsp())
        if (n := len(children)) != 1:
            msg = f"Expected one bsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bsp(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_bsp())
        if (n := len(children)) > 1:
            msg = f"Expected at most one bsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_hard(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Spacing.Label.HARD, child))

    def extend_hard(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Spacing.Label.HARD, child) for child in children)

    def children_hard(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Spacing.Label.HARD
        )

    def child_hard(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_hard())
        if (n := len(children)) != 1:
            msg = f"Expected one hard child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hard(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_hard())
        if (n := len(children)) > 1:
            msg = f"Expected at most one hard child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nbsp(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Spacing.Label.NBSP, child))

    def extend_nbsp(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Spacing.Label.NBSP, child) for child in children)

    def children_nbsp(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Spacing.Label.NBSP
        )

    def child_nbsp(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_nbsp())
        if (n := len(children)) != 1:
            msg = f"Expected one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nbsp(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_nbsp())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nil(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Spacing.Label.NIL, child))

    def extend_nil(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Spacing.Label.NIL, child) for child in children)

    def children_nil(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Spacing.Label.NIL
        )

    def child_nil(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_nil())
        if (n := len(children)) != 1:
            msg = f"Expected one nil child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nil(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_nil())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nil child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_num_blanks(self, child: "Integer") -> None:
        self.children.append((Spacing.Label.NUM_BLANKS, child))

    def extend_num_blanks(self, children: typing.Iterable["Integer"]) -> None:
        self.children.extend((Spacing.Label.NUM_BLANKS, child) for child in children)

    def children_num_blanks(self) -> typing.Iterator["Integer"]:
        return (typing.cast("Integer", child) for label, child in self.children if label == Spacing.Label.NUM_BLANKS)

    def child_num_blanks(self) -> "Integer":
        children = list(self.children_num_blanks())
        if (n := len(children)) != 1:
            msg = f"Expected one num_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_num_blanks(self) -> typing.Optional["Integer"]:
        children = list(self.children_num_blanks())
        if (n := len(children)) > 1:
            msg = f"Expected at most one num_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_soft(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Spacing.Label.SOFT, child))

    def extend_soft(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Spacing.Label.SOFT, child) for child in children)

    def children_soft(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Spacing.Label.SOFT
        )

    def child_soft(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_soft())
        if (n := len(children)) != 1:
            msg = f"Expected one soft child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_soft(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_soft())
        if (n := len(children)) > 1:
            msg = f"Expected at most one soft child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class DocLiteral:
    class Label(enum.Enum):
        COMPOUND_LITERAL = enum.auto()
        CONCAT_LITERAL = enum.auto()
        JOIN_LITERAL = enum.auto()
        SPACING = enum.auto()
        TEXT_LITERAL = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[
            Label | None,
            typing.Union["CompoundLiteral", "ConcatLiteral", "JoinLiteral", "Spacing", "TextLiteral"],
        ]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: typing.Union["CompoundLiteral", "ConcatLiteral", "JoinLiteral", "Spacing", "TextLiteral"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[
            typing.Union["CompoundLiteral", "ConcatLiteral", "JoinLiteral", "Spacing", "TextLiteral"]
        ],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[
        Label | None,
        typing.Union["CompoundLiteral", "ConcatLiteral", "JoinLiteral", "Spacing", "TextLiteral"],
    ]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_compound_literal(self, child: "CompoundLiteral") -> None:
        self.children.append((DocLiteral.Label.COMPOUND_LITERAL, child))

    def extend_compound_literal(self, children: typing.Iterable["CompoundLiteral"]) -> None:
        self.children.extend((DocLiteral.Label.COMPOUND_LITERAL, child) for child in children)

    def children_compound_literal(self) -> typing.Iterator["CompoundLiteral"]:
        return (
            typing.cast("CompoundLiteral", child)
            for label, child in self.children
            if label == DocLiteral.Label.COMPOUND_LITERAL
        )

    def child_compound_literal(self) -> "CompoundLiteral":
        children = list(self.children_compound_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one compound_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_compound_literal(self) -> typing.Optional["CompoundLiteral"]:
        children = list(self.children_compound_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one compound_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_concat_literal(self, child: "ConcatLiteral") -> None:
        self.children.append((DocLiteral.Label.CONCAT_LITERAL, child))

    def extend_concat_literal(self, children: typing.Iterable["ConcatLiteral"]) -> None:
        self.children.extend((DocLiteral.Label.CONCAT_LITERAL, child) for child in children)

    def children_concat_literal(self) -> typing.Iterator["ConcatLiteral"]:
        return (
            typing.cast("ConcatLiteral", child)
            for label, child in self.children
            if label == DocLiteral.Label.CONCAT_LITERAL
        )

    def child_concat_literal(self) -> "ConcatLiteral":
        children = list(self.children_concat_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one concat_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_concat_literal(self) -> typing.Optional["ConcatLiteral"]:
        children = list(self.children_concat_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one concat_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join_literal(self, child: "JoinLiteral") -> None:
        self.children.append((DocLiteral.Label.JOIN_LITERAL, child))

    def extend_join_literal(self, children: typing.Iterable["JoinLiteral"]) -> None:
        self.children.extend((DocLiteral.Label.JOIN_LITERAL, child) for child in children)

    def children_join_literal(self) -> typing.Iterator["JoinLiteral"]:
        return (
            typing.cast("JoinLiteral", child)
            for label, child in self.children
            if label == DocLiteral.Label.JOIN_LITERAL
        )

    def child_join_literal(self) -> "JoinLiteral":
        children = list(self.children_join_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one join_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join_literal(self) -> typing.Optional["JoinLiteral"]:
        children = list(self.children_join_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one join_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_spacing(self, child: "Spacing") -> None:
        self.children.append((DocLiteral.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable["Spacing"]) -> None:
        self.children.extend((DocLiteral.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator["Spacing"]:
        return (typing.cast("Spacing", child) for label, child in self.children if label == DocLiteral.Label.SPACING)

    def child_spacing(self) -> "Spacing":
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> typing.Optional["Spacing"]:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_text_literal(self, child: "TextLiteral") -> None:
        self.children.append((DocLiteral.Label.TEXT_LITERAL, child))

    def extend_text_literal(self, children: typing.Iterable["TextLiteral"]) -> None:
        self.children.extend((DocLiteral.Label.TEXT_LITERAL, child) for child in children)

    def children_text_literal(self) -> typing.Iterator["TextLiteral"]:
        return (
            typing.cast("TextLiteral", child)
            for label, child in self.children
            if label == DocLiteral.Label.TEXT_LITERAL
        )

    def child_text_literal(self) -> "TextLiteral":
        children = list(self.children_text_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one text_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text_literal(self) -> typing.Optional["TextLiteral"]:
        children = list(self.children_text_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one text_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class TextLiteral:
    class Label(enum.Enum):
        TEXT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Literal", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Literal", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[typing.Union["Literal", "Trivia"]], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Literal", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_text(self, child: "Literal") -> None:
        self.children.append((TextLiteral.Label.TEXT, child))

    def extend_text(self, children: typing.Iterable["Literal"]) -> None:
        self.children.extend((TextLiteral.Label.TEXT, child) for child in children)

    def children_text(self) -> typing.Iterator["Literal"]:
        return (typing.cast("Literal", child) for label, child in self.children if label == TextLiteral.Label.TEXT)

    def child_text(self) -> "Literal":
        children = list(self.children_text())
        if (n := len(children)) != 1:
            msg = f"Expected one text child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text(self) -> typing.Optional["Literal"]:
        children = list(self.children_text())
        if (n := len(children)) > 1:
            msg = f"Expected at most one text child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class ConcatLiteral:
    class Label(enum.Enum):
        DOC_LIST_LITERAL = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["DocListLiteral", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["DocListLiteral", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[typing.Union["DocListLiteral", "Trivia"]], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["DocListLiteral", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_doc_list_literal(self, child: "DocListLiteral") -> None:
        self.children.append((ConcatLiteral.Label.DOC_LIST_LITERAL, child))

    def extend_doc_list_literal(self, children: typing.Iterable["DocListLiteral"]) -> None:
        self.children.extend((ConcatLiteral.Label.DOC_LIST_LITERAL, child) for child in children)

    def children_doc_list_literal(self) -> typing.Iterator["DocListLiteral"]:
        return (
            typing.cast("DocListLiteral", child)
            for label, child in self.children
            if label == ConcatLiteral.Label.DOC_LIST_LITERAL
        )

    def child_doc_list_literal(self) -> "DocListLiteral":
        children = list(self.children_doc_list_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_list_literal(self) -> typing.Optional["DocListLiteral"]:
        children = list(self.children_doc_list_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class JoinLiteral:
    class Label(enum.Enum):
        DOC_LIST_LITERAL = enum.auto()
        SEPARATOR = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["DocListLiteral", "DocLiteral", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["DocListLiteral", "DocLiteral", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["DocListLiteral", "DocLiteral", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["DocListLiteral", "DocLiteral", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_doc_list_literal(self, child: "DocListLiteral") -> None:
        self.children.append((JoinLiteral.Label.DOC_LIST_LITERAL, child))

    def extend_doc_list_literal(self, children: typing.Iterable["DocListLiteral"]) -> None:
        self.children.extend((JoinLiteral.Label.DOC_LIST_LITERAL, child) for child in children)

    def children_doc_list_literal(self) -> typing.Iterator["DocListLiteral"]:
        return (
            typing.cast("DocListLiteral", child)
            for label, child in self.children
            if label == JoinLiteral.Label.DOC_LIST_LITERAL
        )

    def child_doc_list_literal(self) -> "DocListLiteral":
        children = list(self.children_doc_list_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_list_literal(self) -> typing.Optional["DocListLiteral"]:
        children = list(self.children_doc_list_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_separator(self, child: "DocLiteral") -> None:
        self.children.append((JoinLiteral.Label.SEPARATOR, child))

    def extend_separator(self, children: typing.Iterable["DocLiteral"]) -> None:
        self.children.extend((JoinLiteral.Label.SEPARATOR, child) for child in children)

    def children_separator(self) -> typing.Iterator["DocLiteral"]:
        return (
            typing.cast("DocLiteral", child) for label, child in self.children if label == JoinLiteral.Label.SEPARATOR
        )

    def child_separator(self) -> "DocLiteral":
        children = list(self.children_separator())
        if (n := len(children)) != 1:
            msg = f"Expected one separator child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_separator(self) -> typing.Optional["DocLiteral"]:
        children = list(self.children_separator())
        if (n := len(children)) > 1:
            msg = f"Expected at most one separator child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class DocListLiteral:
    class Label(enum.Enum):
        DOC_LITERAL = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["DocLiteral", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["DocLiteral", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[typing.Union["DocLiteral", "Trivia"]], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["DocLiteral", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_doc_literal(self, child: "DocLiteral") -> None:
        self.children.append((DocListLiteral.Label.DOC_LITERAL, child))

    def extend_doc_literal(self, children: typing.Iterable["DocLiteral"]) -> None:
        self.children.extend((DocListLiteral.Label.DOC_LITERAL, child) for child in children)

    def children_doc_literal(self) -> typing.Iterator["DocLiteral"]:
        return (
            typing.cast("DocLiteral", child)
            for label, child in self.children
            if label == DocListLiteral.Label.DOC_LITERAL
        )

    def child_doc_literal(self) -> "DocLiteral":
        children = list(self.children_doc_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> typing.Optional["DocLiteral"]:
        children = list(self.children_doc_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class CompoundLiteral:
    class Label(enum.Enum):
        DOC_LITERAL = enum.auto()
        GROUP = enum.auto()
        NEST = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["DocLiteral", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["DocLiteral", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["DocLiteral", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["DocLiteral", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_doc_literal(self, child: "DocLiteral") -> None:
        self.children.append((CompoundLiteral.Label.DOC_LITERAL, child))

    def extend_doc_literal(self, children: typing.Iterable["DocLiteral"]) -> None:
        self.children.extend((CompoundLiteral.Label.DOC_LITERAL, child) for child in children)

    def children_doc_literal(self) -> typing.Iterator["DocLiteral"]:
        return (
            typing.cast("DocLiteral", child)
            for label, child in self.children
            if label == CompoundLiteral.Label.DOC_LITERAL
        )

    def child_doc_literal(self) -> "DocLiteral":
        children = list(self.children_doc_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> typing.Optional["DocLiteral"]:
        children = list(self.children_doc_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((CompoundLiteral.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((CompoundLiteral.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == CompoundLiteral.Label.GROUP
        )

    def child_group(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_group())
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((CompoundLiteral.Label.NEST, child))

    def extend_nest(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((CompoundLiteral.Label.NEST, child) for child in children)

    def children_nest(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == CompoundLiteral.Label.NEST
        )

    def child_nest(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_nest())
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_nest())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class TriviaPreserve:
    class Label(enum.Enum):
        TRIVIA_NODE_LIST = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Trivia", "TriviaNodeList"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["Trivia", "TriviaNodeList"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[typing.Union["Trivia", "TriviaNodeList"]], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Trivia", "TriviaNodeList"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_trivia_node_list(self, child: "TriviaNodeList") -> None:
        self.children.append((TriviaPreserve.Label.TRIVIA_NODE_LIST, child))

    def extend_trivia_node_list(self, children: typing.Iterable["TriviaNodeList"]) -> None:
        self.children.extend((TriviaPreserve.Label.TRIVIA_NODE_LIST, child) for child in children)

    def children_trivia_node_list(self) -> typing.Iterator["TriviaNodeList"]:
        return (
            typing.cast("TriviaNodeList", child)
            for label, child in self.children
            if label == TriviaPreserve.Label.TRIVIA_NODE_LIST
        )

    def child_trivia_node_list(self) -> "TriviaNodeList":
        children = list(self.children_trivia_node_list())
        if (n := len(children)) != 1:
            msg = f"Expected one trivia_node_list child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trivia_node_list(self) -> typing.Optional["TriviaNodeList"]:
        children = list(self.children_trivia_node_list())
        if (n := len(children)) > 1:
            msg = f"Expected at most one trivia_node_list child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class TriviaNodeList:
    class Label(enum.Enum):
        IDENTIFIER = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Identifier", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Identifier", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[typing.Union["Identifier", "Trivia"]], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Identifier", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_identifier(self, child: "Identifier") -> None:
        self.children.append((TriviaNodeList.Label.IDENTIFIER, child))

    def extend_identifier(self, children: typing.Iterable["Identifier"]) -> None:
        self.children.extend((TriviaNodeList.Label.IDENTIFIER, child) for child in children)

    def children_identifier(self) -> typing.Iterator["Identifier"]:
        return (
            typing.cast("Identifier", child)
            for label, child in self.children
            if label == TriviaNodeList.Label.IDENTIFIER
        )

    def child_identifier(self) -> "Identifier":
        children = list(self.children_identifier())
        if (n := len(children)) != 1:
            msg = f"Expected one identifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_identifier(self) -> typing.Optional["Identifier"]:
        children = list(self.children_identifier())
        if (n := len(children)) > 1:
            msg = f"Expected at most one identifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Identifier:
    class Label(enum.Enum):
        NAME = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(default_factory=list)

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_name(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Identifier.Label.NAME, child))

    def extend_name(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Identifier.Label.NAME, child) for child in children)

    def children_name(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Identifier.Label.NAME)

    def child_name(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_name())
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Literal:
    class Label(enum.Enum):
        VALUE = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(default_factory=list)

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_value(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Literal.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Literal.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Literal.Label.VALUE)

    def child_value(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Integer:
    class Label(enum.Enum):
        VALUE = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(default_factory=list)

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_value(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Integer.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Integer.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Integer.Label.VALUE)

    def child_value(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Trivia:
    class Label(enum.Enum):
        LINE_COMMENT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["LineComment", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["LineComment", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["LineComment", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["LineComment", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_line_comment(self, child: "LineComment") -> None:
        self.children.append((Trivia.Label.LINE_COMMENT, child))

    def extend_line_comment(self, children: typing.Iterable["LineComment"]) -> None:
        self.children.extend((Trivia.Label.LINE_COMMENT, child) for child in children)

    def children_line_comment(self) -> typing.Iterator["LineComment"]:
        return (
            typing.cast("LineComment", child) for label, child in self.children if label == Trivia.Label.LINE_COMMENT
        )

    def child_line_comment(self) -> "LineComment":
        children = list(self.children_line_comment())
        if (n := len(children)) != 1:
            msg = f"Expected one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_line_comment(self) -> typing.Optional["LineComment"]:
        children = list(self.children_line_comment())
        if (n := len(children)) > 1:
            msg = f"Expected at most one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class LineComment:
    class Label(enum.Enum):
        CONTENT = enum.auto()
        NEWLINE = enum.auto()
        PREFIX = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(default_factory=list)

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_content(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((LineComment.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((LineComment.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == LineComment.Label.CONTENT)

    def child_content(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_content())
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_content())
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_newline(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((LineComment.Label.NEWLINE, child))

    def extend_newline(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((LineComment.Label.NEWLINE, child) for child in children)

    def children_newline(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == LineComment.Label.NEWLINE)

    def child_newline(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_newline())
        if (n := len(children)) != 1:
            msg = f"Expected one newline child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_newline(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_newline())
        if (n := len(children)) > 1:
            msg = f"Expected at most one newline child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_prefix(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((LineComment.Label.PREFIX, child))

    def extend_prefix(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((LineComment.Label.PREFIX, child) for child in children)

    def children_prefix(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == LineComment.Label.PREFIX)

    def child_prefix(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_prefix())
        if (n := len(children)) != 1:
            msg = f"Expected one prefix child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_prefix(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_prefix())
        if (n := len(children)) > 1:
            msg = f"Expected at most one prefix child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None
