"""Config flow for the EZHU KVM48 Power System integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback

from .const import (
    CONF_FACTORY_PASSWORD,
    DEFAULT_FACTORY_PASSWORD,
    DEFAULT_HOST,
    DEFAULT_NAME,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .wake_client import EzhuKvmClient, EzhuKvmError, KvmInfoEx, discover_kvm_devices

if TYPE_CHECKING:
    from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

_LOGGER = logging.getLogger(__name__)


class EzhuKvmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EZHU KVM48 Power System."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._discovered_host: str | None = None
        self._discovered_port: int = DEFAULT_PORT
        self._discovered_info: KvmInfoEx | None = None
        self._discovered_devices: dict[str, KvmInfoEx] = {}
        self._pending_config: dict[str, Any] = {}

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle automatic discovery via Home Assistant DHCP / ARP watcher."""
        host = discovery_info.ip
        port = DEFAULT_PORT

        client = EzhuKvmClient(host=host, port=port, timeout=2.5)
        try:
            info = await self.hass.async_add_executor_job(client.get_info_ex)
        except Exception as err:
            _LOGGER.debug(
                "DHCP candidate %s did not respond to EZHU KVM48 WAKE probe: %s",
                host,
                err,
            )
            return self.async_abort(reason="cannot_connect")

        unique_id = info.serial_number or f"{host}:{port}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._discovered_host = host
        self._discovered_port = port
        self._discovered_info = info

        display_name = (
            f"{info.dev_name or DEFAULT_NAME} ({info.hostname or host})"
        )
        self.context["title_placeholders"] = {
            "name": display_name,
            "host": host,
        }
        return await self.async_step_dhcp_confirm()

    async def async_step_dhcp_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup of a DHCP-discovered EZHU KVM48 controller."""
        assert self._discovered_host is not None
        assert self._discovered_info is not None
        info = self._discovered_info
        host = self._discovered_host
        port = self._discovered_port

        if user_input is not None:
            title = f"{info.dev_name or DEFAULT_NAME} ({info.hostname or host})"
            return self.async_create_entry(
                title=title,
                data={
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_PASSWORD: user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                    CONF_FACTORY_PASSWORD: user_input.get(
                        CONF_FACTORY_PASSWORD, DEFAULT_FACTORY_PASSWORD
                    ),
                    CONF_SCAN_INTERVAL: int(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                vol.Optional(
                    CONF_FACTORY_PASSWORD, default=DEFAULT_FACTORY_PASSWORD
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=2, max=3600)),
            }
        )
        return self.async_show_form(
            step_id="dhcp_confirm",
            data_schema=schema,
            description_placeholders={
                "name": info.dev_name or DEFAULT_NAME,
                "hostname": info.hostname or host,
                "host": host,
                "serial_number": info.serial_number or "unknown",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (direct host entry or automatic LAN scan if host left empty)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = (user_input.get(CONF_HOST) or "").strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            password = user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)
            factory_password = user_input.get(
                CONF_FACTORY_PASSWORD, DEFAULT_FACTORY_PASSWORD
            )
            scan_interval = int(
                user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            )

            if not host:
                # Active LAN / ARP discovery on TCP port 1001
                discovered = await self.hass.async_add_executor_job(
                    discover_kvm_devices, port
                )
                configured_ids = {
                    entry.unique_id
                    for entry in self._async_current_entries()
                    if entry.unique_id
                }
                unconfigured: dict[str, KvmInfoEx] = {}
                for ip_str, info in discovered:
                    uid = info.serial_number or f"{ip_str}:{port}"
                    if uid not in configured_ids:
                        unconfigured[ip_str] = info

                if not unconfigured:
                    errors["base"] = (
                        "already_configured" if discovered else "no_devices_found"
                    )
                elif len(unconfigured) == 1:
                    ip_str, info = next(iter(unconfigured.items()))
                    unique_id = info.serial_number or f"{ip_str}:{port}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    title = (
                        f"{info.dev_name or DEFAULT_NAME} "
                        f"({info.hostname or ip_str})"
                    )
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_HOST: ip_str,
                            CONF_PORT: port,
                            CONF_PASSWORD: password,
                            CONF_FACTORY_PASSWORD: factory_password,
                            CONF_SCAN_INTERVAL: scan_interval,
                        },
                    )
                else:
                    self._discovered_devices = unconfigured
                    self._pending_config = {
                        CONF_PORT: port,
                        CONF_PASSWORD: password,
                        CONF_FACTORY_PASSWORD: factory_password,
                        CONF_SCAN_INTERVAL: scan_interval,
                    }
                    return await self.async_step_pick_device()
            else:
                client = EzhuKvmClient(
                    host=host,
                    port=port,
                    password=password,
                    factory_password=factory_password,
                )
                try:
                    info = await self.hass.async_add_executor_job(client.get_info_ex)
                except EzhuKvmError as err:
                    _LOGGER.warning(
                        "Failed to connect to EZHU KVM48 at %s:%s: %s",
                        host,
                        port,
                        err,
                    )
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error connecting to EZHU KVM48")
                    errors["base"] = "unknown"
                else:
                    unique_id = info.serial_number or f"{host}:{port}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    title = (
                        user_input.get(CONF_NAME)
                        or f"{info.dev_name or DEFAULT_NAME} ({info.hostname or host})"
                    )
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_PASSWORD: password,
                            CONF_FACTORY_PASSWORD: factory_password,
                            CONF_SCAN_INTERVAL: scan_interval,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                vol.Optional(
                    CONF_FACTORY_PASSWORD, default=DEFAULT_FACTORY_PASSWORD
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=2, max=3600)),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle picking a device when multiple EZHU KVM48 controllers are discovered."""
        if user_input is not None:
            host = user_input[CONF_HOST]
            info = self._discovered_devices[host]
            port = self._pending_config[CONF_PORT]
            unique_id = info.serial_number or f"{host}:{port}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            title = f"{info.dev_name or DEFAULT_NAME} ({info.hostname or host})"
            return self.async_create_entry(
                title=title,
                data={
                    CONF_HOST: host,
                    **self._pending_config,
                },
            )

        options = {
            ip_str: (
                f"{info.dev_name or DEFAULT_NAME} — {info.hostname or ip_str} "
                f"({ip_str}, S/N: {info.serial_number or 'N/A'})"
            )
            for ip_str, info in self._discovered_devices.items()
        }
        schema = vol.Schema({vol.Required(CONF_HOST): vol.In(options)})
        return self.async_show_form(step_id="pick_device", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EzhuKvmOptionsFlow:
        """Create the options flow."""
        return EzhuKvmOptionsFlow()


class EzhuKvmOptionsFlow(OptionsFlow):
    """Handle options flow for EZHU KVM48 Power System."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=current.get(CONF_HOST, DEFAULT_HOST)
                ): str,
                vol.Required(
                    CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(
                    CONF_PASSWORD,
                    default=current.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                ): str,
                vol.Optional(
                    CONF_FACTORY_PASSWORD,
                    default=current.get(
                        CONF_FACTORY_PASSWORD, DEFAULT_FACTORY_PASSWORD
                    ),
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=2, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
