from timeit import default_timer as timer
from concurrent.futures import ThreadPoolExecutor
from functools import partial
class LogWriter():

    file = None
    tpe = ThreadPoolExecutor(1)

    def __init__(self, fn):
        global start_time
        if 'start_time' not in globals():
            start_time = timer()
        self.file = open(fn,'w')

    def write(self, t, *args):
        global start_time
        self.tpe.submit(partial(self.file.write,f'{t-start_time},{",".join([str(x) for x in args])}\n'))

    def __del__(self):
        self.tpe.shutdown(wait=True)
        self.file.close()