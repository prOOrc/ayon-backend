from ayon_server.entities.core import ProjectLevelEntity, attribute_library
from ayon_server.entities.models import ModelSet
from ayon_server.types import ProjectLevelEntityType


class SubsetEntity(ProjectLevelEntity):
    entity_type: ProjectLevelEntityType = "subset"
    model = ModelSet("subset", attribute_library["subset"])

    #
    # Properties
    #

    @property
    def folder_id(self) -> str:
        return self._payload.folder_id

    @folder_id.setter
    def folder_id(self, value: str):
        self._payload.folder_id = value

    @property
    def parent_id(self) -> str:
        return self.folder_id

    @property
    def family(self) -> str:
        return self._payload.family

    @family.setter
    def family(self, value: str):
        self._payload.family = value
