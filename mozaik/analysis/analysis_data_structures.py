"""
This module contains the definition of the AnalysisDataStructure API and
implementation of some basic analysis data structures.
"""
import mozaik
import numpy
from mozaik.tools.mozaik_parametrized import MozaikParametrized, SNumber, SInteger, SString
logger = mozaik.getMozaikLogger("Mozaik")


class AnalysisDataStructure(MozaikParametrized):
    """
    Encapsulates data that a certain Analysis class generates.

    An analysis class can generate several AnalysisDataStructures (ADSs) and
    one ADS can be generated by several Analysis classes.
    The goal is to offer a common interface of such data for plotting
    i.e. many analyses can generate 2D tuning curves of several kinds but they
    all share a common data structure and can be plotted in a common way.

    One important aspect of the ADS design is the notion of parameters as
    opposed to inputs. Each ADS should define a number of Parameters (see the
    documentation on Parameters).
    The importance of parameters is that they will offer a way to identify the
    ADS in the data store (see param_filter_query in queries). 
    Furthermore the constructor of the AnalysisDataStructure can
    accept inputs, which are standard variables that should correspond to the
    data that is actually stored in the ADS.

    The five parameters that each ADS has are:

        identifier -
            An important parameter of each AnalysisDataStructure is an
            identifier which is used to identify data structures of common type
            in storage facilities. Currently different datastructures with
            a common interface should share the identifiers but it is not clear
            yet whether this is needed. If it turns out such sharing is not
            necessary it might be abolished and there will be one-to-one
            mapping between AnalysisDataStructure classes and identifiers.

        analysis_algorithm -
            The identity (name) of the analysis class that produced this
            analysis data structure.

        sheet_name -
            The sheet for which this results were computed. None if they do not
            belong to a specific sheet.

        neuron -
            Neuron id to which the data structure belongs. None if it is not
            neuron specific.

        stimulus_id -
            Stimulus id (as string) to which the data structure belongs.
            None if it is not stimulus specific.

        tags -
            In complicated workflows it might become difficult to design a
            filter to extract the right set of recordings or analysis data
            structures for a given analysis or visualization.
            We do not want users to define multiple AnalysisDataStructures that
            hold the same kind of data only to be able to tell them apart.

            Therefore, we also allow all analysis data structures to contain a
            list of tags (which are strings) that one can add during their
            creation (or later) and use them to later for their identification
            in a DataStore. Queries are written that support filtering of ADSs
            based on tags.

            However, in general, we encourage users to use filter methods
            rather than tags to perform their plotting/analysis whenever
            possible!
    """

    identifier = SString(doc="The identifier of the analysis data structure")
    analysis_algorithm = SString(doc="The identifier of the analysis data structure")
    
    neuron = SInteger(default=None,
                           doc="Neuron id to which the datastructure belongs. None if it is not neuron specific")
    sheet_name = SString(default=None,
                              doc="The sheet for which this results were computed. None if they do not belong to specific sheet")
    stimulus_id = SString(default=None,
                               doc="The stimulus for which the results were computed. None if they are not related to specific stimulus")

    def __init__(self,tags=[], **params):
        MozaikParametrized.__init__(self, **params)
        self.tags = tags


class PerNeuronValue(AnalysisDataStructure):
    """
    Data structure holding single value per neuron.

    values
          - The vector of values one per neuron

    value_name
          - The name of the value.

    value_units
          - Quantities unit describing the units of the value

    period
          - The period of the value. If value is not periodic period=None
    
    ids 
          - The ids of the neurons which are stored, in the same order as in the values
    """
    value_name = SString(doc="The name of the value.")
    period = SNumber(units=None,default=None,doc="The name of the value.")

    def __init__(self, values, idds, value_units, **params):
        AnalysisDataStructure.__init__(self, identifier='PerNeuronValue', **params)
        self.value_units = value_units
        self.values = numpy.array(values)
        self.ids = list(idds)
    
    def get_value_by_id(self,idds):
        self.ids
        if isinstance(idds,list) or isinstance(idds,numpy.ndarray):
            return [self.values[list(self.ids).index(i)] for i in idds]
        else:
            return numpy.array(self.values)[list(self.ids).index(idds)]

