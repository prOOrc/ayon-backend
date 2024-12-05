from pydantic import validator

from ayon_server.settings.common import BaseSettingsModel
from ayon_server.settings.settings_field import SettingsField


class TaskType(BaseSettingsModel):
    _layout: str = "compact"
    name: str = SettingsField(..., title="Name", min_length=1, max_length=100)
    shortName: str = SettingsField("", title="Short name")
    icon: str = SettingsField("task_alt", title="Icon", widget="icon")

    # Set to old name when renaming
    original_name: str | None = SettingsField(None, title="Original name", scope=[])

    def __hash__(self):
        return hash(self.name)

    @validator("original_name")
    def validate_original_name(cls, v, values):
        if v is None:
            return values["name"]
        return v


default_task_types = [
    TaskType(name="Generic", shortName="gener", icon="task_alt"),
    TaskType(name="Art", shortName="art", icon="palette"),
    TaskType(name="Modeling", shortName="mdl", icon="language"),
    TaskType(name="Texture", shortName="tex", icon="brush"),
    TaskType(name="Lookdev", shortName="look", icon="ev_shadow"),
    TaskType(name="Rigging", shortName="rig", icon="construction"),
    TaskType(name="Edit", shortName="edit", icon="imagesearch_roller"),
    TaskType(name="Layout", shortName="lay", icon="nature_people"),
    TaskType(name="Setdress", shortName="dress", icon="scene"),
    TaskType(name="Animation", shortName="anim", icon="directions_run"),
    TaskType(name="FX", shortName="fx", icon="fireplace"),
    TaskType(name="Lighting", shortName="lgt", icon="highlight"),
    TaskType(name="Paint", shortName="paint", icon="video_stable"),
    TaskType(name="Compositing", shortName="comp", icon="layers"),
    TaskType(name="Roto", shortName="roto", icon="gesture"),
    TaskType(name="Matchmove", shortName="matchmove", icon="switch_video"),
]
