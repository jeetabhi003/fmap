"""Department registry. pipeline.json names departments by these keys."""

from departments import (
    compliance, content, engine, intake, launch, leads, listings, matching, references, register, storyboard,
    video, web,
)

DEPARTMENTS = {
    module.NAME: module
    for module in (engine, intake, register, listings, references, matching, content, storyboard, video, web,
                   compliance, leads, launch)
}
