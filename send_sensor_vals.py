from machine import Pin, I2C, reset
import time
import ntptime
import BME280
from bh1750 import BH1750
import ssd1306
import json
import sys
import network
import rp2
import requests
import gc
from NR_metric import NRMetricElement, Attributes, Metric
from environment import HOSTNAME, APPNAME, metrics_url, logs_url, WIFI_REGION_CODE
from credentials import SSID, PASSCODE, NR_API_KEY

#you may notice garbage collection called manually as the RP2350 this was tested on has limited memory
#calling manually when large data structures such as HTTP requests / responses go out of scope reduces fragmentation
gc.enable()

#depending on hardware and micropython libraries time may be UTC or local
#the NR API requires UTC or it will give a 202 and then throw the data away
UTC_OFFSET_HOURS = 0

#attirbutes for metrics.  Declared globally to reduce memory overhead
attributes = Attributes(APPNAME, HOSTNAME)

runs = 0

print("Starting NewRelic IoT Sensor Demo...")

#check config
print("Checking config...")
configError = False

if len(SSID) > 0 :
    print("SSID: " + SSID)
else:
    configError = True
    print("SSID not set!!!")
    
if len(PASSCODE) < 1 :
    configError = True
    print("Wifi passcode not set!!!")
    
if len(NR_API_KEY) < 1 :
    configError = True
    print("NR_API_KEY not set!!!")

if len(HOSTNAME) > 0 :
    print("hostname: " + HOSTNAME)
else :
    configError = true
    print("HOSTNAME not set!!!")

if len(APPNAME) > 0 :
    print("appname: " + APPNAME)
else :
    configError = True
    print("APPNAME not set!!!")
    
if len(metrics_url) > 10 :
    print("metrics_url: " + metrics_url)
else :
    configError = True
    print("metrics_url not set!!!")

if len(logs_url) > 10 :
    print("logs_url: " + logs_url)
else :
    configError = True
    print("logs_url not set!!!")


# Initialize I2C communication using hard i2c
i2c = I2C(id=0, scl=Pin(1), sda=Pin(0), freq=400000)

if configError :
    print("Halting due to config error!")
    
    while True :
        display = ssd1306.SSD1306_I2C(128, 32, i2c)
        display.text("CONFIG ERROR",0,0)
        display.text(SSID, 0, 15)
        display.show()
        time.sleep(3600)


#if having problems with a different brand sensor, feel free to uncomment below to check the i2c addresses

# print('I2C SCANNING...')
# devices = i2c.scan()
# 
# if len(devices) == 0:
#   print("No i2c devices found")
# else:
#   print('# of i2c devices:', len(devices))
# 
#   for device in devices:
#     print("I2C addr: ", hex(device))


time.sleep(1)
#connect WIFI
rp2.country(WIFI_REGION_CODE)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSCODE)

while not wlan.isconnected() or wlan.status() < 0 :
    print("Connecting to WIFI:")
    display = ssd1306.SSD1306_I2C(128, 32, i2c)
    display.text("Connecting to WIFI",0,0)
    display.text(SSID, 0, 15)
    display.show()    
    time.sleep(2)

print(wlan.ifconfig())

#The Newrelic API is timestamp sensitive so timing debug info can be helpful
# print(time.time())
# print(time.time() + (UTC_OFFSET_HOURS * 3600))

#set microcontroller time from NTP
ntptime.settime()

# print(time.time())
# print(time.time() + (UTC_OFFSET_HOURS * 3600))

display = ssd1306.SSD1306_I2C(128, 32, i2c)
display.text("WIFI CONNECTED",0,0)
init_timestamp = time.time()
init_timestamp += (UTC_OFFSET_HOURS * 3600)

display.text(str(init_timestamp), 0, 15)
display.show()
time.sleep(9)


#read sensors, display on oled, and send to NR
def run():
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
    
    #toss out first sensor reads, as they can be erroneous
    if runs == 0 :
        return
    
    #send all env data to NR
    http_status_code = send_metric_to_nr(hum, lux, pres, tempF, unix_timestamp)
    
    #put subset of env data and NR status code on OLED
    display = ssd1306.SSD1306_I2C(128, 32, i2c)
    display.text("T: {:.1f}".format(tempF), 0, 0)
    display.text("H: {:.0f}%".format(hum), 71, 0)
    display.text("L: {:.0f}".format(lux), 0, 15)
    display.text("NR: " + str(http_status_code), 71, 15)
    display.show()



#method to actually send a list of metrics to New Relic
#An intermediary data stucture is used since metric data format is non trivial
#see: https://docs.newrelic.com/docs/data-apis/ingest-apis/metric-api/report-metrics-metric-api/
def send_metric_to_nr(hum, lux, pres, tempF, unix_timestamp):
    temp_metric = Metric("temperature", "gauge", tempF, unix_timestamp, attributes)
    humid_metric = Metric("relative_humidity", "gauge", hum, unix_timestamp, attributes)
    pressure_metric = Metric("pressure", "gauge", pres, unix_timestamp, attributes)
    lum_metric = Metric("luminance", "gauge", lux, unix_timestamp, attributes)
    elements = NRMetricElement([temp_metric, humid_metric, pressure_metric, lum_metric])
    # send the NR Metric
    send_bytes_string = json.dumps([elements.to_dict()])
#    print(send_bytes_string)
    send_bytes = send_bytes_string.encode()
    header_data = {"Content-Type": "application/json", "Api-Key": NR_API_KEY}
    r = requests.post(metrics_url, data=send_bytes, headers=header_data, timeout=20)
    http_status_code = r.status_code
    print(r.status_code)
    r.close()
    gc.collect()
    return http_status_code

#send log line to NR directly
def send_log_to_nr(message, unix_timestamp):
    
    log_data = {}
    log_data['timestamp'] = unix_timestamp
    log_data['message'] = message
    log_data['logtype'] = "iotlog"
    log_data['hostname'] = HOSTNAME
    
    
    # send the NR Log
    send_bytes_string = json.dumps(log_data)
    print(send_bytes_string)
    send_bytes = send_bytes_string.encode()
    header_data = {"Content-Type": "application/json", "Api-Key": NR_API_KEY}
    r = requests.post(logs_url, data=send_bytes, headers=header_data, timeout=20)
    http_status_code = r.status_code
    print(r.status_code)
    r.close()
    gc.collect()
    return http_status_code


log_timestamp = time.time()
log_timestamp += (UTC_OFFSET_HOURS * 3600)
send_log_to_nr("RP2350 startup", log_timestamp)


while True:
    try:
        gc.collect()
        print("\nRun: {:d}".format(runs))
        run()
        runs += 1



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