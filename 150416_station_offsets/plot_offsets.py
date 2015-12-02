"""Determine detector offset drift over time

This determines the detector offsets for several stations on various dates.

The offsets seems fairly constant over time, within a nanosecond. A day
of data seems enough to accurately determine the offsets, If a detector
is not working properly it may result in a completely wrong offset,
though there might not be any good data for which the offset would be
needed. However, if the bad detector is detector 2, it might be
difficult to determine the offsets for the other detectors.

Causes for changing offsets at some points:
- Use a temporary GPS with bad view of the sky (501)
- When swapping HiSPARC electronics (e.g. 501, 502, 504)
- When swapping PMTs or a PMT is not working well (e.g. 503, 505, 508)

"""
from datetime import date
import csv
import calendar

from artist import Plot
from numpy import nan, genfromtxt

from sapphire.api import Station
from sapphire.transformations.clock import gps_to_datetime, datetime_to_gps

STATIONS = [502, 503, 504, 505, 506, 508, 509, 510]
DATA_PATH = '/Users/arne/Datastore/station_offsets/'


def get_detector_offsets(station):
    offsets = genfromtxt(DATA_PATH + 'offsets_%d.csv' % station, delimiter='\t',
                         names=('timestamp', 'd0', 'd1', 'd2', 'd3'))
    return offsets


def get_station_offsets(ref, station):
    offsets = genfromtxt(DATA_PATH + 'offsets_ref%d_s%d.csv' % (ref, station), delimiter='\t',
                         names=('timestamp', 'offset'))
    return offsets


def get_n_events(station):
    n = genfromtxt(DATA_PATH + 'n_month_%d.csv' % station, delimiter='\t',
                   names=('timestamp', 'n'))
    return n


def save_n_events_month(station):
    s = Station(station)
    output = open(DATA_PATH + 'n_month_%d.csv' % station, 'a')
    csvwriter = csv.writer(output, delimiter='\t')
    for y in range(2010, 2016):
        for m in range(1, 13):
            if y == 2015 and m >= 4:
                continue
            n = s.n_events(y, m) / float(calendar.monthrange(y, m)[1])
            t = datetime_to_gps(date(y, m, 1))
            csvwriter.writerow([t, n])
    output.close()


def save_n_events(station):
    s = Station(station)
    output = open(DATA_PATH + 'n_%d.csv' % station, 'a')
    csvwriter = csv.writer(output, delimiter='\t')
    for y in range(2010, 2016):
        for m in range(1, 13):
            if y == 2015 and m >= 4:
                continue
            for d in range(1, calendar.monthrange(y, m)[1] + 1):
                n = s.n_events(y, m, d)
                t = datetime_to_gps(date(y, m, d))
                csvwriter.writerow([t, n])
    output.close()


if __name__ == '__main__':

#     save_n_events(501)
#     save_n_events_month(501)
#     for station in STATIONS:
#         save_n_events(station)
#         save_n_events_month(station)

    ref_station = 501
    ref_s = Station(ref_station)
#     ref_gps = ref_s.gps_locations
#     ref_voltages = ref_s.voltages
#     ref_n = get_n_events(501)
    for station in STATIONS:
        s = Station(station)
#         voltages = s.voltages
#         gps = s.gps_locations
        # Determine offsets for first day of each month
#         d_off = get_detector_offsets(station)
        s_off = get_station_offsets(ref_station, station)
#         n = get_n_events(station)
        graph = Plot(width=r'.6\textwidth')
#         graph.scatter(ref_gps['timestamp'], [95] * len(ref_gps), mark='square', markstyle='purple,mark size=.5pt')
#         graph.scatter(ref_voltages['timestamp'], [90] * len(ref_voltages), mark='triangle', markstyle='purple,mark size=.5pt')
#         graph.scatter(gps['timestamp'], [85] * len(gps), mark='square', markstyle='gray,mark size=.5pt')
#         graph.scatter(voltages['timestamp'], [80] * len(voltages), mark='triangle', markstyle='gray,mark size=.5pt')
#         graph.shade_region(n['timestamp'], -ref_n['n'] / 1000, n['n'] / 1000, color='lightgray,const plot')
#         graph.plot(d_off['timestamp'], d_off['d0'], markstyle='mark size=.5pt')
#         graph.plot(d_off['timestamp'], d_off['d2'], markstyle='mark size=.5pt', linestyle='green')
#         graph.plot(d_off['timestamp'], d_off['d3'], markstyle='mark size=.5pt', linestyle='blue')
        graph.plot(s_off['timestamp'] / 1e9, s_off['offset'], mark='*',
                   markstyle='mark size=1.25pt', linestyle=None)
        graph.set_ylabel('$\Delta t$ [ns]')
        graph.set_xlabel('Date')
        graph.set_xticks([datetime_to_gps(date(y, 1, 1)) / 1e9 for y in range(2010, 2016)])
        graph.set_xtick_labels(['%d' % y for y in range(2010, 2016)])
        graph.set_xlimits(1.25, 1.45)
        graph.set_ylimits(-80, 80)
        graph.save_as_pdf('plots/offset_drift_months_%d_simple' % station)
