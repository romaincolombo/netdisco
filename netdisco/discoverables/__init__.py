"""Provides helpful stuff for discoverables."""
# pylint: disable=abstract-method
from urllib.parse import urlparse

from ..const import (
    ATTR_NAME, ATTR_MODEL_NAME, ATTR_HOST, ATTR_PORT, ATTR_SSDP_DESCRIPTION,
    ATTR_SERIAL, ATTR_MODEL_NUMBER, ATTR_HOSTNAME, ATTR_PROPERTIES)


class BaseDiscoverable(object):
    """Base class for discoverable services or device types."""

    def is_discovered(self):
        """Return True if it is discovered."""
        return len(self.get_entries()) > 0

    def get_info(self):
        """Return a list with the important info for each item.

        Uses self.info_from_entry internally.
        """
        return [self.info_from_entry(entry) for entry in self.get_entries()]

    # pylint: disable=no-self-use
    def info_from_entry(self, entry):
        """Return an object with important info from the entry."""
        return entry

    # pylint: disable=no-self-use
    def get_entries(self):
        """Return all the discovered entries."""
        raise NotImplementedError()


class SSDPDiscoverable(BaseDiscoverable):
    """uPnP discoverable base class."""

    def __init__(self, netdis):
        """Initialize SSDPDiscoverable."""
        self.netdis = netdis

    def info_from_entry(self, entry):
        """Get most important info, by default the description location."""
        url = urlparse(entry.location)
        info = {
            ATTR_HOST: url.hostname,
            ATTR_PORT: url.port,
            ATTR_SSDP_DESCRIPTION: entry.location
        }
        device = entry.description.get('device')

        if device:
            info[ATTR_NAME] = device.get('friendlyName')
            info[ATTR_MODEL_NAME] = device.get('modelName')
            info[ATTR_MODEL_NUMBER] = device.get('modelNumber')
            info[ATTR_SERIAL] = device.get('serialNumber')

        return info

    # Helper functions

    # pylint: disable=invalid-name
    def find_by_st(self, st):
        """Find entries by ST (the device identifier)."""
        return self.netdis.ssdp.find_by_st(st)

    def find_by_device_description(self, values):
        """Find entries based on values from their description."""
        return self.netdis.ssdp.find_by_device_description(values)


class MDNSDiscoverable(BaseDiscoverable):
    """mDNS Discoverable base class."""

    def __init__(self, netdis, typ):
        """Initialize MDNSDiscoverable."""
        self.netdis = netdis
        self.typ = typ
        self.services = {}

        netdis.mdns.register_service(self)

    def reset(self):
        """Reset found services."""
        self.services.clear()

    def is_discovered(self):
        """Return True if any device has been discovered."""
        return len(self.get_entries()) > 0

    # pylint: disable=unused-argument
    def remove_service(self, zconf, typ, name):
        """Callback when a service is removed."""
        self.services.pop(name, None)

    def add_service(self, zconf, typ, name):
        """Callback when a service is found."""
        service = None
        tries = 0
        while service is None and tries < 3:
            service = zconf.get_service_info(typ, name)
            tries += 1

        if service is not None:
            self.services[name] = service

    def get_entries(self):
        """Return all found services."""
        return self.services.values()

    def info_from_entry(self, entry):
        """Return most important info from mDNS entries."""
        properties = {}

        for key, value in entry.properties.items():
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            properties[key.decode('utf-8')] = value

        return {
            ATTR_HOST: self.ip_from_host(entry.server),
            ATTR_PORT: entry.port,
            ATTR_HOSTNAME: entry.server,
            ATTR_PROPERTIES: properties,
        }

    def find_by_device_name(self, name):
        """Find entries based on the beginning of their entry names."""
        return [entry for entry in self.services.values()
                if entry.name.startswith(name)]

    def ip_from_host(self, host):
        """Attempt to return the ip address from an mDNS host.

        Return host if failed.
        """
        ips = self.netdis.mdns.zeroconf.cache.entries_with_name(host.lower())

        try:
            return repr(ips[0]) if ips else host
        except TypeError:
            return host


class GDMDiscoverable(BaseDiscoverable):
    """GDM discoverable base class."""

    def __init__(self, netdis):
        """Initialize GDMDiscoverable."""
        self.netdis = netdis

    def info_from_entry(self, entry):
        """Get most important info, by default the description location."""
        return {
            ATTR_HOST: entry.values['location'],
            ATTR_PORT: entry.values['port'],
        }

    def find_by_content_type(self, value):
        """Find entries based on values from their content_type."""
        return self.netdis.gdm.find_by_content_type(value)

    def find_by_data(self, values):
        """Find entries based on values from any returned field."""
        return self.netdis.gdm.find_by_data(values)
