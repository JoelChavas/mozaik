"""
docstring goes here
"""

import numpy
import quantities as qt
import mozaik
import mozaik.tools.units as munits
from neo.core.analogsignalarray import AnalogSignal

logger = mozaik.getMozaikLogger("Mozaik")


def psth(spiketrain, bin_length):
    """
    spiketrain - SpikeTrain object
    The function returns the psth of the spiketrains with bin length bin_length.

    bin_length - (ms) see spike_list explanation


    Note, the spiketrains are assumed to start and stop at the same time!
    """
    t_start = spiketrain.t_start.rescale(qt.ms)
    t_stop = spiketrain.t_stop.rescale(qt.ms)
    num_bins = float((t_stop-t_start)/bin_length)

    range = (float(t_start), float(t_stop))
    h = numpy.histogram(spiketrain, bins=num_bins, range=range)[0] / (bin_length/1000)

    return AnalogSignal(h,t_start=t_start,
                             sampling_period=bin_length*qt.ms,
                             units=munits.spike_per_sec)


def psth_across_trials(spike_trials, bin_length):
    """
    spike_trials - should contain a list of lists of neo spiketrains objects,
    first coresponding to different trials and second to different neurons.
    The function returns the histogram of spikes across trials with bin length
    bin_length.
    Note, the spiketrains are assumed to start and stop at the same time.
    """
    return sum([psth(st, bin_length) for st in spike_trials])/len(spike_trials)
