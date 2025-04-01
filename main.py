import gc
import time

import BME280
import network
import ntptime
import os
import rp2
import ssd1306
from bh1750 import BH1750
from machine import Pin, I2C, reset

import send_sensor_vals
from credentials import SSID, PASSCODE, NR_API_KEY
from environment import HOSTNAME, APPNAME, metrics_url, logs_url, WIFI_REGION_CODE
from send_sensor_vals import send_log_to_nr, send_env_metric_to_nr, report_system_metrics, UTC_OFFSET_HOURS

print("MAIN")

RED_PIN_NUMBER = 21
YELLOW_PIN_NUMBER = 20
GREEN_PIN_NUMBER = 19

green_led = Pin(GREEN_PIN_NUMBER, Pin.OUT)
red_led = Pin(RED_PIN_NUMBER, Pin.OUT)
yellow_led = Pin(YELLOW_PIN_NUMBER, Pin.OUT)

sw3 =  Pin(15, Pin.IN, Pin.PULL_UP)

global wlan

memory_leak_list = []
memory_leak_mode = False

def check_config():

    config_error = False
    if len(SSID) > 0:
        print("SSID: " + SSID)
    else:
        config_error = True
        print("SSID not set!!!")
    if len(PASSCODE) < 1:
        config_error = True
        print("Wifi passcode not set!!!")
    if len(NR_API_KEY) < 1:
        config_error = True
        print("NR_API_KEY not set!!!")
    if len(HOSTNAME) > 0:
        print("hostname: " + HOSTNAME)
    else:
        config_error = True
        print("HOSTNAME not set!!!")
    if len(APPNAME) > 0:
        print("appname: " + APPNAME)
    else:
        config_error = True
        print("APPNAME not set!!!")
    if len(metrics_url) > 10:
        print("metrics_url: " + metrics_url)
    else:
        config_error = True
        print("metrics_url not set!!!")
    if len(logs_url) > 10:
        print("logs_url: " + logs_url)
    else:
        config_error = True
        print("logs_url not set!!!")
    return config_error


#if sw3 is pressed during startup, demo goes into memory leak mode
def read_and_set_mode():
    # this is a hack, but helpful since part of the demo requires a memory leak
    global memory_leak_list
    global memory_leak_mode
    memory_leak_list = []
    memory_leak_mode = False    # holding down on sw3 during startup will send demo into memory leak mode
    send_sensor_vals.memory_leak_mode = memory_leak_mode
    send_sensor_vals.memory_leak_list = memory_leak_list
    print("sw3 value", sw3.value())
    if sw3.value() == 0:
        memory_leak_mode = True
        yellow_led.on()
        red_led.on()


def config_error_halt(i2c):
    print("Halting due to config error!")
    while True:
        display = ssd1306.SSD1306_I2C(128, 32, i2c)
        display.text("CONFIG ERROR", 0, 0)
        display.text(SSID, 0, 15)
        display.show()
        time.sleep(3600)

def connect_wifi(i2c):
    global wlan
    rp2.country(WIFI_REGION_CODE)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSCODE)
    wlan_connection_attempts = 0
    while not wlan.isconnected() or wlan.status() < 0:
        wlan_connection_attempts += 1
        print("Connecting to WIFI:")
        display = ssd1306.SSD1306_I2C(128, 32, i2c)
        display.text("Connecting to WIFI", 0, 0)
        display.text(SSID, 0, 15)
        display.show()
        time.sleep(2)
        
        if (wlan_connection_attempts % 10) == 0 :
            wlan.active(False)
            time.sleep(15)
            rp2.country(WIFI_REGION_CODE)
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            wlan.connect(SSID, PASSCODE)
        
        if wlan_connection_attempts > 120:
            reset()
    print(wlan.ifconfig())


