""" Overview of Corsika Simulations

Get values from corsika_overview.h5
- particle_id, energy, zenith, azimuth

"""
import tables
import numpy
import artist
from random import choice

from sapphire.corsika.particles import name


OVERVIEW = '/Users/arne/Datastore/CORSIKA/corsika_overview.h5'


# Bins
# t_bins = numpy.arange(-3.75, 56.25, 7.5)
#
# # Particles
# particles = {}
# for p in sims['particle_id']:
#     name = corsika.particles.id[p]
#     if name in particles.keys():
#         particles[name] += 1
#     else:
#         particles[name] = 1
# print particles
#
# pyplot.figure()
# pyplot.xticks(rotation=10)
# pyplot.bar(range(len(particles)), particles.values(), align='center', color='black')
# pyplot.xticks(range(len(particles)), particles.keys())
# pyplot.xlabel('Primary Particle')
# pyplot.ylabel('Count')
# pyplot.title('Number of simulations per primary particle')
# pyplot.show()
#

def plot_energy(energy):
    """Energies"""
    bins = sorted(list(set(energy)))
    bins.append(bins[-1] * 10)
    counts, bins = numpy.histogram(energy, bins=bins)
    graph = artist.Plot(axis='semilogx')
    graph.plot(bins[:-1], counts)
    graph.set_xlabel('Energy [eV]')
    graph.set_ylabel('Count')
    graph.set_ylimits(min=0)
    graph.set_title('Number of simulations per primary energy')
    graph.save_as_pdf('energy')


def plot_zenith(zenith):
    """Zeniths"""
    bins = sorted(list(set(zenith)))
    bins.append(bins[-1] + bins[-1])
    counts, bins = numpy.histogram(zenith, bins=bins)
    graph = artist.Plot()
    graph.plot(bins[:-1], counts)
    graph.set_xlabel('Zenith [rad]')
    graph.set_ylabel('Count')
    graph.set_ylimits(min=0)
    graph.set_title('Number of simulations per zenith angle')
    graph.save_as_pdf('zenith')


def plot_azimuth(azimuth):
    """Azimuths"""
    bins = sorted(list(set(azimuth)))
    bins.append(bins[-1] + bins[-1])
    counts, bins = numpy.histogram(azimuth, bins=bins)
    graph = artist.Plot()
    graph.plot(bins[:-1], counts)
    graph.set_xlabel('Azimuth [rad]')
    graph.set_ylabel('Count')
    graph.set_ylimits(min=0)
    graph.set_title('Number of simulations per azimuth angle')
    graph.save_as_pdf('azimuth')


def plot_energy_zenith(energy, zenith, particle_id=None):
    """Energy, Zenith"""
    e_bins = sorted(list(set(energy)))
    e_bins.append(e_bins[-1] * 10)
    z_bins = sorted(list(set(zenith)))
    z_bins.append(z_bins[-1] + (z_bins[-1] - z_bins[-2]))
    counts, e_bins, z_bins = numpy.histogram2d(energy, zenith, bins=[e_bins, z_bins])
    graph = artist.Plot() # axis='semilogx'
    graph.histogram2d(counts, numpy.log10(e_bins) - 0.5, z_bins - (z_bins[1] / 2), type='area')
    graph.set_xlimits(min=11.5, max=17.5)
    graph.set_xlabel('Energy [eV]')
    graph.set_ylabel('Zenith [rad]')
    graph.set_title('Number of simulations per energy and zenith angle')
    if particle_id is None:
        graph.save_as_pdf('energy_zenith')
    else:
        graph.save_as_pdf('energy_zenith_%s' % name(particle_id))

#
# # Angles vs Energies
# pyplot.figure()
# pyplot.hist2d(sims['energy'], sims['theta'], bins=[e_bins, t_bins], cmap='binary')
# pyplot.xlabel('Energy [log10(GeV)]')
# pyplot.ylabel('Zenith [degrees]')
# pyplot.title('Number of simulations for each energy/zenith combination')
# pyplot.colorbar()
# pyplot.show()

def plot_energy_zenith_per_particle(energy, zenith, particle):
    # Angles vs Energies per Particle
    unique_particles = set(particle)

    for unique_particle in unique_particles:
        s_energy = energy.compress(particle == unique_particle)
        s_zenith = zenith.compress(particle == unique_particle)
        plot_energy_zenith(s_energy, s_zenith, particle_id=unique_particle)


def get_data(overview):
    seed1 = overview.root.simulations.col('seed1')
    seed2 = overview.root.simulations.col('seed2')
    seeds = numpy.array(['%d_%d' % (s1, s2) for s1, s2  in zip(seed1, seed2)])
    particle = overview.root.simulations.col('particle_id')
    energy = overview.root.simulations.col('energy')
    zenith = overview.root.simulations.col('zenith')
    azimuth = overview.root.simulations.col('azimuth')
    return seeds, particle, energy, zenith, azimuth


def get_unique(parameter):
    return sorted(list(set(parameter)))


def get_random_seed(seeds, particle, energy, zenith, e, z):
    result = seeds.compress((energy == e) & (zenith == z) & (particle == 14))
    try:
        return choice(result)
    except IndexError:
        return None

def get_seed_matrix(seeds, particle, energy, zenith):
    unique_energy = get_unique(energy)
    unique_zenith = get_unique(zenith)

    for en in unique_energy:
        for zen in unique_zenith:
            seed = get_random_seed(seeds, particle, energy, zenith, en, zen)
            print ('Energy: 10^%d, Zenith: %4.1f: %s' %
                   (numpy.log10(en), numpy.degrees(zen), seed))


if __name__ == '__main__':
    with tables.open_file(OVERVIEW, 'r') as overview:
        seeds, particle, energy, zenith, azimuth = get_data(overview)
#     plot_energy(energy)
#     plot_zenith(zenith)
#     plot_azimuth(azimuth)
#     plot_energy_zenith(energy, zenith)
#     plot_energy_zenith_per_particle(energy, zenith, particle)
    get_seed_matrix(seeds, particle, energy, zenith)
