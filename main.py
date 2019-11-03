#Set Temperatures in celsius and Times in 24h hours and minutes
#temperature to be maintained when nobody is home/in the room/over night
away_temp = 20
#default heating temperature
default_temp = 25
#temperature to which heat up to when people are cold and the program is overriden
heat_up_temp = 29
#Temperature check frequency in seconds
temp_check_time = 58.0 
#Set times for schedules
#wake up hour
morning_hour = 6
#wake up minute
morning_minute = 30
#hour leaving the house to work
home_away_hour = 7
#minute leaving the house to work
home_away_minute = 15
#hour when back from work
back_home_hour = 16
#minute when back from work
back_home_minute = 20
#hour of bed time
night_hour = 22
#minute of bed time
night_minute = 30

import esp
esp.osdebug(None)
import gc
gc.collect()

import machine
from machine import Pin

#define LEDs on their PINs
green_led = machine.Pin(5, machine.Pin.OUT)
red_led = machine.Pin(0, machine.Pin.OUT)
yellow_led = machine.Pin(2, machine.Pin.OUT)

#define all leds off
def leds_off():
    red_led.low()
    green_led.low()
    yellow_led.low()

def leds_on():
    red_led.high()
    green_led.high()
    yellow_led.high()

#make sure LEDs are off on start
leds_off()

#define on and off on LEDs
def red_on():
    green_led.low()
    red_led.high()
    yellow_led.low()
def green_on():
    green_led.high()
    red_led.low()
    yellow_led.low()
def yellow_on():
    green_led.low()
    red_led.low()
    yellow_led.high()

#define pin controlling the Relay
relay = Pin(13, machine.Pin.OUT)

#define input pins for callbacks/change of mode
#switch to away mode
p16 = Pin(16, Pin.IN)
#swith for default timer mode
p14 = Pin(14, Pin.IN)
#swith led for heat-up mode
p15 = Pin(15, Pin.IN)

#connect to wifi
import time
import network
def wifi_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Connecting to wifi')
        sta_if.active(True)
        sta_if.connect('WIFI NETWORK', 'WIFI PASSWORD')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())    
wifi_connect()

#start webrepl
import webrepl
webrepl.start()

#Import temperature library and assign pin to read data from the sensor
import dht
temp = dht.DHT11(machine.Pin(4))

#get current time
from ntptime import settime

def adjust_time():
    try:
        settime()
    except Exception:
        pass

adjust_time()

#set up check time function
def check_time():
    global current_time
    current_time = time.localtime()

    #what year is it
    global year
    year = current_time[0]

    #what month is it
    global month
    month = current_time[1]

    #dd is day in a month, variable called "day" is a day in a week of 6
    global dd
    dd = current_time[2]
    
    #setting the current minute which is the same regardless of the time zone
    global minute
    minute = current_time[4]

    #weekday of 6 where 0 is Monday and 6 is Sunday
    global day
    day = current_time[6] + 1

    #since we are 5 hour behind, the next day happens 5 hour later here so we have to change the day and a weekday
    global hour
    if current_time[3] < 5:
        hour = current_time[3] + 19
        dd = current_time[2] - 1
        if day == 1:
            day = 7
        else:
            day = current_time[6] + 1
    else:
        hour = current_time[3] - 5

#call check time function at startup
check_time()

#establishing initial variables so that they exist and are not empty
#all_info has full date with all other logging info
all_info_data = "all_info_data initial"
#time of day is also a timeline in the loop/schedule that is being followed
time_of_day = "time_of_day initial"
#whether we are heating or not a.k.a. relay on or off
heating_status = "heating_status initial"
#initial temperature value
t = 0
#initial humidity value
h = 0
#e a.k.a. error message initial value
e = "error initial value"

#define all information shown and logged in a neat way
def all_info():
    global all_info_data
    all_info_data = ("Date: %04d-%02d-%02d - Day: %d/7 @ %d:%02d Temperature: %02d, Humidity: %02d, Heating: %s, Timeline: %s" % (year, month, dd, day, hour, minute, t, h, heating_status, time_of_day))
    print (all_info_data)

all_info()
    
import socket
def http_get(url):
    _, _, host, path = url.split('/', 3)
    addr = socket.getaddrinfo(host, 80)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))
    while True:
        data = s.recv(100)
        if data:
            print(str(data, 'utf8'), end='')
        else:
            break
    s.close()
    
#write all errors to log.txt file
def write_to_log(message,error):
    leds_off()
    print (message)
    print ("Accesing log")
    log = open('log.txt', 'a')
    log.write("%s" % all_info_data)
    log.write(", %s" % error)
    log.write(", M: %s" % message)
    log.write('\n')
    log.close()
    print ("Writing to log successful")
    leds_on()
    url = "http://hangared.com/smart/mail/index.php?warning="
    url += "Thermostat_1_warning:"
    url += message
    http_get(url)
    
    #here we end all running processes
    if error == "":
        pass
    else:
        import sys
        sys.exit()

