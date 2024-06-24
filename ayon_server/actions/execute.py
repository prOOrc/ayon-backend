import urllib.parse
from typing import Literal

from ayon_server.actions.context import ActionContext
from ayon_server.entities import UserEntity
from ayon_server.events import EventStream
from ayon_server.types import Field, OPModel
from ayon_server.utils import create_hash


class ExecuteResponseModel(OPModel):
    type: Literal["launcher", "void"] = Field(...)
    success: bool = Field(True)
    message: str | None = Field(None, description="The message to display")
    uri: str | None = Field(None, description="The uri to open in the browser")

    # TODO: for http/browser actions
    # payload: dict | None = Field(None, description="The payload of the request")


class ActionExecutor:
    user: UserEntity
    server_url: str
    access_token: str | None
    addon_name: str
    addon_version: str
    variant: str
    identifier: str
    context: ActionContext

    async def get_launcher_action_response(
        self,
        args: list[str],
        message: str | None = None,
    ) -> ExecuteResponseModel:
        """Return a response for a launcher action

        Launcher actions are actions that open the Ayon Launcher
        with the given arguments.

        An event is dispatched to the EventStream to track the progress of the action.
        The hash of the event is returned as a part of the URI.

        Uri is then used by the frontend to open the launcher.

        Launcher then uses the event hash to get the event details
        and update the event status.
        """
        payload = {
            "args": args,
            "variant": self.variant,
        }

        summary = {
            "addon_name": self.addon_name,
            "addon_version": self.addon_version,
            "variant": self.variant,
            "action_identifier": self.identifier,
        }

        hash = create_hash()

        await EventStream.dispatch(
            "action.launcher",
            hash=hash,
            description=message or "Running action",
            summary=summary,
            payload=payload,
            user=self.user.name,
            project=self.context.project_name,
            finished=False,
        )

        encoded_url = urllib.parse.quote_plus(self.server_url)

        return ExecuteResponseModel(
            success=True,
            type="launcher",
            uri=f"ayon-launcher://action?server_url={encoded_url}&token={hash}",
            message=message,
        )

    async def get_void_action_response(
        self,
        success: bool = True,
        message: str | None = None,
    ) -> ExecuteResponseModel:
        """Return a response for a void actions

        Void actions are actions that are only executed on the server.
        They only return a message to display in the frontend
        after the action is executed.
        """

        if message is None:
            message = f"Action {self.identifier} executed successfully"

        return ExecuteResponseModel(
            success=success,
            type="void",
            message=message,
            uri=None,
        )
