# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.open_exchange_rate_poller import OpenExchangeRatePoller
from gryphon.data_service.task import Task


class UtilitiesPollTask(Task):
    def __init__(self):
        self.pollers = [
            OpenExchangeRatePoller()
        ]

    def start_task(self):
        for poller in self.pollers:
            poller.start()
