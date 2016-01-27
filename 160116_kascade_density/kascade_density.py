"""Compare predicted detector density to the detected number of particles

Errors:
- Scintillator transmission and PMT gain errors (relative error of ~70%).
- Error due to non linearity of the PMT curve.
- Poisson error on both in and output.

The MPV is not properly fit in the dataset. The n# columns are simply
pulseheights divided by 380. So determine the MPV (per channel) and correctly
convert pulsehieght to the number of detected particles.

This can probably be improved further by using the pulseintegrals.

The PMT non-linearity needs to be determined per channel. Use the KASCADE
predicted density as the input. After fitting the curve (in = f(out)) the
output can be converted back to the actual expected output.

"""
import tables
from numpy import (histogram2d, histogram, linspace, array, where,
                   log10, inf, sqrt, abs, interp, diff, mean,
                   empty_like, copyto, cos, zeros)
from scipy.stats import poisson, norm

from artist import Plot, MultiPlot

from sapphire.analysis.find_mpv import FindMostProbableValueInSpectrum as FindMPV

from fit_curve import ice_cube_pmt_p1, fit_curve

DATA_PATH = '/Users/arne/Datastore/kascade/kascade-reconstructions.h5'
COLORS = ['black', 'red', 'green', 'blue']
LOG_TICKS = [.1, .2, .3, .4, .5, .6, .7, .8, .9,
             1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 20, 30, 40, 50, 60, 70, 80, 90,
             100, 200, 300, 400, 500, 600, 700, 800, 900]
LOG_LABELS = [''] * len(LOG_TICKS)
LOG_LABELS[0] = '0.1'
LOG_LABELS[1] = '0.2'
LOG_LABELS[4] = '0.5'
LOG_LABELS[9] = '1'
LOG_LABELS[10] = '2'
LOG_LABELS[13] = '5'
LOG_LABELS[18] = '10'
LOG_LABELS[19] = '20'
LOG_LABELS[22] = '50'
LOG_LABELS[31] = '500'

SRC_PH_MPV = 380.  # Pulseheight MPV used for n columns in data file
SRC_PI_MPV = 5000.  # Pulseintegral MPV used for reconstructions_n in data file


def get_out_for_in(actual_in, ref_in, ref_out):
    """Convert an input signal to expected output"""

    return interp(actual_in, ref_in, ref_out)


def get_in_for_out(detected_out, ref_out, ref_in):
    """Convert an output signal to corresponding input"""

    return interp(detected_out, ref_out, ref_in)


def fit_mpvs(ni):
    corrected_ni = empty_like(ni)
    copyto(corrected_ni, ni)
    bins = linspace(0, 3800, 300)
    mpvs = []
    for i in range(4):
        mpv = fit_mpv(ni[:, i] * SRC_PH_MPV, bins)
        mpvs.append(mpv)
        corrected_ni[:, i] = ni[:, i] * (SRC_PH_MPV / mpv)
    return corrected_ni, mpvs


def fit_mpv(n, bins):
    fit = FindMPV(*histogram(n, bins=bins)).find_mpv()
    if not fit[1]:
        RuntimeError("Failed MPV fit.")
    return fit[0]


def residuals(yfit, ydata):
    return ((yfit - ydata) ** 2 / ydata)


class KascadeDensity(object):

    def __init__(self, data_path=DATA_PATH):
        self.lin_bins = linspace(0.5, 500, 200)
        self.ref_out = linspace(0.1, 500, 4000)
        self.ref_in_i = zeros((len(self.ref_out), 4))
        self.lin_out_i = zeros((len(self.lin_bins), 4))
        self.log_bins = linspace(log10(self.lin_bins[0]),
                                 log10(self.lin_bins[-1]), 100)

        with tables.open_file(DATA_PATH, 'r') as data:
            self.read_densities(data)
        self.process_densities()

    def read_densities(self, data):
        """Read and process data points"""

        recs = data.root.reconstructions

        # Pulseheight-based counts (plulseheight / 380.)
        n1 = recs.col('n1')
        n2 = recs.col('n2')
        n3 = recs.col('n3')
        n4 = recs.col('n4')
        self.src_pi = array([n1, n2, n3, n4]).T
        self.src_pi[:, 1] = where(self.src_pi[:, 1] <= 0, 1e-2,
                                  self.src_pi[:, 1])
        self.src_p = self.src_pi.sum(axis=1) / 4.
        self.mph_pi, _ = fit_mpvs(self.src_pi)
        self.mpv_p = self.mph_pi.sum(axis=1) / 4.

        # Pulseintegral-based counts (integrals / 5000.)
        self.src_ni = array(data.root.reconstructions_integrals_n)
        self.src_ni[:, 1] = where(self.src_ni[:, 1] <= 0, 1e-2,
                                  self.src_ni[:, 1])
        self.src_n = self.src_ni.sum(axis=1) / 4.

        # Fit MPV per channel
        self.mpv_ni, self.mpv = fit_mpvs(self.src_ni)
        self.mpv_n = self.mpv_ni.sum(axis=1) / 4.

        self.zenith = recs.col('reference_theta')