#let's measure the temperature and humidity    
def measure_temperature():
    try:
        time.sleep(2.0)
        check_time()
        temp.measure()
        global t
        t = temp.temperature()
        global h
        h = temp.humidity()
    except Exception as error:
        message = ("Temp_Sensor_Problem")
        write_to_log(message,error)

#Define all 3 Modes
def heat_default():
    global heating_status
    try:
        measure_temperature()
        if (t < default_temp):
            heating_status = "ON"
            relay.high()
            red_on()        
        else:
            relay.low()
            heating_status = "OFF"
            green_on()
        #print all current info
        all_info()
        #wait until we read temperature again (currently set to 60 seconds)
        time.sleep(temp_check_time)
    except Exception as error:
        message = ("heat_default_error")
        print (message)
        leds_off()
        write_to_log(message,error)
def heat_away():
    global heating_status
    try:
        measure_temperature()
        if (t < away_temp):
            heating_status = "ON"
            relay.high()
            red_on()
        else:
            relay.low()
            heating_status = "OFF"
            green_on()
        all_info()
        time.sleep(temp_check_time)
    except Exception as error:
        message = ("heat_away_error")
        print (message)
        leds_off()
        write_to_log(message,error)
def away():
    global heating_status
    try:
        measure_temperature()
        if (t < away_temp):
            heating_status = "ON"
            relay.high()
            red_led.high()
            green_led.low()
            yellow_led.high()
            print ("AWAY MODE")
        else:
            heating_status = "OFF"
            relay.low()
            red_led.low()
            green_led.high()
            yellow_led.high()
            print ("AWAY MODE")
        all_info()
        time.sleep(temp_check_time)
    except Exception as error:
        message = ("away_error_(away mode)")
        print (message)
        leds_off()
        write_to_log(message,error)
#The most important mode - timer based on our values
def default_timer():
    try:
        global time_of_day
        while True:
            adjust_time()
            yellow_on()
            #from 22:30 to 11:59
            while (hour == night_hour and minute >= night_minute ) or (hour == night_hour + 1):
                time_of_day = ("night before midnight")
                heat_away()
            #from 0:00 to 6:30
            while (hour >= 0 and hour <= morning_hour and minute < morning_minute) or (hour == morning_hour and minute < morning_minute) or (hour >= 0 and hour <= morning_hour - 1):
                time_of_day = ("night after midnight")
                heat_away()
            #from 6:30 till 7:15
            while (hour == morning_hour and minute >= morning_minute  and day <= 5) or (hour == home_away_hour and minute < home_away_minute and day <= 5):
                time_of_day = ("from 6:30 till we leave")
                heat_default()
            #from 7:15 till 16:20
            while (hour >= home_away_hour + 1 and hour < back_home_hour and day <= 5) or (hour == home_away_hour and minute >= home_away_minute and day <= 5)or (hour == back_home_hour and minute < back_home_minute and day <= 5):
                time_of_day = ("during the business day")
                heat_away()
            #Weekend from 7:30 to 22:30
            while (hour >= morning_hour + 1 and hour < night_hour and day >= 6) or (hour == morning_hour and minute >= morning_minute and day >= 6) or (hour == night_hour and minute < night_minute and day >= 6):
                time_of_day = ("weekend during the day")
                heat_default()
            #back from work after 16:20 and before 22:29
            while (hour >= back_home_hour + 1 and hour < night_hour and day <= 5) or (hour == back_home_hour and minute >= back_home_minute and day <= 5) or (hour == night_hour and minute < night_minute and day <= 5):
                time_of_day = ("back from work, before bedtime")
                heat_default()
            #yellow_on()
    except Exception as error:
        message = ("default_timer_error")
        print (message)
        leds_off()
        write_to_log(message,error)
#HEAT UP override mode - for when it's cold on timer
def heat_up():
    global heating_status
    try:
        while True:
            measure_temperature()
            if (t < heat_up_temp):
                heating_status = "ON"
                relay.high()
                red_on()
                print ("HEAT UP MODE - no schedule")
            else:
                heating_status = "OFF"
                relay.low()
                green_on()
                print ("HEAT UP MODE - no schedule")
            all_info()
            time.sleep(temp_check_time)
    except Exception as error:
        message = ("heat_up_error")
        print (message)
        leds_off()
        write_to_log(message,error)
#Define callbacks
#p16.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=away)
#p14.irq(trigger=Pin.IRQ_FALLING, handler=default_timer)
p15.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=away)
#Run the main program

measure_temperature()
all_info()
write_to_log("start_up_or_restart", "")
default_timer()
