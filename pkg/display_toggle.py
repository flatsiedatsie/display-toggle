"""Display toggle adapter for WebThings Gateway."""


from gateway_addon import Adapter, Device, Property, Database

import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import json
import time
import subprocess

_TIMEOUT = 3

_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.webthings', 'config'),
]

if 'WEBTHINGS_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['WEBTHINGS_HOME'], 'config'))


class DisplayToggleAdapter(Adapter):
    """Adapter for Display Toggle"""

    def __init__(self, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """

        #print("initialising adapter from class")
        self.pairing = False
        self.addon_name = 'display-toggle'
        self.DEBUG = False
        self.name = self.__class__.__name__
        Adapter.__init__(self, self.addon_name, self.addon_name, verbose=verbose)

        #print(str(os.uname()))

        if os.path.isfile('/boot/debug_display_toggle.txt'):
            self.DEBUG = True

        self.running = True
        self.addon_path = os.path.join(self.user_profile['addonsDir'], self.addon_name)
        self.persistence_file_path = os.path.join(self.user_profile['dataDir'], self.addon_name,'persistence.json')

        self.persistent_data = {'display':True, 'brightness':100,'rotation':'0'}
        self.user_action_occured = False # set to true if the user manually toggles something (in the first 90 seconds).
        self.do_not_turn_on_initially = False # User may disabe the safety feature where the screen always turns on for the first 90 seconds.
        
        self.backlight = False # whether the Pi's display has hardware backlight control
        
        self.screen_width  = run_command('cat /sys/class/graphics/fb0/virtual_size | cut -d, -f1')
        self.screen_height = run_command('cat /sys/class/graphics/fb0/virtual_size | cut -d, -f2')
        
        self.screen_width = self.screen_width.replace('\n','')
        self.screen_height = self.screen_height.replace('\n','')
        
        self.pi4 = False
        try:
            
            fd = os.open("/sys/firmware/devicetree/base/model",os.O_RDONLY)
	
            ret = os.read(fd,15)
            #print("Pi version: " + str(ret))
            if "Raspberry Pi 4" in str(ret):
                if self.DEBUG:
                    print("it's a Raspberry Pi 4")
                self.pi4 = True
            os.close(fd)
            
        except Exception as ex:
            print("Error getting pi version: " + str(ex))
        
        
        try:
            self.persistence_file_dir = os.path.join(self.user_profile['dataDir'], self.addon_name)
            self.persistence_file_path = os.path.join(self.user_profile['dataDir'], self.addon_name, 'persistence.json')
            if not os.path.isdir(self.persistence_file_dir):
                os.mkdir(self.persistence_file_dir)
            
            if not os.path.isfile(self.persistence_file_path):
                self.save_persistent_data()
        
            with open(self.persistence_file_path) as f:
                self.persistent_data = json.load(f)
                if self.DEBUG:
                    print("Persistence data was loaded succesfully.")
        
        except Exception as ex:
            print("Error reading persistent data: " + str(ex))
        
        
        # Read configuration settings
        self.add_from_config()
        
        
        try:
            self.display_toggle = DisplayToggleDevice(self)
            self.handle_device_added(self.display_toggle)
            
            self.display_toggle = self.get_device('display-toggle')
            self.display_toggle.connected_notify(True)
            if self.DEBUG:
                print("display_toggle device created")

        except Exception as ex:
            print("Could not create display_toggle device: " + str(ex))


        if os.path.isdir('/sys/class/backlight/rpi_backlight'):
            self.backlight = True
            self.set_brightness(self.persistent_data['brightness'])
        
        if self.pi4:
            self.set_rotation(self.persistent_data['rotation'])

        if self.do_not_turn_on_initially == False:
            #if self.DEBUG:
            if self.DEBUG:
                print("display toggle is waiting 90 seconds")
            self.set_power_state(True) # ALWAYS turn on the display for the first 90 seconds.
            #if self.persistent_data['display'] == True:
            #    self.set_power_state(self.persistent_data['display'])
            #else:
            time.sleep(90)
            if self.user_action_occured == False:
                self.set_power_state(self.persistent_data['display'])
        else:
            self.set_power_state(self.persistent_data['display'])


        # Detect when the user powers down the touch screen, and restore screen rotation afterwards
        self.previous_keyboard_count = 0
        #print("ok")
        while self.running:
            found_keyboards = 0
            
            keyboards = run_command('ls -l /dev/input/by-id/*-mouse')
            
            if 'No such file or directory' in keyboards:
                #print("no keyboards")
                pass
            else:
                keyboards = keyboards.strip().split('\n')
                found_keyboards = len(keyboards)
                #print("keyboards array: " + str(len(keyboards)))
            
            if found_keyboards != self.previous_keyboard_count:
                self.previous_keyboard_count = found_keyboards
                #print("keyboard count changed")
                self.set_power_state(self.persistent_data['display'])
            time.sleep(2)

#
#  ADD FROM CONFIG
#

    def add_from_config(self):
        """Attempt to load configuration."""
        try:
            database = Database(self.addon_name)
            if not database.open():
                print("Error. Could not open settings database")
                return

            config = database.load_config()
            database.close()

        except Exception as ex:
            print("Error. Failed to open settings database. Closing proxy: " + str(ex))
            self.close_proxy()
            
        try:
            if not config:
                return

            if 'Debugging' in config:
                #print("-Debugging was in config")
                self.DEBUG = bool(config['Debugging'])
                if self.DEBUG:
                    print("Debugging enabled")

            if 'Do not turn on initially' in config:
                #print("-Debugging was in config")
                self.do_not_turn_on_initially = bool(config['Do not turn on initially'])
                if self.DEBUG:
                    print("Do not turn on initially preference was in config: " + str(self.do_not_turn_on_initially))

            if self.DEBUG:
                print(str(config))
                
        except Exception as ex:
            print("Error reading config: " + str(ex))












#
# MAIN SETTING OF THE STATES
#


    def set_power_state(self,power):
        if self.DEBUG:
            print("Setting display power to " + str(power))
            
        self.persistent_data['display'] = power
        self.save_persistent_data()
        
        try:
            #if bool(power) != bool(self.persistent_data['power']):
            #self.persistent_data['power'] = bool(power)
            #self.save_persistent_data()

            if power:
                os.system("vcgencmd display_power 1")
                #os.system("DISPLAY=:0 xset dpms force on")
                os.system("DISPLAY=:0 xset -dpms")
                os.system("DISPLAY=:0 xset s off")
                os.system("DISPLAY=:0 xset s noblank")
                self.set_power_property(bool(power))
                
                # restore rotation too
                self.set_rotation( self.persistent_data['rotation'] )
                
            else:
                os.system("vcgencmd display_power 0")
                #os.system("DISPLAY=:0 xset dpms force off")    
                self.set_power_property(bool(power))

        except Exception as ex:
            if self.DEBUG:
                print("Error setting display power state: " + str(ex))


    # brightness currently not implemented
    def set_brightness(self,brightness):
        if self.DEBUG:
            print("Setting brightness to " + str(brightness))
        #if int(volume) != self.persistent_data['volume']:
        #    self.persistent_data['volume'] = int(volume)
        #    self.save_persistent_data()

        try:
            self.persistent_data['brightness'] = brightness
            self.save_persistent_data()
            
            #if sys.platform == 'darwin':
            #    command = \
            #        'osascript -e \'set volume output volume {}\''.format(
            #            volume
            #        )
            #else:
            if self.backlight:
                byte_brightness = int(brightness * 2.5)
                command = 'echo {} > /sys/class/backlight/rpi_backlight/brightness'.format(byte_brightness)
            else:
                decimal_brightness = brightness / 100
                command = 'DISPLAY=:0 xrandr --output HDMI-1 --brightness {}'.format(decimal_brightness, '.1f')


            if self.DEBUG:
                print("Command to change brightness: " + str(command))

            os.system(command)

            if self.DEBUG:
                print("New brightness has been set")
        except Exception as ex:
            if self.DEBUG:
                print("Error while trying to set brightness: " + str(ex))

        self.set_brightness_property(brightness)



    def set_rotation(self,degrees):
        if self.DEBUG:
            print("changing rotation to: " + str(degrees))
            
        try:
            self.persistent_data['rotation'] = str(degrees)
            self.save_persistent_data()
            
            if int(degrees) == 0:
                os.system("DISPLAY=:0 xrandr --output HDMI-1 --rotate normal")
                os.system("DISPLAY=:0 xinput --set-prop 'ILITEK ILITEK-TP' 'Coordinate Transformation Matrix' 1 0 0 0 1 0 0 0 1")
                os.system("DISPLAY=:0 xinput --set-prop 'HID 222a:0001' 'Coordinate Transformation Matrix' 1 0 0 0 1 0 0 0 1")
                
            elif int(degrees) == 90:
                os.system("DISPLAY=:0 xrandr --output HDMI-1 --rotate left")
                os.system("DISPLAY=:0 xinput --set-prop 'ILITEK ILITEK-TP' 'Coordinate Transformation Matrix' 0 -1 1 1 0 0 0 0 1")
                os.system("DISPLAY=:0 xinput --set-prop 'HID 222a:0001' 'Coordinate Transformation Matrix' 0 -1 1 1 0 0 0 0 1")
                
            elif int(degrees) == 180:
                os.system("DISPLAY=:0 xrandr --output HDMI-1 --rotate inverted")
                os.system("DISPLAY=:0 xinput --set-prop 'ILITEK ILITEK-TP' 'Coordinate Transformation Matrix' -1 0 1 0 -1 1 0 0 1")
                os.system("DISPLAY=:0 xinput --set-prop 'HID 222a:0001' 'Coordinate Transformation Matrix' -1 0 1 0 -1 1 0 0 1")
                
            elif int(degrees) == 270:
                os.system("DISPLAY=:0 xrandr --output HDMI-1 --rotate right")
                os.system("DISPLAY=:0 xinput --set-prop 'ILITEK ILITEK-TP' 'Coordinate Transformation Matrix' 0 1 0 -1 0 1 0 0 1")
                os.system("DISPLAY=:0 xinput --set-prop 'HID 222a:0001' 'Coordinate Transformation Matrix' 0 1 0 -1 0 1 0 0 1")
                
                
            if int(degrees) == 180:
                os.system("sudo touch /boot/rotate180.txt")
            else:
                if os.path.isfile('/boot/rotate180.txt'):
                    os.system("sudo rm /boot/rotate180.txt")
                
            
        except Exception as ex:
            if self.DEBUG:
                print("Error trying to set rotation: " + str(ex))
            
        self.set_rotation_property(str(degrees))

            
#
# SUPPORT METHODS
#


    def set_power_property(self, power):
        if self.DEBUG:
            print("new display state on thing: " + str(power))
        try:
            if self.devices['display-toggle'] != None:
                self.devices['display-toggle'].properties['power'].update( bool(power) )
        except Exception as ex:
            print("Error setting power state property: " + str(ex))


    def set_brightness_property(self, brightness):
        if self.DEBUG:
            print("new brightness: " + str(brightness))
        try:
            if self.devices['display-toggle'] != None:
                self.devices['display-toggle'].properties['brightness'].update( int(brightness) )
        except Exception as ex:
            print("Error setting brightness property: " + str(ex))


    def set_rotation_property(self, rotation):
        if self.DEBUG:
            print("new rotation: " + str(rotation))
        try:
            #print(str(dir(self.devices['display-toggle'].properties)))
            if self.devices['display-toggle'] != None:
                if 'rotation' in self.devices['display-toggle'].properties:
                    self.devices['display-toggle'].properties['rotation'].update( str(rotation) )
                else:
                    if self.DEBUG:
                        print('rotation was not a property')
        except Exception as ex:
            print("Error setting rotation property: " + str(ex))




    def unload(self):
        if self.DEBUG:
            print("Shutting down display toggle.")
        self.running = False
        self.set_power_state(1)



    def remove_thing(self, device_id):
        try:
            self.set_power_state(1)
            obj = self.get_device(device_id)
            self.handle_device_removed(obj)                     # Remove from device dictionary
            if self.DEBUG:
                print("User removed Display toggle thing")
        except:
            print("Could not remove Display toggle thing from devices")




#
#  SAVE TO PERSISTENCE
#

    def save_persistent_data(self):
        #if self.DEBUG:
        #print("Saving persistence data to file: " + str(self.persistence_file_path))
            
        try:
            if not os.path.isfile(self.persistence_file_path):
                open(self.persistence_file_path, 'a').close()
                if self.DEBUG:
                    print("Created an empty persistence file")

            with open(self.persistence_file_path) as f:
                if self.DEBUG:
                    print("saving persistent data: " + str(self.persistent_data))
                json.dump( self.persistent_data, open( self.persistence_file_path, 'w+' ) )
                return True

        except Exception as ex:
            print("Error: could not store data in persistent store: " + str(ex) )
            return False







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
        
        #self._type = ['OnOffSwitch']

        try:

            self.properties["power"] = DisplayToggleProperty(
                            self,
                            "power",
                            {
                            #    '@type': 'OnOffProperty',
                                'label': "State",
                                'title': "State",
                                'type': 'boolean'
                            },
                            self.adapter.persistent_data['display']) # set the display to on at init


        except Exception as ex:
            print("error adding power property: " + str(ex))
            

        try:
            if os.path.isdir('/sys/class/backlight/rpi_backlight'):
                self.properties["brightness"] = DisplayToggleProperty(
                                self,
                                "brightness",
                                {
                                    "@type": "BrightnessProperty",
                                    "type": "integer",
                                    "title": "Brightness",
                                    "description": "The level of light from 0-100",
                                    "minimum" : 0,
                                    "maximum" : 100
                                },
                                self.adapter.persistent_data['brightness'])
                self._type.append('MultiLevelSwitch')
                            
                            
        except Exception as ex:
            print("error adding brightness property: " + str(ex))
                            
        try:
            if self.adapter.pi4:
                self.properties["rotation"] = DisplayToggleProperty(
                                self,
                                "rotation",
                                {
                                    "type": "string",
                                    'enum': ['0','90','180','270'],
                                    "title": "Rotation",
                                    "description": "The prefered rotation of the display"
                                },
                                str(self.adapter.persistent_data['rotation']))

        except Exception as ex:
            print("error adding rotation property: " + str(ex))

        if self.adapter.DEBUG:
            print("self.adapter.screen_width: " + str(self.adapter.screen_width))
            print("type(self.adapter.screen_width): " + str(type(self.adapter.screen_width)))
            print("self.adapter.screen_width.isdigit(): ", self.adapter.screen_width.isdigit())
        
        if self.adapter.screen_width.isdigit() and self.adapter.screen_height.isdigit():
            
            self.properties["width"] = DisplayToggleProperty(
                            self,
                            "width",
                            {
                                'title': "Width",
                                'type': 'integer',
                                'readOnly': True
                            },
                            int(self.adapter.screen_width))
                        
            self.properties["height"] = DisplayToggleProperty(
                            self,
                            "height",
                            {
                                'title': "Height",
                                'type': 'integer',
                                'readOnly': True
                            },
                            int(self.adapter.screen_height))




        if self.adapter.DEBUG:
            print("Display toggle thing has been prepared.")



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
        if self.device.adapter.DEBUG:
            print("property: set_value called for " + str(self.title))
            print("property: set_value to: " + str(value))
        try:
            if self.title == 'power':
                self.device.adapter.set_power_state(bool(value))
                #self.update(value)

            if self.title == 'brightness':
                self.device.adapter.set_brightness(int(value))
                #self.update(value)
                
            if self.title == 'rotation':
                self.device.adapter.set_rotation(str(value))

        except Exception as ex:
            print("set_value error: " + str(ex))

        
        self.device.adapter.user_action_occured = True



    def update(self, value):
        if self.device.adapter.DEBUG:
            print("property -> update: " + str(value))
        if value != self.value:
            self.value = value
            self.set_cached_value(value)
            self.device.notify_property_changed(self)







def run_command(cmd, timeout_seconds=20):
    try:
        
        p = subprocess.run(cmd, timeout=timeout_seconds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)

        if p.returncode == 0:
            return p.stdout # + '\n' + "Command success" #.decode('utf-8')
            #yield("Command success")
        else:
            if p.stderr:
                return "Error: " + str(p.stderr)  + '\n' + "Command failed"   #.decode('utf-8'))

    except Exception as e:
        print("Error running command: "  + str(e))