#         self.k_ni = ((recs.col('k_dens_mu') + recs.col('k_dens_e')).T * cos(self.zenith)).T
        self.k_ni = (recs.col('k_dens_mu') + recs.col('k_dens_e'))
        self.k_n = self.k_ni.sum(axis=1) / 4.

        # Fit PMT curve
        self.cor_ni = empty_like(self.mpv_ni)
        self.fit_i = []
        for i in range(4):
            filter = (self.k_ni[:, i] > .5) & (self.k_ni[:, i] < 100)
            k = self.k_ni[:, i].compress(filter).tolist()
            h = self.mpv_ni[:, i].compress(filter).tolist()
            try:
                fit = fit_curve(h, k)
            except:
                pass
            self.fit_i.append(fit[0])
            self.ref_in_i[:, i] = ice_cube_pmt_p1(self.ref_out, *fit[0])
            self.lin_out_i[:, i] = get_out_for_in(self.lin_bins, self.ref_in_i[:, i], self.ref_out)
            # Detected n corrected for PMT
            self.cor_ni[:, i] = get_in_for_out(self.mpv_ni[:, i], self.ref_out, self.ref_in_i[:, i])

        filter = (self.k_n > .5) & (self.k_n < 100)
        k = self.k_n.compress(filter).tolist()
        h = self.mpv_n.compress(filter).tolist()
        fit = fit_curve(h, k)  # err=sqrt(k)
        self.ref_in = ice_cube_pmt_p1(self.ref_out, *fit[0])
        self.lin_out = get_out_for_in(self.lin_bins, self.ref_in, self.ref_out)
        # Detected n corrected for PMT
        self.fit = fit[0]
        self.cor_n = get_in_for_out(self.mpv_n, self.ref_out, self.ref_in)

        self.res_ni = residuals(self.cor_ni, self.k_ni)
        self.res_n = residuals(self.cor_n, self.k_n)

    def process_densities(self):
        """Determine errors on the data"""

        # Error due to PMT linearity and ADC/mV resolution
        self.dvindvout = (diff(self.lin_bins) / diff(self.lin_out_i[:,1])).tolist()  # dVin/dVout
        self.dvindvout.extend([self.dvindvout[-1]])
        self.dvindvout = array(self.dvindvout)
        self.sigma_Vout = 0.57 / 2.  # Error on Vout
        self.sigma_Vin = self.sigma_Vout * self.dvindvout

        # Resolution of the detector
        sigma_res = 0.7
        r_lower, r_upper = norm.interval(0.68, self.lin_bins, sqrt(self.lin_bins) * sigma_res)
        self.response_lower = r_lower
        self.response_upper = r_upper
        self.response_lower_pmt = get_out_for_in(r_lower, self.ref_in, self.ref_out)
        self.response_upper_pmt = get_out_for_in(r_upper, self.ref_in, self.ref_out)

        # Poisson error 68% interval (one sigma)
        p_lower, p_upper = poisson.interval(0.68, self.lin_bins)
        self.poisson_lower = p_lower
        self.poisson_upper = p_upper
        self.poisson_lower_pmt = get_out_for_in(p_lower, self.ref_in, self.ref_out)
        self.poisson_upper_pmt = get_out_for_in(p_upper, self.ref_in, self.ref_out)

    def make_plots(self):
#         return

        self.plot_pmt_curves()

#         self.plot_kas_n_histogram()
#         self.plot_src_n_histogram()
#         self.plot_mpv_n_histogram()
        self.plot_cor_n_histogram()

#         self.plot_src_hisparc_kascade_station()
#         self.plot_mpv_hisparc_kascade_station()
        self.plot_cor_hisparc_kascade_station()

