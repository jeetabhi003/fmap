"""Department registry. pipeline.json names departments by these keys."""

from departments import (
    compliance, content, engine, intake, launch, leads, listings, matching, references, register, web,
)

DEPARTMENTS = {
    module.NAME: module
    for module in (engine, intake, register, listings, references, matching, content, web, compliance, leads, launch)
}
