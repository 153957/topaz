"""Determine detector offset drift over time

This determines the detector offsets for several stations on various dates.

The offsets seems fairly constant over time, within a nanosecond. A day
of data seems enough to accurately determine the offsets, If a detector
is not working properly it may result in a completely wrong offset,
though there might not be any good data for which the offset would be
needed. However, if the bad detector is detector 2, it might be
difficult to determine the offsets for the other detectors.

Causes for changing offsets at some points:
- When swapping HiSPARC electronics (e.g. 501, 502, 504)
- When swapping PMTs or a PMT is not working well (e.g. 503, 505, 508)

"""
import os

import tables
from artist import Plot
from numpy import histogram, arange, nan
from scipy.optimize import curve_fit

from sapphire.analysis.reconstructions import ReconstructESDCoincidences as Rec
from sapphire.utils import gauss
from sapphire.clusters import Station

DATA_PATH = '/Users/arne/Datastore/esd/'
STATIONS = [501, 502, 503, 504, 505, 506, 508, 509, 1006]

O = (0, 0, 0)
STATION = Station(None, 0, O,
                  detectors=[(O, 'UD'), (O, 'UD'), (O, 'LR'), (O, 'LR')])
LIMITS = 20


def determine_offset(data, station):
    station_group = data.get_node('/station_%d' % station)
    offsets = Rec.determine_detector_timing_offsets(STATION, station_group)
    offsets = [o if o != 0. else nan for o in offsets]
    return offsets


if __name__ == '__main__':

    for station in STATIONS:
        # Determine offsets for first day of each month
        offsets = []
        for y in range(2010, 2015):
            for m in range(1, 13):
                path = os.path.join(DATA_PATH, str(y), str(m), '%d_%d_1.h5' % (y, m))
                with tables.open_file(path, 'r') as data:
                    offsets.append(determine_offset(data, station))
        d1, _, d3, d4 = zip(*offsets)
        x = range(len(d1))
        graph = Plot()
        graph.plot(x, d1, markstyle='mark size=.5pt')
        graph.plot(x, d3, markstyle='mark size=.5pt', linestyle='green')
        graph.plot(x, d4, markstyle='mark size=.5pt', linestyle='blue')
        graph.set_ylabel('$\Delta t$ [ns]')
        graph.set_xlabel('Date')
        graph.set_xlimits(0, max(x))
        graph.set_ylimits(-LIMITS, LIMITS)
        graph.save_as_pdf('detector_offset_drift_months_%d' % station)

        # Determine offsets for each day in one month
        offsets = []
        y = 2013
        m = 1
        for d in range(1, 32):
            path = os.path.join(DATA_PATH, str(y), str(m), '%d_%d_%d.h5' % (y, m, d))
            with tables.open_file(path, 'r') as data:
                offsets.append(determine_offset(data, station))
        d1, _, d3, d4 = zip(*offsets)
        x = range(len(d1))
        graph = Plot()
        graph.plot(x, d1, markstyle='mark size=.5pt')
        graph.plot(x, d3, markstyle='mark size=.5pt', linestyle='green')
        graph.plot(x, d4, markstyle='mark size=.5pt', linestyle='blue')
        graph.set_ylabel('$\Delta t$ [ns]')
        graph.set_xlabel('Day')
        graph.set_xlimits(0, max(x))
        graph.set_ylimits(-LIMITS, LIMITS)
        graph.save_as_pdf('detector_offset_drift_daily_%d' % station)