#         self.plot_src_hisparc_kascade_detector()
#         self.plot_mpv_hisparc_kascade_detector()
        self.plot_cor_hisparc_kascade_detector()
#         self.plot_mpv_hisparc_pulseheight_detector()

#         self.plot_kascade_detector_average()
#         self.plot_src_hisparc_detector_average()
#         self.plot_mpv_hisparc_detector_average()
        self.plot_cor_hisparc_detector_average()

#         self.plot_src_contribution_detector()
#         self.plot_mpv_contribution_detector()
#         self.plot_cor_contribution_detector()

#         self.plot_src_contribution_station()
#         self.plot_mpv_contribution_station()
#         self.plot_cor_contribution_station()

#         self.plot_derrivative_pmt()

#         self.plot_slice_src()
#         self.plot_slice_mpv()
#         self.plot_slice_cor()

    def plot_xy_log(self, plot):
        """Add x=y line to log plots"""

        plot.plot([log10(.1), log10(max(self.lin_bins))], [log10(.1), log10(max(self.lin_bins))], linestyle='thick, green', mark=None)

    def plot_errors_log(self, plot):
        """Add expected lines to hisparc v kascade density plot"""

#         plot.plot(log10(self.lin_bins - self.sigma_Vin), log10(self.lin_bins), linestyle='thick, blue', mark=None)
#         plot.plot(log10(self.lin_bins + self.sigma_Vin), log10(self.lin_bins), linestyle='thick, blue', mark=None)
#         plot.shade_region(log10(self.lin_bins), log10(self.response_lower), log10(self.response_upper), color='red, opacity=0.2')
#         plot.plot(log10(self.lin_bins), log10(self.response_lower + 0.0001), linestyle='thick, red', mark=None)
#         plot.plot(log10(self.lin_bins), log10(self.response_upper + 0.0001), linestyle='thick, red', mark=None)
#         plot.plot(log10(self.lin_bins), log10(self.poisson_lower + 0.0001), linestyle='thick, green', mark=None)
#         plot.plot(log10(self.lin_bins), log10(self.poisson_upper + 0.0001), linestyle='thick, green', mark=None)
        plot.shade_region(log10(self.lin_bins), log10(self.poisson_lower), log10(self.poisson_upper), color='green, opacity=0.2')

    def plot_2d_histogram_lines(self, plot, n, k_n):
        """Add expected lines to hisparc v kascade density plot"""

#         plot.plot([-10, max(self.lin_bins)], [-10, max(self.lin_bins)], linestyle='thick, green', mark=None)
#         plot.plot(self.lin_bins, self.lin_bins, xerr=self.sigma_Vin, linestyle='thick, blue', mark=None)
        plot.shade_region(self.lin_bins, self.response_lower, self.response_upper, color='red, opacity=0.2')
        plot.shade_region(self.lin_bins, self.poisson_lower, self.poisson_upper, color='green, opacity=0.2')
