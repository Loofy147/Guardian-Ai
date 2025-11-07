import time
from guardian_ai.celery_utils import celery_app

@celery_app.task(bind=True)
def long_running_task(self, x, y):
    """
    A sample long-running task that adds two numbers.
    """
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100})
    time.sleep(10) # Simulate a long process
    self.update_state(state='PROGRESS', meta={'current': 50, 'total': 100})
    time.sleep(10) # Simulate more work
    self.update_state(state='SUCCESS', meta={'current': 100, 'total': 100})
    return x + y
