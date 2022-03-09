"""User entity."""

from openpype.access.permissions import Permissions
from openpype.access.roles import Roles
from openpype.exceptions import RecordNotFoundException
from openpype.lib.postgres import Postgres

from .common import Entity, EntityType, attribute_library
from .models import ModelSet


class UserEntity(Entity):
    entity_type = EntityType.USER
    entity_name = "user"
    model = ModelSet("user", attribute_library["user"], has_id=False)

    #
    # Load
    #

    @classmethod
    async def load(cls, name: str) -> "UserEntity":
        """Load a user from the database."""

        if not (
            user_data := await Postgres.fetch(
                "SELECT * FROM public.users WHERE name = $1", name
            )
        ):
            raise RecordNotFoundException()
        return cls.from_record(exists=True, validate=False, **dict(user_data[0]))

    #
    # Save
    #

    async def save(self, db=None) -> bool:
        """Save the user to the database."""
        pass

    #
    # Delete
    #

    async def delete(self, db=None) -> bool:
        """Delete existing user."""
        pass

    #
    # Authorization helpers
    #

    @property
    def is_admin(self) -> bool:
        return self._payload.data.get("roles", {}).get("admin", False)

    @property
    def is_manager(self) -> bool:
        return self._payload.data.get("roles", {}).get(
            "manager", False
        ) or self._payload.data.get("roles", {}).get("admin", False)

    def permissions(self, project_name: str) -> Permissions:
        """Return user permissions on a given project."""

        # TODO: consider caching this

        active_roles = []
        for role_name, projects in self._payload.data.get("roles", {}).items():
            if projects == "all" or (
                isinstance(projects, list) and project_name in projects
            ):
                active_roles.append(role_name)

        return Roles.combine(active_roles, project_name)
