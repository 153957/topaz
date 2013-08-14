"""Test time windows for coincidences

This script gets the number of found coincidences as a function of the
coincidence window.

"""
from itertools import combinations

import matplotlib.pyplot as plt
import tables
import numpy

from sapphire.api import Station, Network
from sapphire.publicdb import download_data
from sapphire.analysis import coincidences


def main():
    station_groups = ['/hisparc/cluster_amsterdam/station_%d' % u for u in STATIONS]

    data = tables.openFile('/Volumes/Hyperdrive/Datastore/esd/2013/8/2013_8_1.h5', 'r')
    coinc = coincidences.Coincidences(data, None, station_groups)

    c_n = []
    windows = 10 ** numpy.arange(1, 15, 0.5)

    for window in windows:
        c, ts = coinc._search_coincidences(window=window)
        c_n.append(len(c))

    plt.figure()
    plt.plot(numpy.log10(windows), c_n)
    plt.annotate('Science Park Cluster\n'
                 'Date: 2013-8-1\n'
                 'Total number of events: %d\n' % len(ts), (0.2, 0.9), xycoords='axes fraction')
    plt.title('Found coincidences versus coincidence window')
    plt.xlabel('Coincidence window (10^x)')
    plt.ylabel('Found coincidences')
    plt.show()
    return c_n, windows


def coincidences_all_stations():
    network = Network()
    station_ids = []
    station_coords = []
    cluster_groups = []
    for station in network.all_stations:
        try:
            info = Station(station['number'])
        except:
            continue
        if info.has_data(year=2013, month=8, day=1):
            cluster_groups.append(info.cluster.lower())
            station_ids.append(station['number'])
            station_coords.append(info.location())

    distances = distance_combinations(station_coords)
    plot_station_distances(distances)

    group_name = 'All stations'

    station_groups = ['/hisparc/cluster_%s/station_%d' % (c, s)
                      for c, s in zip(cluster_groups, station_ids)]

    data = tables.openFile('/Volumes/Hyperdrive/Datastore/esd/2013/8/2013_8_1.h5', 'r')
    coinc = coincidences.Coincidences(data, None, station_groups)

    event_tables = []
    for station_group in coinc.station_groups:
        try:
            event_tables.append(coinc.data.getNode(station_group, 'events'))
        except tables.NoSuchNodeError:
            print 'No events for: %s' % station_group
    find_n_coincidences(coinc, event_tables, group_name)


def coincidences_each_cluster():
    network = Network()
    for cluster in network.all_clusters:
        stations = network.stations(cluster=cluster['number'])
        station_ids = []
        station_coords = []
        cluster_groups = []
        for station in stations:
            try:
                info = Station(station['number'])
            except:
                continue
            if info.has_data(year=2013, month=8, day=1):
                cluster_groups.append(info.cluster.lower())
                station_ids.append(station['number'])
                station_coords.append(info.location())
        if len(station_ids) <= 1:
            continue

        distances = distance_combinations(station_coords)
        plot_station_distances(distances)

        group_name = '%s Cluster' % cluster['name']

        station_groups = ['/hisparc/cluster_%s/station_%d' % (c, s)
                          for c, s in zip(cluster_groups, station_ids)]

        data = tables.openFile('/Volumes/Hyperdrive/Datastore/esd/2013/8/2013_8_1.h5', 'r')
        coinc = coincidences.Coincidences(data, None, station_groups)

        event_tables = []
        for station_group in coinc.station_groups:
            try:
                event_tables.append(coinc.data.getNode(station_group, 'events'))
            except tables.NoSuchNodeError:
                print 'No events for: %s' % station_group
        find_n_coincidences(coinc, event_tables, group_name)


def find_n_coincidences(coinc, event_tables, group_name, plot=True):

    timestamps = coinc._retrieve_timestamps(event_tables)
    ts_arr = numpy.array(timestamps, dtype='3u8')
    n_events = len(timestamps)

    del timestamps

    same_station = numpy.where(ts_arr[:-1, 1] == ts_arr[1:, 1])[0]
    while len(same_station) > 0:
        ts_arr = numpy.delete(ts_arr, same_station, axis=0)
        same_station = numpy.where(ts_arr[:-1, 1] == ts_arr[1:, 1])[0]
    n_filtered = len(ts_arr)

    ts_diff = ts_arr[1:, 0] - ts_arr[:-1, 0]

    del ts_arr

    # 10^14 ns = 1.1 day
    windows = 10 ** numpy.arange(0, 14, 0.2)
    counts = [len(numpy.where(ts_diff < window)[0]) for window in windows]

    if sum(counts) == 0:
        return
    if plot:
        plot_coinc_window(windows, counts, group_name, n_events, n_filtered)


def plot_coinc_window(windows, counts, group_name='', n_events=0, n_filtered=0):
    plt.figure()
    plt.plot(numpy.log10(windows), counts)
    plt.annotate('%s\n'
                 'Date: 2013-8-1\n'
                 'Total n events: %d\n'
                 'No self coincidence events: %d\n' %
                 (group_name, n_events, n_filtered),
                 (0.05, 0.7), xycoords='axes fraction')
    plt.title('Found coincidences versus coincidence window')
    plt.xlabel('Coincidence window (10^x)')
    plt.ylabel('Found coincidences')
    plt.yscale('log')
    plt.ylim(ymin=0.1)
    plt.show()


def Dns(Dm):
    """Convert distance in meters to ns (light travel time)"""
    c = 0.3  # m/ns (or km/us)
    return Dm / c


def plot_station_distances(distances):
    fig = plt.figure()
    ax1 = plt.subplot(111) # y-axis in m
    plt.hist(distances)
    plt.title('Distances between all combinations of 2 stations')
    plt.xlabel('Distance (km)')
    plt.ylabel('Occurance')
    ax2 = plt.twiny() # x-axis in us
    x1, x2 = ax1.get_xlim()
    ax2.set_xlim(Dns(x1), Dns(x2))
    plt.show()


def distance_combinations(coordinates):
    distances = [distance(s1, s2) for s1, s2 in combinations(coordinates, 2)]
    return distances

def distance(s1, s2):
    R = 6371  # km Radius of earth
    d_lat = numpy.radians(s2['latitude'] - s1['latitude'])
    d_lon = numpy.radians(s2['longitude'] - s1['longitude'])
    a = (numpy.sin(d_lat / 2) ** 2 + numpy.cos(numpy.radians(s1['latitude'])) *
         numpy.cos(numpy.radians(s2['latitude'])) * numpy.sin(d_lon / 2) ** 2)
    c = 2 * numpy.arctan2(numpy.sqrt(a), numpy.sqrt(1 - a))
    distance = R * c
    return distance

if __name__ == '__main__':
#    coincidences_each_cluster()
    coincidences_all_stations()

"""
Idea for faster cincidence finding

- Use numpy array
- Find where difference between subsequent elements is less than window
- Then find where difference between those that passed previous check
  also have less difference than window between next (idx+2) element
- ...

ts_arr = np.array(sorted_timestamps)


def coinc_level(ts_arr, window):
    n_coincidence = []
    c_idx = np.where(ts_arr[:-1] - ts_arr[1:] > window)
    tss = len(ts_arr)

    while not len(c_idx[0]) == 0:
        window *= 3
        n_coincidence.append(c_idx)
        c_idx = np.where(ts_arr[c_idx[0]] - ts_arr[c_idx[0] + 1] > window)

    return c_idx

def faculty(n):
    if n == 1:
        return 1
    else:
        return n * faculty(n-1)

"""
