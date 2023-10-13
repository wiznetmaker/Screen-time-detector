import board
import busio
import digitalio
import analogio
import time
from random import randint
from secrets import secrets
import LD2410B
import neopixel

from adafruit_wiznet5k.adafruit_wiznet5k import *
import adafruit_wiznet5k.adafruit_wiznet5k_socket as socket

from adafruit_io.adafruit_io import IO_MQTT
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

#Distance sensor
dist_sen = LD2410B.LD2410B(board.GP0,board.GP1)

#Adafruit IO Flag for reset 
flag = digitalio.DigitalInOut(board.GP3)
flag.direction = digitalio.Direction.OUTPUT

#Neopixel for LED notification
pixel_pin = board.GP2
num_pixels = 12
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=10, auto_write=False)
pixels.fill((0,0,0)) # set to turn off the pixel
pixels.show() #present to off

#SPI
SPI0_SCK = board.GP18
SPI0_TX = board.GP19
SPI0_RX = board.GP16
SPI0_CSn = board.GP17

#Reset
W5x00_RSTn = board.GP20


print("Wiznet5k Adafruit Up&Down Link Test (DHCP)")
# Setup your network configuration below
# random MAC, later should change this value on your vendor ID
MY_MAC = (0x00, 0x01, 0x02, 0x03, 0x04, 0x05)
IP_ADDRESS = (192, 168, 1, 100)
SUBNET_MASK = (255, 255, 255, 0)
GATEWAY_ADDRESS = (192, 168, 1, 1)
DNS_SERVER = (8, 8, 8, 8)

ethernetRst = digitalio.DigitalInOut(W5x00_RSTn)
ethernetRst.direction = digitalio.Direction.OUTPUT

# For Adafruit Ethernet FeatherWing
cs = digitalio.DigitalInOut(SPI0_CSn)
# For Particle Ethernet FeatherWing
# cs = digitalio.DigitalInOut(board.D5)

spi_bus = busio.SPI(SPI0_SCK, MOSI=SPI0_TX, MISO=SPI0_RX)

# Reset W5x00 first
ethernetRst.value = False
time.sleep(1)
ethernetRst.value = True

# # Initialize ethernet interface without DHCP
# eth = WIZNET5K(spi_bus, cs, is_dhcp=False, mac=MY_MAC, debug=False)
# # Set network configuration
# eth.ifconfig = (IP_ADDRESS, SUBNET_MASK, GATEWAY_ ADDRESS, DNS_SERVER)

# Initialize ethernet interface with DHCP
eth = WIZNET5K(spi_bus, cs, is_dhcp=True, mac=MY_MAC, debug=False)

print("Chip Version:", eth.chip)
print("MAC Address:", [hex(i) for i in eth.mac_address])
print("My IP address is:", eth.pretty_ip(eth.ip_address))

### Topic Setup ###
# Adafruit IO-style Topic
# Use this topic if you'd like to connect to io.adafruit.com
# mqtt_topic = secrets["aio_username"] + '/feeds/test'

#Global variable for collecting screen time from Adafruit IO to the main code
global time_recorder

### Code ###
# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client):
    # This function will be called when the mqtt_client is connected
    # successfully to the broker.
    print("Connected to Adafruit IO!")
    
    #Subscribe to Group
    #io.subscribe(group_key=group_name)
    io.subscribe("scale") 
    io.subscribe("test")
    io.subscribe("alert")
    io.subscribe("light")


def disconnected(client):
    # This method is called when the mqtt_client disconnects
    # from the broker.
    print("Disconnected from Adafruit IO!")

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))
    
def message(client, topic, message):
    global time_recorder
    # Method callled when a client's subscribed feed has a new value.
    print("New message 1 on topic {0}: {1}".format(topic, message))

#function to collect the screen time from adafruit IO
def waiting_time(client, topic, message):
    global time_recorder
    # Method callled when a client's subscribed feed has a new value.
    print("New message 2 on topic {0}: {1}".format(topic, message))
    time_recorder = int(message)

#function to collect reset response from adafruit IO
def reset(client, topic, message):
    # Method callled when a client's subscribed feed has a new value.
    print("New message on topic {0}: {1}".format(topic, message))
    if message == "0":
        flag.value = 1

