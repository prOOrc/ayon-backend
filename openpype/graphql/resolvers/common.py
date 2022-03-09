from typing import Annotated

import strawberry
from strawberry.types import Info

from openpype.lib.postgres import Postgres
from openpype.utils import EntityID
from openpype.graphql.connections import BaseConnection, PageInfo


def argdesc(description):
    description = "\n".join([line.strip() for line in description.split("\n")])
    return strawberry.argument(description=description)


ARGFirst = Annotated[int | None, argdesc("Pagination: first")]
ARGAfter = Annotated[str | None, argdesc("Pagination: first")]
ARGLast = Annotated[int | None, argdesc("Pagination: last")]
ARGBefore = Annotated[str | None, argdesc("Pagination: before")]
ARGIds = Annotated[list[str] | None, argdesc("List of ids to be returned")]


class FieldInfo:
    """Info object parser.

    Parses a strawberry.Info object and returns a list of selected fields.
    list of roots may be provided - roots will be stripped from the paths.

    List of roots must be ordered from the most specific to the most general,
    otherwise the stripping will not work.

    Paths are returned as a comma separated string.
    """

    def __init__(self, info: Info, roots: list[str] = None):
        self.info = info
        if roots is None:
            self.roots = []
        else:
            self.roots = roots

        def parse_fields(fields, name=None):
            for field in fields:
                fname = name + "." + field.name if name else field.name
                yield fname
                yield from parse_fields(field.selections, fname)

        self.fields = []
        for field in parse_fields(info.selected_fields):
            for root in self.roots:
                if field.startswith(root + "."):
                    field = field.removeprefix(root + ".")
                    break
            if field in self.fields:
                continue
            self.fields.append(field)

    def __iter__(self):
        return self.fields.__iter__()

    def __contains__(self, field):
        return field in self.fields

    def has_any(self, *fields):
        for field in fields:
            if field in self.fields:
                return True
        return False


async def resolve(
    connection_type,
    edge_type,
    node_type,
    project_name: str,
    query: str,
    first: int = 0,
    last: int = 0,
    context: dict = None,
) -> BaseConnection:
    """Return a connection object from a query."""

    edges = []
    count = first or last

    async for record in Postgres.iterate(query):
        if count and count <= len(edges):
            break

        node = node_type.from_record(project_name, record, context=context)
        edges.append(edge_type(node=node, cursor=EntityID.parse(record["id"])))

    has_next_page = False
    has_previous_page = False
    start_cursor = None
    end_cursor = None

    if first:
        has_next_page = len(edges) >= first
        has_previous_page = False  # TODO
        start_cursor = edges[0].cursor if edges else None
        end_cursor = edges[-1].cursor if edges else None
    elif last:
        has_next_page = False  # TODO
        has_previous_page = len(edges) >= last
        start_cursor = edges[0].cursor if edges else None
        end_cursor = edges[-1].cursor if edges else None
        edges.reverse()

    page_info = PageInfo(
        has_next_page=has_next_page,
        has_previous_page=has_previous_page,
        start_cursor=start_cursor,
        end_cursor=end_cursor,
    )

    return connection_type(edges=edges, page_info=page_info)
