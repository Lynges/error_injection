import csv
import copy
import os
import urllib.request
import pathlib
import itertools 
import matplotlib.pyplot as plt

from collections import deque
from random import randint, shuffle, choices, seed

from settings import SENSOR_HEIGHTS

from injectors import SpikeInjector, ClogInjector, DriftInjector, FlatlineInjector, ConstantInjector, TransmissionFaultInjector, NoiseInjector

seed(99409940)

ROW_LIMIT = None
PLOTTED_SENSORS = []

PLOT_COLORS = ['#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00','#ffff33','#a65628','#f781bf','#999999']

inputdata = {}
outputdata = {}

input_csv = '/home/lynge/noget/data/testing_no_errors.csv'

with open(input_csv, newline='') as inputfile:
    print("Started reading {0}".format(input_csv))
    reader  = csv.DictReader(inputfile)
    rowcounter = 0
    for row in reader:
        if ROW_LIMIT and rowcounter > ROW_LIMIT:
            break
        rowcounter += 1
        for key in row.keys():
            if key == '':
                continue
            else:
                if key not in inputdata.keys() and key != "TIME":
                    inputdata[key] = []
                if key not in outputdata.keys():
                    outputdata[key] = deque()
                if key == 'TIME':
                    outputdata[key].append(row[key])
                else:
                    inputdata[key].append(float(row[key]))
    print("Done reading file into dict. Closing file")


NEXT_COLOR = itertools.cycle(PLOT_COLORS)

def random_chunks(amount, chunk_count, minimum=0):
    chunks = []
    orig_amount = amount
    while len(chunks) < chunk_count:
        chunk = randint(0, amount)
        if (amount - chunk) < ((chunk_count - (len(chunks) + 1)) * minimum):
            continue
        chunks.append(chunk)
        amount = amount - chunk
        if amount < 0:
            amount = 0
    if sum(chunks) < orig_amount:
        addition = (orig_amount - sum(chunks))//len(chunks)
        chunks = [x + addition for x in chunks]
    return chunks

def inject_errors(injectors, inputdata, outputdata, dirname, errorrate=randint(2, 3)):
    name_of_run = '_'.join([inj.label for inj in injectors])
    print("Starting injection for {0} into {1} with errorrate {2}".format(name_of_run, dirname, errorrate))
    spike_injector = SpikeInjector(spike_frequency=0.0002) # create the spike injector for this run
    for sensorname in inputdata:
        datapoints = len(inputdata[sensorname])
        lengths = random_chunks(datapoints//100*errorrate, len(injectors), datapoints//100*errorrate//4//len(injectors))
        paddings = random_chunks(datapoints - sum(lengths), len(injectors) + 1)

        shuffle(lengths)
        shuffle(paddings)
        shuffle(injectors)

        injector_ranges = []
        front_padding = 0

        if sensorname in SENSOR_HEIGHTS.keys():
            sensorheight = SENSOR_HEIGHTS[sensorname]
        else:
            print("Sensor {sid} not in SENSOR_HEIGHTS".format(sid=sensorname))
            sensorheight = 0

        maxval = max(inputdata[sensorname]) - sensorheight
        minval = min(inputdata[sensorname]) - sensorheight
        spike_injector.next_sensor(maxval, minval, datapoints)
        for inj in injectors:
            inj.next_sensor(maxval, minval, datapoints)
            front_padding += paddings.pop(0)
            injector_ranges.append((inj, front_padding, front_padding + lengths[0]))
            front_padding += lengths.pop(0)
        


        maincounter = 0
        irc = 0
        for val in inputdata[sensorname]:
            val = val - sensorheight
            outval = (val, "normal")
            if irc < len(injector_ranges) and maincounter > injector_ranges[irc][1]:
                if maincounter <= injector_ranges[irc][2]:
                    newval = injector_ranges[irc][0].inject(val)
                    if newval != val:
                        outval = (newval, injector_ranges[irc][0].label)
                else:
                    irc += 1
            spikeval = spike_injector.inject(outval[0])
            if spikeval != outval[0]:
                outval = (spikeval, spike_injector.label)
            outputdata[sensorname].append((outval[0] + sensorheight, outval[1]))
            maincounter += 1
    
    print("Creating plots for chosen sensors")
    create_plot(dirname, outputdata, name_of_run)

    outputfile_name = name_of_run + '.csv'

    print("Done with data. Writing to output file: {0}".format(outputfile_name))
    fieldnames = []
    for sensorname in outputdata.keys():
        if sensorname == 'TIME':
            fieldnames.append(sensorname)
            continue
        fieldnames.append(sensorname + '_value')
        fieldnames.append(sensorname + '_label')
        
    with open(os.path.join(dirname, outputfile_name), 'w', newline='') as outputfile:
        writer = csv.DictWriter(outputfile, fieldnames=fieldnames)
        writer.writeheader()
        
        rowdict = get_outputrow(outputdata)
        while rowdict:
            writer.writerow(rowdict)
            rowdict = get_outputrow(outputdata)
    print("Done writing to file")
        


def get_outputrow(data):
    result = {}
    for key in data:
        if not data[key]:
            return False
        rval = data[key].popleft()
        if key == 'TIME':
            result[key] = rval
        else:
            result[key + '_value'] = rval[0]
            result[key + '_label'] = rval[1]
    return result
            

def create_plot(plot_path, data, plot_name):  
    global PLOTTED_SENSORS
    global NEXT_COLOR
    if not PLOTTED_SENSORS:
        PLOTTED_SENSORS = choices(list(data.keys())[3:], k=5)
    for senskey in PLOTTED_SENSORS:
        plt.figure(figsize=(32,18))
        xvals = []
        yvals = []
        highlight_points = []
        xcounter = 0
        for dt in list(itertools.islice(data[senskey], 50, len(data[senskey]))):
            xvals.append(xcounter)
            yvals.append(dt[0])
            if dt[1] != 'normal':
                
                highlight_points.append(xcounter)
            xcounter += 1
        
        plt.plot(yvals)
        highlights = find_highligts(highlight_points)
        for highlight in highlights:
            plt.axvspan(highlight[0], highlight[1], color=next(NEXT_COLOR), alpha=0.5)
        plt.savefig(plot_path + '/' + plot_name + '_' + senskey + '_plot.svg')



def find_highligts(highlight_points):
    result = []
    
    current = [None, None]
    for hp in highlight_points:
        if current[0] == None:
            current[0] = hp
            current[1] = hp
            continue
        if current[1] + 1 == hp:
            current[1] = hp
        else:
            result.append(current)
            current = [None, None]
    if current[0] != None and current[1] != None:
        result.append(current)
    return result


print("Creating dirname")

dirname = '/home/lynge/noget/data/error_injected/{0}'.format(urllib.request.urlopen("https://project-names.herokuapp.com/names").read().decode('utf-8'))
pathlib.Path(dirname).mkdir(parents=True, exist_ok=True)

print("Creating injectors")
injectors = [
    NoiseInjector(),
    # SpikeInjector(spike_frequency=0.005),
    ClogInjector(),
    DriftInjector(0.00003),
    DriftInjector(-0.00003),
    FlatlineInjector(),
    ConstantInjector(),
    TransmissionFaultInjector()
]

print("Starting injection run")
# for inj in injectors:
#     inject_errors([inj], inputdata, copy.deepcopy(outputdata), dirname, errorrate=randint(2, 3))

inject_errors(injectors, inputdata, copy.deepcopy(outputdata), dirname, errorrate=randint(2, 3))
