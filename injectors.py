from random import randrange, random, uniform, randint
import numpy as np

class BaseInjector(object):

    def next_sensor(self, maxval, minval, valcount):
        self.max_value = maxval
        self.min_value = minval
        self.number_of_values = valcount

        self.next()


    def next(self):
        pass
            
class SpikeInjector(BaseInjector):
    spike_frequency = 0.01
    spike_value = []
    spike_values = {}

    
    def __init__(self, spike_frequency=0.05):
        self.spike_frequency = spike_frequency
        self.label = "spike"

    def next(self):
        self.spike_value_up = self.max_value * uniform(0.6, 1.0)
        self.spike_value_down = self.min_value - abs(self.min_value * uniform(0.6, 1.0))
    
    def inject(self, data):
        if random() < self.spike_frequency:
            if uniform(0.0 , 1.0) > 0.5:
                spike_val = self.spike_value_up
            else:
                spike_val = self.spike_value_down
            return spike_val 
        return data


class DriftInjector(BaseInjector):
    row_count = 0
    
    def __init__(self, drift):
        self.drift_constant = drift
        if drift > 0:
            self.label = "drift_up"
        else:
            self.label = "drift_down"

    def inject(self, data):
        self.row_count += 1
        return data + (self.drift_constant * self.row_count)
    
    def next(self):
        self.row_count = 0
    

class ClogInjector(BaseInjector):
    prev_value = None
    prev_data = None
    drain = None
    
    def __init__(self):
        self.label = "clog"        

    def choose_drain(self):
        self.drain = uniform(0.15, 1.0)

    def inject(self, data):
        if self.prev_value == None:
            self.prev_data = data
            self.prev_value = data
            return data
        self.prev_value = self.prev_value + (max(0, data - self.prev_data) * self.drain)
        self.prev_data = data
        if self.prev_value > self.max_value:
            return self.max_value
        return self.prev_value
    
    def next(self):
        self.prev_value = None
        self.prev_data = None
        self.choose_drain()
        self.label = "clog_{0}".format(self.drain)



class FlatlineInjector(BaseInjector):

    flatline_value = None
    
    def __init__(self):
        self.label = "flatline"

    def next(self):
        self.flatline_value = None
    
    def inject(self, data):
        if self.flatline_value == None:
            self.flatline_value = data
        return self.flatline_value      


class NoiseInjector(BaseInjector):
    
    def __init__(self, sigma = 0.1):
        self.label = "noise"
        self.sigma = sigma
    
    def next(self):
        mu = 0
        self.norm_dist = np.random.normal(mu, self.sigma, self.number_of_values)
        self.noisecounter = 0

    def inject(self, data):
        self.noisecounter += 1
        return data + self.norm_dist[self.noisecounter]

class ConstantInjector(BaseInjector):

    constant = 0

    def __init__(self):
        self.label = "constant"
    
    def next(self):
        variance = self.max_value - self.min_value
        self.constant = uniform(variance / 20, variance)
    
    def inject(self, data):
        return data + self.constant

class TransmissionFaultInjector(BaseInjector):

    def __init__(self):
        self.label = "transmissionfault"
    
    def inject(self, data):
        return 0.0