# read sensors, display on oled, and send to NR
def run():
    
        
    #    if (runs % 5) == 0:
    report_system_metrics()

    global display
    bme = BME280.BME280(i2c=i2c)
    light_sensor = BH1750(bus=i2c, addr=0x23)

    # correct for UTC if necessary depending on hardware
    unix_timestamp = time.time()
    unix_timestamp += (UTC_OFFSET_HOURS * 3600)

    hum = float(bme.humidity)
    pres = float(bme.pressure)
    lux = round(float(light_sensor.luminance(BH1750.CONT_HIRES_1)), 2)

    # Convert temperature to fahrenheit
    tempF = (bme.read_temperature() / 100) * (9 / 5) + 32
    tempF = round(tempF, 2)

    # Print sensor readings
    print("Temperature: ", tempF)
    print("Humidity: ", hum)
    print("Pressure: ", pres)
    print("Luminance: {:.2f} lux".format(lux))

    # toss out first sensor reads, as they can be erroneous
    if runs == 0:
        return

    # send all env data to NR
    http_status_code = send_env_metric_to_nr(hum, lux, pres, tempF, unix_timestamp)

    # put subset of env data and NR status code on OLED
    display = ssd1306.SSD1306_I2C(128, 32, i2c)
    display.text("T: {:.1f}".format(tempF), 0, 0)
    display.text("H: {:.0f}%".format(hum), 71, 0)
    display.text("L: {:.0f}".format(lux), 0, 15)
    display.text("NR: " + str(http_status_code), 71, 15)
    display.show()

#add to memory leak
def drip():
    print("drip...")
    memory_leak_list.append(os.urandom(1664))

if __name__ == "__main__":

    print("Starting NewRelic IoT Sensor Demo...")
    print("Memory leak mode: ", memory_leak_mode)
    gc.enable()
    read_and_set_mode()

    print("Checking config...")
    configError = check_config()

    # Initialize I2C communication using hard i2c
    i2c = I2C(id=0, scl=Pin(1), sda=Pin(0), freq=400000)

    if configError:
        config_error_halt(i2c)

    connect_wifi(i2c)

    # The Newrelic API is timestamp sensitive so timing debug info can be helpful
    # print(time.time())
    # print(time.time() + (UTC_OFFSET_HOURS * 3600))

    # set microcontroller time from NTP
    ntptime.settime()

    send_sensor_vals.report_system_metrics()

    display = ssd1306.SSD1306_I2C(128, 32, i2c)
    display.text("WIFI CONNECTED", 0, 0)
    init_timestamp = time.time()
    init_timestamp += (UTC_OFFSET_HOURS * 3600)
    display.text(str(init_timestamp), 0, 15)
    display.show()
    time.sleep(5)

    log_timestamp = time.time()
    log_timestamp += (UTC_OFFSET_HOURS * 3600)
    send_log_to_nr("RP2350 startup", log_timestamp)
    if memory_leak_mode:
        send_log_to_nr("Running memory leak demo...", log_timestamp)
        print("Starting memory leak demo")

    log_timestamp = time.time()
    log_timestamp += (UTC_OFFSET_HOURS * 3600)
    send_log_to_nr(wlan.ifconfig(), log_timestamp)

    runs = 0


while True:
    try:
        if((runs > 300) & memory_leak_mode) :
            reset()

        gc.collect()
        print("\nRun: {:d}".format(runs))
        
        if not wlan.isconnected() or wlan.status() < 0:
            connect_wifi(i2c)
        
        run()
        runs += 1

        print("Memory Leak Mode: ", memory_leak_mode)
        if memory_leak_mode :
            drip()



    except Exception as e:
        # Handle any exceptions during sensor reading
        print('An error occurred:', e)
        try:
            display = ssd1306.SSD1306_I2C(128, 32, i2c)
            display.text("Error: " + str(e), 0, 0)
            display.show()
            log_timestamp = time.time()
            log_timestamp += (UTC_OFFSET_HOURS * 3600)
            send_log_to_nr("Error: " + str(e), log_timestamp)

        except Exception as e1:
            print('An exception handling error occurred:', e1)

    time.sleep(10)
