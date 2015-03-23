import itertools

import numpy as np
from numpy import (nan, isnan, arange, histogram, linspace, pi, array, sqrt,
                   degrees, percentile, isfinite)
import tables

from artist import Plot, PolarPlot

from sapphire.utils import pbar, gauss, ERR, angle_between


STATIONS = [501, 510]
COINDATA_PATH = '/Users/arne/Datastore/501_510/c_501_510_141101_150201.h5'


def plot_angles(data):
    """Make azimuth and zenith plots to compare the results"""

    rec501 = data.get_node('/hisparc/cluster_amsterdam/station_501', 'reconstructions')
    rec510 = data.get_node('/hisparc/cluster_amsterdam/station_510', 'reconstructions')

    zen501 = rec501.col('zenith')
    zen510 = rec510.col('zenith')
    azi501 = rec501.col('azimuth')
    azi510 = rec510.col('azimuth')
    minn501 = rec501.col('min_n')
    minn510 = rec510.col('min_n')

    high_zenith = (zen501 > .2) & (zen510 > .2)

    for minn in [0, 1, 2, 4, 8, 16]:
        filter = (minn501 > minn) & (minn510 > minn)

        length = len(azi501.compress(high_zenith & filter))
        shifts501 = np.random.normal(0, .06, length)
        shifts510 = np.random.normal(0, .06, length)
        azicounts, x, y = np.histogram2d(azi501.compress(high_zenith & filter) + shifts501,
                                         azi510.compress(high_zenith & filter) + shifts510,
                                         bins=np.linspace(-pi, pi, 73))
        plota = Plot()
        plota.histogram2d(azicounts, degrees(x), degrees(y), type='reverse_bw', bitmap=True)
#         plota.set_title('Reconstructed azimuths for events in coincidence (zenith gt .2 rad)')
        plota.set_xlabel(r'$\phi_{501}$ [\si{\degree}]')
        plota.set_ylabel(r'$\phi_{510}$ [\si{\degree}]')
        plota.set_xticks([-180, -90, 0, 90, 180])
        plota.set_yticks([-180, -90, 0, 90, 180])
        plota.save_as_pdf('azimuth_501_510_minn%d' % minn)

        length = len(zen501.compress(filter))
        shifts501 = np.random.normal(0, .04, length)
        shifts510 = np.random.normal(0, .04, length)
        zencounts, x, y = np.histogram2d(zen501.compress(filter) + shifts501,
                                         zen510.compress(filter) + shifts510,
                                         bins=np.linspace(0, pi / 3., 41))
        plotz = Plot()
        plotz.histogram2d(zencounts, degrees(x), degrees(y), type='reverse_bw', bitmap=True)
#         plotz.set_title('Reconstructed zeniths for station events in coincidence')
        plotz.set_xlabel(r'$\theta_{501}$ [\si{\degree}]')
        plotz.set_ylabel(r'$\theta_{510}$ [\si{\degree}]')
        plotz.set_xticks([0, 15, 30, 45, 60])
        plotz.set_yticks([0, 15, 30, 45, 60])
        plotz.save_as_pdf('zenith_501_510_minn%d' % minn)

        distances = angle_between(zen501.compress(filter), azi501.compress(filter),
                                  zen510.compress(filter), azi510.compress(filter))
        counts, bins = np.histogram(distances, bins=linspace(0, pi, 100))
        plotd = Plot()
        plotd.histogram(counts, degrees(bins))
        sigma = degrees(percentile(distances[isfinite(distances)], 67))
        plotd.set_label(r'67\%% within \SI{%.1f}{\degree}' % sigma)
#         plotd.set_title('Distance between reconstructed angles for station events')
        plotd.set_xlabel('Angle between reconstructions [\si{\degree}]')
        plotd.set_ylabel('Counts')
        plotd.set_xlimits(min=0, max=90)
        plotd.set_ylimits(min=0)
        plotd.save_as_pdf('angle_between_501_510_minn%d' % minn)


if __name__ == '__main__':
    with tables.open_file(COINDATA_PATH, 'r') as data:
        plot_angles(data)
