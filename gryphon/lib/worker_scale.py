
import heroku

class HerokuWorkerScale(object):
    def __init__(self, api_key, app_name):
        self.key = api_key
        self.name = app_name
    
    def _scale(self, num_change):
        if self.key:
            cloud = heroku.from_key(self.key)
            app = cloud.apps[self.name]
            workers = app.processes['worker']
            len_workers = len([worker for worker in workers])
            workers.scale(len_workers+num_change)
    def add_worker(self):
        self._scale(1)
    
    def remove_worker(self):
        self._scale(-1)
        
