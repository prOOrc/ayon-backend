from ayon_server.api.dependencies import CurrentUser
from ayon_server.api.responses import EmptyResponse
from ayon_server.exceptions import ForbiddenException
from ayon_server.helpers.deploy_project import create_project_from_anatomy
from ayon_server.settings.anatomy import Anatomy
from ayon_server.types import Field, OPModel

from .router import router


class DeployProjectRequestModel(OPModel):
    name: str = Field(..., description="Project name")
    code: str = Field(..., description="Project code")
    anatomy: Anatomy = Field(..., description="Project anatomy")
    library: bool = Field(False, description="Library project")


@router.post("/projects", status_code=201)
async def deploy_project(
    payload: DeployProjectRequestModel, user: CurrentUser
) -> EmptyResponse:
    """Create a new project using the provided anatomy object.

    Main purpose is to take an anatomy object and transform its contents
    to the project entity (along with additional data such as the project name).
    """

    if not user.is_manager:
        raise ForbiddenException("Only managers can create projects")

    await create_project_from_anatomy(
        name=payload.name,
        code=payload.code,
        anatomy=payload.anatomy,
        library=payload.library,
        user_name=user.name,
    )

    return EmptyResponse(status_code=201)