#         plot.plot(self.lin_bins, self.response_lower, linestyle='thick, red', mark=None)
#         plot.plot(self.lin_bins, self.response_upper, linestyle='thick, red', mark=None)
#         plot.plot(self.lin_bins, self.poisson_lower, linestyle='thick, green', mark=None)
#         plot.plot(self.lin_bins, self.poisson_upper, linestyle='thick, green', mark=None)

    def plot_hisparc_kascade_station(self, n, k_n):
        plot = Plot()
        counts, xbins, ybins = histogram2d(log10(k_n), log10(n),
                                           bins=self.log_bins, normed=True)
        counts[counts == -inf] = 0
        plot.histogram2d(counts, xbins, ybins, bitmap=True, type='reverse_bw')
        self.plot_xy_log(plot)
        plot.set_yticks(log10(LOG_TICKS))
        plot.set_xticks(log10(LOG_TICKS))
        plot.set_ytick_labels(LOG_LABELS)
        plot.set_xtick_labels(LOG_LABELS)
        plot.set_ylabel(r'HiSPARC detected density [\si{\per\meter\squared}]')
        plot.set_xlabel(r'KASCADE predicted density [\si{\per\meter\squared}]')
        return plot

    def plot_src_hisparc_kascade_station(self):
        plot = self.plot_hisparc_kascade_station(self.src_n, self.k_n)
        plot.save_as_pdf('plots/hisparc_kascade_station_src')

    def plot_mpv_hisparc_kascade_station(self):
        plot = self.plot_hisparc_kascade_station(self.mpv_n, self.k_n)
        plot.save_as_pdf('plots/hisparc_kascade_station_mpv')

    def plot_cor_hisparc_kascade_station(self):
        plot = self.plot_hisparc_kascade_station(self.cor_n, self.k_n)
        plot.save_as_pdf('plots/hisparc_kascade_station_cor')

    def plot_hisparc_kascade_detector(self, ni, k_ni):
        plot = MultiPlot(2, 2, width=r'.3\linewidth', height=r'.3\linewidth')
        for i in range(4):
            splot = plot.get_subplot_at(i / 2, i % 2)
            counts, xbins, ybins = histogram2d(log10(k_ni[:, i]), log10(ni[:, i]),
                                               bins=self.log_bins, normed=True)
            counts[counts == -inf] = 0
            splot.histogram2d(counts, xbins, ybins, bitmap=True, type='reverse_bw')
            self.plot_xy_log(splot)
        plot.set_ytick_labels_for_all(None, LOG_LABELS)
        plot.set_xtick_labels_for_all(None, LOG_LABELS)
        plot.set_yticks_for_all(ticks=log10(LOG_TICKS))
        plot.set_xticks_for_all(ticks=log10(LOG_TICKS))
        plot.show_xticklabels_for_all([(1, 0), (0, 1)])
        plot.show_yticklabels_for_all([(1, 0), (0, 1)])
        plot.set_ylabel(r'HiSPARC detected density [\si{\per\meter\squared}]')
        plot.set_xlabel(r'KASCADE predicted density [\si{\per\meter\squared}]')
        return plot

    def plot_src_hisparc_kascade_detector(self):
        plot = self.plot_hisparc_kascade_detector(self.src_ni, self.k_ni)
        plot.save_as_pdf('plots/hisparc_kascade_detector_src')

    def plot_mpv_hisparc_kascade_detector(self):
        plot = self.plot_hisparc_kascade_detector(self.mpv_ni, self.k_ni)
        plot.save_as_pdf('plots/hisparc_kascade_detector_mpv')

    def plot_cor_hisparc_kascade_detector(self):
        plot = self.plot_hisparc_kascade_detector(self.cor_ni, self.k_ni)
        plot.save_as_pdf('plots/hisparc_kascade_detector_cor')

    def plot_mpv_hisparc_pulseheight_detector(self):
        """Compare counts from pulseheight versus counts from integral"""
        plot = self.plot_hisparc_kascade_detector(self.mph_pi, self.mpv_ni)
        plot.set_xlabel(r'HiSPARC integral derived particle density [\si{\per\meter\squared}]')
        plot.set_ylabel(r'HiSPARC pulseheight derived particle density [\si{\per\meter\squared}]')
        plot.save_as_pdf('plots/hisparc_pulseheight_detector_mpv')

    def plot_detector_average(self, n, ni):
        plot = MultiPlot(2, 2, width=r'.3\linewidth', height=r'.3\linewidth')
        for i in range(4):
            splot = plot.get_subplot_at(i / 2, i % 2)
            counts, xbins, ybins = histogram2d(log10(n), log10(ni[:, i]), bins=self.log_bins)
            counts[counts == -inf] = 0
            splot.histogram2d(counts, xbins, ybins, bitmap=True, type='reverse_bw')
        plot.set_ytick_labels_for_all(None, LOG_LABELS)
        plot.set_xtick_labels_for_all(None, LOG_LABELS)
        plot.set_yticks_for_all(ticks=log10(LOG_TICKS))
        plot.set_xticks_for_all(ticks=log10(LOG_TICKS))
        plot.show_xticklabels_for_all([(1, 0), (0, 1)])
        plot.show_yticklabels_for_all([(1, 0), (0, 1)])
        return plot

    def plot_kascade_detector_average(self):
        mplot = self.plot_detector_average(self.k_n, self.k_ni)
        mplot.set_xlabel(r'KASCADE predicted density average [\si{\per\meter\squared}]')
        mplot.set_ylabel(r'KASCADE predicted density detector i [\si{\per\meter\squared}]')
        mplot.save_as_pdf('plots/detector_average_kas')

    def plot_src_hisparc_detector_average(self):
        mplot = self.plot_detector_average(self.src_n, self.src_ni)
        mplot.set_xlabel(r'HiSPARC detected density average [\si{\per\meter\squared}]')
        mplot.set_ylabel(r'HiSPARC detected density detector i [\si{\per\meter\squared}]')
        mplot.save_as_pdf('plots/detector_average_src')

    def plot_mpv_hisparc_detector_average(self):
        mplot = self.plot_detector_average(self.mpv_n, self.mpv_ni)
        mplot.set_xlabel(r'HiSPARC detected density average [\si{\per\meter\squared}]')
        mplot.set_ylabel(r'HiSPARC detected density detector i [\si{\per\meter\squared}]')
        mplot.save_as_pdf('plots/detector_average_mpv')

    def plot_cor_hisparc_detector_average(self):
        mplot = self.plot_detector_average(self.cor_n, self.cor_ni)
        mplot.set_xlabel(r'HiSPARC detected density average [\si{\per\meter\squared}]')
        mplot.set_ylabel(r'HiSPARC detected density detector i [\si{\per\meter\squared}]')
        mplot.save_as_pdf('plots/detector_average_cor')

    def plot_pmt_curves(self):
        plot = Plot('loglog')
        filter = self.ref_out < 500

        for i in range(4):
            filter2 = self.ref_in_i[:, i] < 500
            pin = self.ref_in_i[:, i].compress(filter & filter2)
            pout = self.ref_out.compress(filter & filter2)
            plot.plot(pin, pout, linestyle=COLORS[i], mark=None)
        plot.set_ylimits(min=min(self.lin_bins), max=max(self.lin_bins))
        plot.set_xlimits(min=min(self.lin_bins), max=max(self.lin_bins))
        plot.set_xlabel(r'Input signal')
        plot.set_ylabel(r'Output signal')
        plot.save_as_pdf('plots/pmt_curves')

    def plot_slice(self, n):
        densities = [1, 3, 8, 15, 30]
        bins = linspace(0, 15, 150)
        plot = Plot()
        for density in densities:
            padding = round(sqrt(density) / 2.)
            counts, bins = histogram(n.compress(abs(self.k_n - density) < padding),
                                     bins=bins, density=True)
            plot.histogram(counts, bins)
            plot.add_pin(r'\SI[multi-part-units=single, separate-uncertainty]{%d\pm%d}{\per\meter\squared}' %
                         (density, padding), 'above', bins[counts.argmax()])
        plot.set_ylimits(min=0)
        plot.set_xlimits(min=bins[0], max=bins[-1])
        plot.set_xlabel(r'HiSPARC detected density [\si{\per\meter\squared}]')
        plot.set_ylabel(r'Counts')
        return plot

    def plot_slice_src(self):
        plot = self.plot_slice(self.src_n)
        plot.save_as_pdf('plots/slice_src')

    def plot_slice_mpv(self):
        plot = self.plot_slice(self.mpv_n)
        plot.save_as_pdf('plots/slice_mpv')

    def plot_slice_cor(self):
        plot = self.plot_slice(self.cor_n)
        plot.save_as_pdf('plots/slice_cor')

    def plot_contribution_station(self, n):
        plot = Plot('semilogy')
        colors = ['red', 'blue', 'green', 'purple', 'gray', 'brown', 'cyan',
                  'magenta', 'orange', 'teal']
        padding = 0.5
        bins = linspace(0, 15, 150)
        plot.histogram(*histogram(n, bins=bins))
        plot.draw_vertical_line(1)
        for j, density in enumerate(range(1, 8)):
            counts, bins = histogram(n.compress(abs(self.k_n - density) < padding), bins=bins)
            plot.histogram(counts, bins + (j / 100.), linestyle=colors[j % len(colors)])
        plot.set_ylimits(min=0.9, max=1e4)
        plot.set_xlimits(min=bins[0], max=bins[-1])
        plot.set_xlabel(r'HiSPARC detected density [\si{\per\meter\squared}]')
        plot.set_ylabel(r'Counts')
        return plot

    def plot_src_contribution_station(self):
        plot = self.plot_contribution_station(self.src_n)
        plot.save_as_pdf('plots/contribution_station_scr')

    def plot_mpv_contribution_station(self):
        plot = self.plot_contribution_station(self.mpv_n)
        plot.save_as_pdf('plots/contribution_station_mpv')

    def plot_cor_contribution_station(self):
        plot = self.plot_contribution_station(self.cor_n)
        plot.save_as_pdf('plots/contribution_station_cor')

    def plot_contribution_detector(self, ni):
        plot = MultiPlot(2, 2, 'semilogy', width=r'.3\linewidth', height=r'.3\linewidth')
        colors = ['red', 'blue', 'green', 'purple', 'gray', 'brown', 'cyan',
                  'magenta', 'orange', 'teal']
        padding = 0.5
        bins = linspace(0, 15, 150)
        for i in range(4):
            splot = plot.get_subplot_at(i / 2, i % 2)
            splot.histogram(*histogram(ni[:, i], bins=bins))
            splot.draw_vertical_line(1)
            for j, density in enumerate(range(1, 8)):
                counts, bins = histogram(ni[:, i].compress(abs(self.k_ni[:, i] - density) < padding), bins=bins)
                splot.histogram(counts, bins + (j / 100.), linestyle=colors[j % len(colors)])
        plot.set_ylimits_for_all(min=0.9, max=1e4)
        plot.set_xlimits_for_all(min=bins[0], max=bins[-1])
        plot.show_xticklabels_for_all([(1, 0), (0, 1)])
        plot.show_yticklabels_for_all([(1, 0), (0, 1)])
        plot.set_xlabel(r'HiSPARC detected density [\si{\per\meter\squared}]')
        plot.set_ylabel(r'Counts')
        return plot

    def plot_src_contribution_detector(self):
        plot = self.plot_contribution_detector(self.src_ni)
        plot.save_as_pdf('plots/contribution_detector_scr')

    def plot_mpv_contribution_detector(self):
        plot = self.plot_contribution_detector(self.mpv_ni)
        plot.save_as_pdf('plots/contribution_detector_mpv')

    def plot_cor_contribution_detector(self):
        plot = self.plot_contribution_detector(self.cor_ni)
        plot.save_as_pdf('plots/contribution_detector_cor')

    def plot_n_histogram(self, n, ni, bins):
        """Plot histogram of detected signals"""

        plot = Plot('semilogy')
        plot.histogram(*histogram(n, bins=bins), linestyle='dotted')
        for i in range(4):
            plot.histogram(*histogram(ni[:, i], bins=bins), linestyle=COLORS[i])
        plot.set_ylimits(min=.99)
        plot.set_xlimits(min=bins[0], max=bins[-1])
        plot.set_ylabel(r'Counts')
        return plot

    def plot_kas_n_histogram(self):
        bins = linspace(0, 20, 300)
        plot = self.plot_n_histogram(self.k_n, self.k_ni, bins)
        plot.set_xlabel(r'Particle count')
        plot.save_as_pdf('plots/histogram_kas')

    def plot_src_n_histogram(self):
        bins = linspace(0, 4000, 200)
        plot = self.plot_n_histogram(self.src_n * SRC_PH_MPV, self.src_ni * SRC_PH_MPV, bins)
        for i, mpv in enumerate(self.mpv):
            plot.draw_vertical_line(mpv, linestyle=COLORS[i])
        plot.set_xlabel(r'Pulseheight [ADC]')
        plot.save_as_pdf('plots/histogram_src')

    def plot_mpv_n_histogram(self):
        bins = linspace(0, 10, 200)
        plot = self.plot_n_histogram(self.mpv_n, self.mpv_ni, bins)
        plot.draw_vertical_line(1)
        plot.set_xlabel(r'Particle count')
        plot.save_as_pdf('plots/histogram_mpv')

    def plot_cor_n_histogram(self):
        bins = linspace(0, 20, 300)
        plot = self.plot_n_histogram(self.cor_n, self.cor_ni, bins)
        plot.draw_vertical_line(1)
        plot.set_xlabel(r'Particle count')
        plot.save_as_pdf('plots/histogram_cor')

    def plot_derrivative_pmt(self):
        plot = Plot()
        plot.plot(self.lin_bins, self.dvindvout, mark=None)
        plot.set_xlimits(min=self.lin_bins[0], max=self.lin_bins[-1])
        plot.set_xlabel(r'Particle density [\si{\per\meter\squared}]')
        plot.set_ylabel(r'$\sigma V_{\mathrm{in}}\frac{\mathrm{d}V_{\mathrm{out}}}{\mathrm{d}V_{\mathrm{in}}}$')
        plot.save_as_pdf('plots/derrivative_pmt_saturation')


if __name__ == "__main__":
    kd = KascadeDensity()
    kd.make_plots()
