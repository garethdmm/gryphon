import logging
def log_request_perf(handler):
    
    if handler.get_status() < 400:
        log_method = logging.info
    elif handler.get_status() < 500:
        log_method = logging.warning
    else:
        log_method = logging.error
    request_time = 1000.0 * handler.request.request_time()
    request_speed_message=''
    if request_time <= 100:
        request_speed_message = 'FAST'
    elif request_time <= 200:
        request_speed_message = 'SPEED OK'
    elif request_time <= 400:
        request_speed_message= 'PRETTY SLOW'
    elif request_time <= 600:
        request_speed_message= 'SLOW'
    elif request_time <= 800:
        request_speed_message= 'VERY SLOW'
    elif request_time > 800:
        request_speed_message= 'CRITICALLY SLOW'
           
    log_method("%d %s %.2fms - %s", handler.get_status(),
               handler._request_summary(), request_time, request_speed_message)