#Main function to manage the screen time operation   
def scan(time_value,temp,counter,alert_counter,leave, led):
    global time_recorder
    
    #collect data function from LD2410B module library
    dist_sen.collect_data()
    #check the sensor's targetting object
    if dist_sen.target == "Both target":
        if dist_sen.move_dist >= dist_sen.stable_dist: #compare the distance - distance value is more accurate
            data = dist_sen.move_dist
        else:
            data = dist_sen.stable_dist 
    elif dist_sen.target == "Moving target": #If it detects the moving object, choose moving target
        data = dist_sen.move_dist
    elif dist_sen.target == "Stable target": #Since the distance between the module is short, stable target could be consider to use.
        data = dist_sen.stable_dist
        if data == 8: #if it shows 8 value, it means error.
            data = dist_sen.move_dist
    else:
        data = None # No target, just ignore
    
    if data != None
        # the range that I will be seated - If detected
        if data > 65 and data < 100: 
            leave = False # Turn off leave flag
            temp = time.time() #collect current time
            if time_value is None:
                time_value = temp # Starting Point 
            else: #check current status for LED display
                difference = temp - time_value
                if difference <= (time_recorder /3): #Beginning period with the screen
                    print ("Green Light")
                    pixels.fill((38,252,5)) # Display green light
                    pixels.show() 
                    led += 1
                    if led == 1: #Upload once to adafruit IO
                        io.publish("light", "#26fc05") #Upload green light status
                elif difference > (time_recorder /3) and difference < time_recorder: #it has been for a while with the screen
                    print ("Yellow Light")
                    if led >= 1:
                        led = 0
                    pixels.fill((250,242,7)) # Display Yellow Light
                    pixels.show() 
                    led -= 1
                    if led == -1: #Upload once to adafruit IO
                        io.publish("light", "#faf207")
                elif difference >= time_recorder: #If it has passed or equal to the waiting time
                    print("Over time! - Red Light") 
                    alert_counter += 1
                    if alert_counter == 1: #Activate the alert section
                        io.publish("alert", "OverTime") #posted to adafruit IO to show it has passed the screening time
                        io.publish("light", "#fc0905") #showed red on adafruit IO
                    pixels.fill((252,9,5)) # sDisplay Red Light
                    pixels.show() 
        else: #detected No one is in front of the screen
            if leave is False: #confirmed the previous moments are present in front of the screen 
                counter += 1 
                if temp is not None: #if the previous moment is present in front of the screen
                    counter  = 0 #reset counter
                    temp = None
                print (counter)
                if counter > 3: #if accumulated for 3 times, confirmed no one is in front of the screen.
                    #reset everything
                    temp = time.time()
                    difference = temp - time_value
                    print ("You have looked on the screen for {} seconds".format(difference))
                    counter = 0
                    time_value = None
                    temp = None
                    alert_counter = 0
                    leave = True
                    led = 0
                    pixels.fill((0,0,0)) # set to turn off the pixel
                    pixels.show() #present to off
                    io.publish("light", "#000000") 
                
    return time_value, temp, counter, alert_counter,leave,led


# Initialize MQTT interface with the ethernet interface
MQTT.set_socket(socket, eth)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    is_ssl=False,
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

# Setup the callback methods above
io.on_connect = connected
io.on_disconnect = disconnected
io.on_message = message
io.on_subscribe = subscribe

# Set up a callback for the led feed
io.add_feed_callback("scale", waiting_time) 
io.add_feed_callback("test", reset)

"""
# Group name
group_name = "neopixel"


# # Subscribe to all messages on the led feed
io.subscribe("neopixel.brightness")
"""
# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

time_value = None
temp = None
counter = 0
alert_counter = 0
leave = False
led = 0
io.get("scale") #get value from adafruit IO for screen time

# # Subscribe to all messages on the led feed
print("Connected to Adafruit !!")

while True:
    try:
        io.loop()
        #io.get("scale")
        if flag.value is True: #if found reset, reset
            print ("RESET")
            time_value = None
            temp = None
            counter = 0
            flag.value = 0
            alert_counter = 0
            leave = False
            led = 0
            pixels.fill((0,0,0)) # set to turn off the pixel
            pixels.show() #present to off
            io.publish("light", "#000000") 
            
        time_value, temp, counter, alert_counter,leave,led = scan(time_value,temp,counter,alert_counter,leave,led)
            
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        io.reconnect()
        continue
    time.sleep(0.01)