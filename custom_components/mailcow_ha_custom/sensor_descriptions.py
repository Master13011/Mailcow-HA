# sensor_descriptions.py

from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="version",
        name="Mailcow Version",
        icon="mdi:package-variant"
    ),
    SensorEntityDescription(
        key="mailbox_count",
        name="Mailbox Count",
        icon="mdi:email-multiple"
    ),
    SensorEntityDescription(
        key="domain_count",
        name="Domain Count",
        icon="mdi:domain"
    ),
    SensorEntityDescription(
        key="vmail_status",
        name="Vmail Usage",
        icon="mdi:harddisk",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="containers_status",
        name="Container Health",
        icon="mdi:docker"
    ),
)
