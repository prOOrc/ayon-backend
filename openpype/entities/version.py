from typing import NoReturn

from openpype.entities.core import ProjectLevelEntity, attribute_library
from openpype.entities.models import ModelSet
from openpype.exceptions import ConstraintViolationException
from openpype.lib.postgres import Postgres
from openpype.types import ProjectLevelEntityType


class VersionEntity(ProjectLevelEntity):
    entity_type: ProjectLevelEntityType = "version"
    model = ModelSet("version", attribute_library["version"])

    async def save(self, transaction=False) -> None:
        """Save entity to database."""

        if self.version < 0:
            # Ensure there is no previous hero version
            res = await Postgres.fetch(
                f"""
                SELECT id FROM project_{self.project_name}.versions
                WHERE
                    version < 0
                AND id != $1
                AND subset_id = $2
                """,
                self.id,
                self.subset_id,
            )
            if res:
                raise ConstraintViolationException("Hero version already exists.")

        await super().save(transaction=transaction)

    async def commit(self, transaction=False) -> None:
        """Refresh hierarchy materialized view on folder save."""

        transaction = transaction or Postgres
        await transaction.execute(
            f"""
            REFRESH MATERIALIZED VIEW CONCURRENTLY
            project_{self.project_name}.version_list
            """
        )

    #
    # Properties
    #

    @property
    def name(self) -> str:
        return f"v{self.version:03d}"

    @name.setter
    def name(self, value) -> NoReturn:
        raise AttributeError("Cannot set name of version.")

    @property
    def version(self) -> int:
        return self._payload.version

    @version.setter
    def version(self, value: int) -> None:
        self._payload.version = value

    @property
    def subset_id(self) -> str:
        return self._payload.subset_id

    @subset_id.setter
    def subset_id(self, value: str) -> None:
        self._payload.subset_id = value

    @property
    def task_id(self) -> str:
        return self._payload.task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        self._payload.task_id = value

    @property
    def thumbnail_id(self) -> str:
        return self._payload.thumbnail_id

    @thumbnail_id.setter
    def thumbnail_id(self, value: str) -> None:
        self._payload.thumbnail_id = value

    @property
    def author(self) -> str:
        return self._payload.author
