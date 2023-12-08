from ayon_server.lib.postgres import Postgres
from ayon_server.types import Field, OPModel


class ProjectCounts(OPModel):
    total: int = Field(0, title="Total projects", example=6)
    active: int = Field(0, title="Active projects", example=1)


class ProjectMetrics(OPModel):
    """Project metrics model"""

    folder_count: int = Field(0, title="Folder count", example=52)
    product_count: int = Field(0, title="Product count", example=587)
    version_count: int = Field(0, title="Version count", example=2348)
    representation_count: int = Field(0, title="Representation count", example=2888)
    task_count: int = Field(0, title="Task count", example=222)
    workfile_count: int = Field(0, title="Workfile count", example=323)
    root_count: int = Field(0, title="Root count", example=2)
    team_count: int = Field(0, title="Team count", example=2)
    duration: int = Field(
        0,
        title="Duration",
        description="Duration in days",
        example=30,
    )

    # Saturated metrics

    folder_types: list[str] | None = Field(
        None,
        title="Folder types",
        example=["Folder", "Asset", "Episode", "Sequence"],
    )
    task_types: list[str] | None = Field(
        None,
        title="Task types",
        example=["Art", "Modeling", "Texture", "Lookdev"],
    )
    statuses: list[str] | None = Field(
        None,
        title="Statuses",
        example=["Not ready", "In progress", "Pending review", "Approved"],
    )
    # Do not include tags (may be huge and sensitive)
    # tags: list[str] | None = Field(None, title="Tags")


async def get_project_counts(saturated: bool) -> ProjectCounts | None:
    """Number of total and active projects"""
    query = """
    SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE active) AS active
    FROM projects;
    """

    async for row in Postgres.iterate(query):
        return ProjectCounts(
            total=row["total"] or 0,
            active=row["active"] or 0,
        )
    return None


async def get_project_metrics(project_name: str, saturated: bool) -> ProjectMetrics:

    data = {}
    for entity_type in [
        "folder",
        "product",
        "version",
        "representation",
        "task",
        "workfile",
    ]:
        query = f"""
        SELECT COUNT(*) AS c
        FROM project_{project_name}.{entity_type}s
        """

        res = await Postgres.fetch(query)
        data[f"{entity_type}_count"] = res[0]["c"]

    # TODO: root_count, team_count, duration

    if saturated:
        for entity_type in ["folder", "task"]:
            query = f"""
            SELECT DISTINCT ({entity_type}_type) as t
            FROM project_{project_name}.{entity_type}s
            """

            res = await Postgres.fetch(query)
            data[f"{entity_type}_types"] = [r["t"] for r in res]

    return ProjectMetrics(**data)


async def get_projects(saturated: bool) -> list[ProjectMetrics]:
    """Project specific metrics

    Contain information about size and usage of each active project.
    """
    query = """
    SELECT name
    FROM projects
    WHERE active IS TRUE;
    """

    res = await Postgres.fetch(query)
    return [await get_project_metrics(r["name"], saturated) for r in res]


async def get_average_project_event_count(saturated: bool) -> int | None:
    """Average number of events per project

    This disregards projects with less than 300 events
    (such as testing projects).
    """

    query = """
        SELECT AVG(event_count) AS average_event_count_per_project
        FROM (
            SELECT project_name, COUNT(*) AS event_count
            FROM events
            GROUP BY project_name
            HAVING COUNT(*) >= 300 and project_name is not null
        ) AS subquery;
    """

    async for row in Postgres.iterate(query):
        res = row["average_event_count_per_project"]
        if not res:
            return None
        return int(res)
    return None