"""Type stubs for i3ipc."""

from typing import Iterator

class Con:
    id: int
    pid: int | None
    name: str | None
    type: str
    layout: str
    focused: bool
    nodes: list[Con]
    marks: list[str]
    window_title: str | None
    app_id: str | None
    window_class: str | None
    window_instance: str | None
    _con_id: int
    rect: Rect
    deco_rect: Rect

    def command(self, command: str) -> list[CommandReply]: ...
    def workspace(self) -> Con | None: ...
    def find_by_id(self, con_id: int) -> Con | None: ...
    def find_focused(self) -> Con | None: ...
    def descendants(self) -> Iterator[Con]: ...
    def leaves(self) -> list[Con]: ...
    def workspaces(self) -> list[Con]: ...

class Rect:
    x: int
    y: int
    width: int
    height: int

class CommandReply:
    success: bool
    error: str | None
    ipc_data: object

class Connection:
    def __init__(self, socket_path: str | None = None) -> None: ...
    def command(self, command: str) -> list[CommandReply]: ...
    def get_tree(self) -> Con: ...
    def get_marks(self) -> list[str]: ...

def Event(name: str) -> type: ...