class AnalysisDataStructure1D(AnalysisDataStructure):
    """
    Data structure representing 1D data.
    All data corresponds to the same axis name and units.
    Explicitly specifies the axis - their name and units.
    Note that at this stage we do not assume the structure in which the data
    is stored.
    Also the class can hold multiple instances of 1D data.

    It uses the quantities package to specify units.
    If at all possible all data stored in numoy arrays should be quantities
    arrays with matching units!

    x_axis_name -
          the name of the x axis
    y_axis_name -
          the name of the y axis
    y_axis_units -
          the quantities units of y axis
    """

    x_axis_name = SString(doc="the name of the x axis.")
    y_axis_name = SString(doc="the name of the y axis.")

    def __init__(self,  y_axis_units, **params):
        AnalysisDataStructure.__init__(self, **params)
        self.y_axis_units = y_axis_units


class AnalogSignalList(AnalysisDataStructure1D):
    """
    This is a simple list of Neo AnalogSignal objects.

    asl -
         the variable containing the list of AnalogSignal objects, in the order
         corresponding to the order of neurons indexes in the indexes parameter.
    ids -
         list of ids of neurons in the original Mozaik sheet to which the
         AnalogSignals correspond.
    """

    def __init__(self, asl, ids, y_axis_units, **params):
        AnalysisDataStructure1D.__init__(self,  y_axis_units,
                                         identifier='AnalogSignalList',
                                         **params)
        self.asl = asl
        self.ids = list(ids)
    
    def get_asl_by_id(self,idd):
        return self.asl[list(self.ids).index(idd)]
    
    def __add__(self, other):
        assert set(self.ids) <= set(other.ids) and set(self.ids) >= set(other.ids)  
        assert self.x_axis_name == other.x_axis_name
        assert self.y_axis_name == other.y_axis_name
        assert self.y_axis_units == other.y_axis_units
        
        new_asl = []
        for idd in self.ids:
            new_asl.append(self.get_asl_by_id(idd) + other.get_asl_by_id(idd))
            
        return AnalogSignalList(new_asl,self.ids,y_axis_units = self.y_axis_units,x_axis_name = self.x_axis_name,y_axis_name = self.y_axis_name, sheet_name = self.sheet_name)
        
class ConductanceSignalList(AnalysisDataStructure1D):
    """
    This is a simple list of Neurotools AnalogSignal objects representing the
    conductances.

    The object holds two lists, one for excitatory and one for inhibitory
    conductances.

    e_asl -
       the variable containing the list of AnalogSignal objects corresponding
       to excitatory conductances, in the order corresponding to the order of
       neurons indexes in the indexes parameter
    i_asl -
       the variable containing the list of AnalogSignal objects corresponding
       to inhibitory conductances, in the order corresponding to the order of
       neurons indexes in the indexes parameter
    ids -
       list of ids of neurons in the original Mozaik sheet to which the
       AnalogSignals correspond
    """

    def __init__(self, e_con, i_con, ids, **params):
        assert e_con[0].units == i_con[0].units
        AnalysisDataStructure1D.__init__(self,
                                         e_con[0].sampling_rate.units,
                                         e_con[0].units,
                                         x_axis_name='time',
                                         y_axis_name='conductance',
                                         identifier='ConductanceSignalList',
                                         **params)
        self.e_con = e_con
        self.i_con = i_con
        self.ids = list(ids)

    def get_econ_by_id(self,idd):
        return self.e_con[self.ids.index(idd)]

    def get_icon_by_id(self,idd):
        return self.i_con[self.ids.index(idd)]

class Connections(AnalysisDataStructure):
    """
    Data structure holding connections.

    proj_name -
            projection name

    source_name -
            the name of the source sheet

    target_name -
            the name of the target sheet

    weights -
            list of tuples (i,j,w) where i is index of pre-synaptic neuron in sheet source_name and j is index of post-synaptic neuron in sheet target_name, and w is the weights
    
    delays -
            list of tuples (i,j,d) where i is index of pre-synaptic neuron in sheet source_name and j is index of post-synaptic neuron in sheet target_name, and d is the delay
    
    """

    proj_name = SString(doc="Projection name.")
    source_name = SString(doc="The name of the source sheet.")
    target_name = SString(doc="The name of the target sheet.")

    def __init__(self, weights, delays, **params):
        AnalysisDataStructure.__init__(self, identifier='Connections', **params)
        self.weights = weights
        self.delays =  delays
