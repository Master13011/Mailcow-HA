import pytest
from custom_components.mailcow.sensor import (
    MailcowVersionSensor,
    MailcowMailboxCountSensor,
    MailcowDomainCountSensor,
    MailcowVmailStatusSensor,
    MailcowContainersStatusSensor,
)

@pytest.mark.asyncio
async def test_sensors_native_value_and_attributes(coordinator):
    version_sensor = MailcowVersionSensor(coordinator)
    assert version_sensor.native_value == "v2.0"

    mailbox_sensor = MailcowMailboxCountSensor(coordinator)
    assert mailbox_sensor.native_value == 5

    domain_sensor = MailcowDomainCountSensor(coordinator)
    assert domain_sensor.native_value == 2

    vmail_sensor = MailcowVmailStatusSensor(coordinator)
    assert vmail_sensor.native_value == 50.0
    extra = vmail_sensor.extra_state_attributes
    assert extra["disk"] == "/dev/sda"

    containers_sensor = MailcowContainersStatusSensor(coordinator)
    state = containers_sensor.native_value
    assert state in ["All Running", "Issues Detected", "No Data", "Unknown"]
