import avahi
import dbus
import dbus.glib

__all__ = ["ZeroconfService"]

class ZeroconfService:
    """A simple class to publish a network service with zeroconf using avahi.
    """

    def __init__(self, name, port, stype="_http._tcp",domain="", host="", text="", newserviceCallback=None, removeserviceCallback=None):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text
        self.bus = dbus.SystemBus()
        self.server = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME,avahi.DBUS_PATH_SERVER),avahi.DBUS_INTERFACE_SERVER)
        self.group = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME,self.server.EntryGroupNew()),avahi.DBUS_INTERFACE_ENTRY_GROUP)
        self.group.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,dbus.UInt32(0),self.name, self.stype, self.domain, self.host,dbus.UInt16(self.port), self.text)
        self.group.Commit()
        self.browser = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, self.server.ServiceBrowserNew(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, self.stype, self.domain, dbus.UInt32(0))),avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        if callable(newserviceCallback):
            self.browser.connect_to_signal('ItemNew', newserviceCallback)
        if callable(removeserviceCallback):
            self.browser.connect_to_signal('ItemRemove', removeserviceCallback)

        
    def unpublish(self):
        self.group.Reset()