from typing import TYPE_CHECKING

import strawberry

from ayon_server.entities import ProjectEntity
from ayon_server.graphql.resolvers.folders import get_folder, get_folders
from ayon_server.graphql.resolvers.representations import (
    get_representation,
    get_representations,
)
from ayon_server.graphql.resolvers.subsets import get_subset, get_subsets
from ayon_server.graphql.resolvers.tasks import get_task, get_tasks
from ayon_server.graphql.resolvers.versions import get_version, get_versions
from ayon_server.graphql.resolvers.workfiles import get_workfile, get_workfiles
from ayon_server.graphql.utils import parse_attrib_data
from ayon_server.lib.postgres import Postgres

if TYPE_CHECKING:
    from ayon_server.graphql.connections import (
        FoldersConnection,
        RepresentationsConnection,
        SubsetsConnection,
        TasksConnection,
        VersionsConnection,
        WorkfilesConnection,
    )
    from ayon_server.graphql.nodes.folder import FolderNode
    from ayon_server.graphql.nodes.representation import RepresentationNode
    from ayon_server.graphql.nodes.subset import SubsetNode
    from ayon_server.graphql.nodes.task import TaskNode
    from ayon_server.graphql.nodes.version import VersionNode
    from ayon_server.graphql.nodes.workfile import WorkfileNode


@strawberry.type
class TaskType:
    name: str


@strawberry.type
class FolderType:
    name: str

    @strawberry.field
    def icon(self) -> str:
        return self.name.lower()


@ProjectEntity.strawberry_attrib()
class ProjectAttribType:
    pass


@strawberry.type
class ProjectNode:
    name: str = strawberry.field()
    project_name: str = strawberry.field()
    code: str = strawberry.field()
    attrib: ProjectAttribType
    active: bool
    library: bool
    created_at: int
    updated_at: int

    folder: "FolderNode" = strawberry.field(
        resolver=get_folder,
        description=get_folder.__doc__,
    )

    folders: "FoldersConnection" = strawberry.field(
        resolver=get_folders,
        description=get_folders.__doc__,
    )

    task: "TaskNode" = strawberry.field(
        resolver=get_task,
        description=get_task.__doc__,
    )

    tasks: "TasksConnection" = strawberry.field(
        resolver=get_tasks,
        description=get_tasks.__doc__,
    )

    subset: "SubsetNode" = strawberry.field(
        resolver=get_subset,
        description=get_subset.__doc__,
    )

    subsets: "SubsetsConnection" = strawberry.field(
        resolver=get_subsets,
        description=get_subsets.__doc__,
    )

    version: "VersionNode" = strawberry.field(
        resolver=get_version,
        description=get_version.__doc__,
    )

    versions: "VersionsConnection" = strawberry.field(
        resolver=get_versions,
        description=get_versions.__doc__,
    )

    representation: "RepresentationNode" = strawberry.field(
        resolver=get_representation,
        description=get_representation.__doc__,
    )

    representations: "RepresentationsConnection" = strawberry.field(
        resolver=get_representations,
        description=get_representations.__doc__,
    )

    workfile: "WorkfileNode" = strawberry.field(
        resolver=get_workfile,
        description=get_workfile.__doc__,
    )

    workfiles: "WorkfilesConnection" = strawberry.field(
        resolver=get_workfiles,
        description=get_workfiles.__doc__,
    )

    @strawberry.field
    async def task_types(self, active_only: bool = False) -> list[TaskType]:
        if active_only:
            query = f"""
                SELECT DISTINCT(task_type) AS task_type
                FROM project_{self.project_name}.tasks
            """
        else:
            query = f"""
                SELECT name AS task_type
                FROM project_{self.project_name}.task_types
                ORDER BY position
            """
        return [
            TaskType(name=row["task_type"]) async for row in Postgres.iterate(query)
        ]

    @strawberry.field
    async def folder_types(self, active_only: bool = False) -> list[FolderType]:
        if active_only:
            query = f"""
                SELECT DISTINCT(folder_type) AS folder_type
                FROM project_{self.project_name}.folders
            """
        else:
            query = f"""
                SELECT name AS folder_type
                FROM project_{self.project_name}.folder_types
                ORDER BY position
            """
        return [
            FolderType(name=row["folder_type"]) async for row in Postgres.iterate(query)
        ]

    @strawberry.field
    async def subset_families(self) -> list[str]:
        return [
            row["family"]
            async for row in Postgres.iterate(
                f"""
                SELECT DISTINCT(family)
                FROM project_{self.project_name}.subsets
            """
            )
        ]


def project_from_record(record: dict, context: dict) -> ProjectNode:
    """Construct a project node from a DB row."""
    return ProjectNode(
        name=record["name"],
        code=record["code"],
        project_name=record["name"],
        active=record["active"],
        library=record["library"],
        attrib=parse_attrib_data(
            ProjectAttribType,
            record["attrib"],
            user=context["user"],
            project_name=record["name"],
        ),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


setattr(ProjectNode, "from_record", staticmethod(project_from_record))