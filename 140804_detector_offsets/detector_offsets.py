""" Determine detector offset distribution

This determines the detector offsets for all stations in an ESD datafile.
These offsets are then fitted and the results are shown.

Having run this script on several datasets the expected distribution
has a mean of 0 ns and a sigma of 2.7 ns.

"""
import tables
from artist import Plot
from numpy import histogram, arange
from scipy.optimize import curve_fit

from sapphire.analysis.reconstructions import ReconstructESDCoincidences
from sapphire.utils import gauss
from sapphire.clusters import Station

DATA_PATH = '/Users/arne/Datastore/esd/2014/1/'
BIN_WIDTH = 2.5


def determine_offset(dirrec, s_path):
    station_group = dirrec.data.get_node(s_path)
    o = (0, 0, 0)
    station = Station(None, 0, o,
                      detectors=[(o, 'UD'), (o, 'UD'), (o, 'LR'), (o, 'LR')])
    offsets = [offset
               for offset in dirrec.determine_detector_timing_offsets(station, station_group)
               if offset != 0.0]
    return offsets


def determine_offsets(data):
    detector_offsets = []
    dirrec = ReconstructESDCoincidences(data)
    for s_path in dirrec.coincidences_group.s_index:
        detector_offsets.extend(determine_offset(dirrec, s_path))
    return detector_offsets


def fit_offsets(offsets):
    bins = arange(-40 + BIN_WIDTH / 2, 40, BIN_WIDTH)
    y, bins = histogram(offsets, bins=bins)
    x = (bins[:-1] + bins[1:]) / 2
    popt, pcov = curve_fit(gauss, x, y, p0=(len(offsets), 0., 2.5))
    return x, y, popt


def plot_fit(x, y, popt, graph):
    graph.plot(x - BIN_WIDTH / 2, y, mark=None, use_steps=True)
    fit_x = arange(min(x), max(x), 0.1)
    graph.plot(fit_x, gauss(fit_x, *popt), mark=None, linestyle='gray')


if __name__ == '__main__':

    files = ['2014_1_1.h5', '2014_1_2.h5', '2014_1_3.h5', '2014_1_4.h5',
             '2014_1_10.h5', '2014_1_20.h5', '2014_1_30.h5']
    for file in files:
        with tables.open_file(DATA_PATH + file, 'r') as data:
            offsets = determine_offsets(data)

        graph = Plot()
        x, y, popt = fit_offsets(offsets)
        plot_fit(x, y, popt, graph)
        graph.set_label('$\mu$: %f, $\sigma$: %f' % (popt[1], popt[2]))
        graph.set_ylabel('P')
        graph.set_xlabel('$\Delta t$ [ns]')
        graph.set_ylimits(min=0)
        graph.save_as_pdf('detector_offset_distribution_' + file[:-3])
