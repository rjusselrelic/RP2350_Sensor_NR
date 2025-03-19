import gc
import json
import os
import time
import requests
from NR_metric import NRMetricElement, Attributes, Metric

from credentials import NR_API_KEY
from environment import HOSTNAME, APPNAME, metrics_url, logs_url

#depending on hardware and micropython libraries time may be UTC or local
#the NR API requires UTC or it will give a 202 and then throw the data away
UTC_OFFSET_HOURS = 0

#attirbutes for metrics.  Declared globally to reduce memory overhead
attributes = Attributes(APPNAME, HOSTNAME)


def report_system_metrics():
    
    try:
        alloc_mem = float(gc.mem_alloc())
        free_mem = float(gc.mem_free())
        
        vfs_statistics = os.statvfs("/")
        vfs_size = vfs_statistics[1] * vfs_statistics[2]
        vfs_free = vfs_statistics[0] * vfs_statistics[3]
        vfs_allocated = vfs_size - vfs_free
        
        print("Allocated memory: ", alloc_mem)
        print("Free memory: ", free_mem)
        print("VFS_Size: ", vfs_size)
        print("Allocated vfs: ", vfs_allocated)
        print("Free vfs: ", vfs_free)
        
        unix_timestamp = time.time()
        unix_timestamp += (UTC_OFFSET_HOURS * 3600)
        
        alloc_mem_metric = Metric("ram_allocated", "gauge", alloc_mem, unix_timestamp, attributes)
        free_mem_metric = Metric("ram_free", "gauge", free_mem, unix_timestamp, attributes)
        
        size_vfs_metric = Metric("vfs_size_bytes", "gauge", float(vfs_size), unix_timestamp, attributes)
        alloc_vfs_metric = Metric("vfs_allocated_bytes", "gauge", float(vfs_allocated), unix_timestamp, attributes)
        free_vfs_metric = Metric("vfs_free_bytes", "gauge", float(vfs_free), unix_timestamp, attributes)
        
        sys_metric_elements = NRMetricElement([alloc_mem_metric, free_mem_metric, size_vfs_metric, alloc_vfs_metric, free_vfs_metric])

        #New Relic metrics to be in an root array
        send_bytes_string = json.dumps([ sys_metric_elements.to_dict() ])
#        print(send_bytes_string)
        send_bytes = send_bytes_string.encode()
        header_data = {"Content-Type": "application/json", "Api-Key": NR_API_KEY}
        r = requests.post(metrics_url, data=send_bytes, headers=header_data, timeout=20)
        http_status_code = r.status_code
        print(r.status_code)
        r.close()
        gc.collect()
        return http_status_code
    
    except Exception as e:
        print("Error reporting system metrics", e)
        return -1




#method to actually send a list of metrics to New Relic
#An intermediary data stucture is used since metric data format is non trivial
#see: https://docs.newrelic.com/docs/data-apis/ingest-apis/metric-api/report-metrics-metric-api/
def send_env_metric_to_nr(hum, lux, pres, tempF, unix_timestamp):
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

