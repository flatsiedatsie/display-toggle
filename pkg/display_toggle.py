"""Display toggle adapter for Mozilla WebThings Gateway."""


from gateway_addon import Adapter, Device, Property
from os import path
import json
import os
import subprocess
import sys
import time

#sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

import requests  # noqa


__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

#_CONFIG_PATHS = [
#    os.path.join(os.path.expanduser('~'), '.mozilla-iot', 'config'),
#]

#if 'MOZIOT_HOME' in os.environ:
#    _CONFIG_PATHS.insert(0, os.path.join(os.environ['MOZIOT_HOME'], 'config'))


class DisplayToggleAdapter(Adapter):
    """Adapter for Internet Radio"""

    def __init__(self, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """

        #print("initialising adapter from class")
        self.pairing = False
        self.addon_name = 'display-toggle'
        self.DEBUG = True
        self.name = self.__class__.__name__
        Adapter.__init__(self, self.addon_name, self.addon_name, verbose=verbose)


        self.addon_path = os.path.join(os.path.expanduser('~'), '.mozilla-iot', 'addons', self.addon_name)
        #self.persistence_file_path = os.path.join(os.path.expanduser('~'), '.mozilla-iot', 'data', self.addon_name,'persistence.json')

        try:
            self.display_toggle = DisplayToggleDevice(self)
            self.handle_device_added(self.display_toggle)
            if self.DEBUG:
                print("display_toggle device created")

        except Exception as ex:
            print("Could not create display_toggle device: " + str(ex))


#
# MAIN SETTING OF THE STATES
#


    def set_signal_state(self,signal):
        if self.DEBUG:
            print("Setting display signal to " + str(signal))
        try:
            #if bool(power) != bool(self.persistent_data['signal']):
            #self.persistent_data['signal'] = bool(signal)
            #self.save_persistent_data()

            if signal:
                os.system("vcgencmd display_power 1")
                self.set_signal_property(bool(signal))
                
            else:
                os.system("vcgencmd display_power 0")    
                self.set_signal_property(bool(signal))

        except Exception as ex:
            print("Error setting display signal state: " + str(ex))


    # brightness currently not implemented
    def set_brightness(self,brightness):
        if self.DEBUG:
            print("Setting brightness to " + str(brightness))
        #if int(volume) != self.persistent_data['volume']:
        #    self.persistent_data['volume'] = int(volume)
        #    self.save_persistent_data()

        try:
            #if sys.platform == 'darwin':
            #    command = \
            #        'osascript -e \'set volume output volume {}\''.format(
            #            volume
            #        )
            #else:
            command = 'echo {} > /sys/class/backlight/rpi_backlight/brightness'.format(brightness)

            if self.DEBUG:
                print("Command to change brightness: " + str(command))

            os.system(command)

            if self.DEBUG:
                print("New brightness has been set")
        except Exception as ex:
            print("Error trying to set brightness: " + str(ex))

        self.set_brightness_property(brightness)


#
# SUPPORT METHODS
#


    def set_signal_property(self, signal):
        if self.DEBUG:
            print("new display state on thing: " + str(signal))
        try:
            if self.devices['display-toggle'] != None:
                self.devices['display-toggle'].properties['signal'].update( bool(signal) )
        except Exception as ex:
            print("Error setting signal state:" + str(ex))


    def set_brightness_property(self, brightness):
        if self.DEBUG:
            print("new brightness: " + str(brightness))
        try:
            if self.devices['display-toggle'] != None:
                self.devices['display-toggle'].properties['brightness'].update( int(brightness) )
        except Exception as ex:
            print("Error setting brightness:" + str(ex))






    def unload(self):
        if self.DEBUG:
            print("Shutting down display toggle.")
        self.set_display_state(1)



    def remove_thing(self, device_id):
        try:
            self.set_display_state(1)
            obj = self.get_device(device_id)
            self.handle_device_removed(obj)                     # Remove from device dictionary
            if self.DEBUG:
                print("User removed Display toggle thing")
        except:
            print("Could not remove Display toggle thing from devices")






#
# DEVICE
#

class DisplayToggleDevice(Device):
    """Candle device type."""

    def __init__(self, adapter):
        """
        Initialize the object.
        adapter -- the Adapter managing this device
        """

        Device.__init__(self, adapter, 'display-toggle')

        self._id = 'display-toggle'
        self.id = 'display-toggle'
        self.adapter = adapter

        self.name = 'Display'
        self.title = 'Display'
        self.description = 'Turn the display on and off'
        
        self._type = ['OnOffSwitch']

        try:

            self.properties["signal"] = DisplayToggleProperty(
                            self,
                            "signal",
                            {
                                '@type': 'OnOffProperty',
                                'label': "Signal",
                                'type': 'boolean'
                            },
                            True) # set the display to on at init

        except Exception as ex:
            print("error adding properties: " + str(ex))

        print("Display toggle thing has been created.")



#
# PROPERTY
#

class DisplayToggleProperty(Property):

    def __init__(self, device, name, description, value):
        Property.__init__(self, device, name, description)
        self.device = device
        self.name = name
        self.title = name
        self.description = description # dictionary
        self.value = value
        self.set_cached_value(value)



    def set_value(self, value):
        #print("property: set_value called for " + str(self.title))
        #print("property: set value to: " + str(value))
        try:
            if self.title == 'signal':
                self.device.adapter.set_signal_state(bool(value))
                #self.update(value)

            if self.title == 'brightness':
                self.device.adapter.set_brightness(int(value))
                #self.update(value)

        except Exception as ex:
            print("set_value error: " + str(ex))



    def update(self, value):
        #print("property -> update")
        #if value != self.value:
        self.value = value
        self.set_cached_value(value)
        self.device.notify_property_changed(self)
