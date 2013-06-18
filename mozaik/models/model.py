"""
docstring goes here

"""
from parameters import ParameterSet
from mozaik.framework.interfaces import MozaikComponent
from mozaik.framework import load_component
from mozaik.stimuli.stimulus import InternalStimulus
import mozaik
import time

try:
    from mpi4py import MPI
except ImportError:
    MPI = None
if MPI:
    mpi_comm = MPI.COMM_WORLD
MPI_ROOT = 0


logger = mozaik.getMozaikLogger("Mozaik")


class Model(MozaikComponent):
    """
    Model encapsulates a mozaik model and defines interfaces
    with which one can do experiments to the model.

    It has to be able to present stimulus  to the input space
    record the activity in the model to this stimulus sequence
    and return it as a neo object.
    For this purpose, derive your model from this Model class and
    give it a member named self.input_layer in the constructor.
    """

    required_parameters = ParameterSet({
        'name': str,
        'results_dir': str,
        'reset': bool,
        'null_stimulus_period': float,
        'input_space': ParameterSet, # can be none - in which case input_space_type is ignored
        'input_space_type': str,  # defining the type of input space, visual/auditory/... it is the class path to the class representing it
    })

    def __init__(self, sim, parameters):
        MozaikComponent.__init__(self, self, parameters)
        self.first_time = True
        self.sim = sim
        self.node = sim.setup(timestep=0.1, min_delay=0.1, max_delay=100.0, threads=3)  # should have some parameters here
        self.sheets = {}
        self.connectors = {}

        # Set-up the input space
        if self.parameters.input_space != None:
            input_space_type = load_component(self.parameters.input_space_type)
            self.input_space = input_space_type(self.parameters.input_space)
        else:
            self.input_space = None
            
        self.simulator_time = 0

    def present_stimulus_and_record(self, stimulus,exc_spike_stimulators,inh_spike_stimulators):
        for sheet in self.sheets.values():
            if self.first_time:
               sheet.record()

        # create empty arrays in annotations to store the sheet identity of stored data
        sim_run_time = self.reset()
        for sheet in self.sheets.values():
            sheet.prepare_input(stimulus.duration,self.simulator_time,exc_spike_stimulators.get(sheet.name,None),inh_spike_stimulators.get(sheet.name,None))
        
        if self.input_space:
            self.input_space.clear()
            self.input_space.add_object(str(stimulus), stimulus)
            if not isinstance(stimulus,InternalStimulus):
                sensory_input = self.input_layer.process_input(self.input_space, stimulus, stimulus.duration, self.simulator_time)
            else:
                self.input_layer.provide_null_input(self.input_space,stimulus.duration,self.simulator_time)
                sensory_input = None                                                    
        else:
            sensory_input = None
             
        sim_run_time += self.run(stimulus.duration)

        segments = []
        if (not MPI) or (mpi_comm.rank == MPI_ROOT):
            for sheet in self.sheets.values():    
                if sheet.to_record != None:
                    if self.parameters.reset:
                        s = sheet.write_neo_object()
                        segments.append(s)
                    else:
                        s = sheet.write_neo_object(stimulus.duration)
                        segments.append(s)

        self.first_time = False
        return (segments, sensory_input,sim_run_time)
        
    def run(self, tstop):
        t0 = time.time()
        logger.info("Simulating the network for %s ms" % tstop)
        self.sim.run(tstop)
        logger.info("Finished simulating the network for %s ms" % tstop)
        self.simulator_time += tstop
        return time.time()-t0

    def reset(self):
        logger.debug("Resetting the network")
        t0 = time.time()
        if self.parameters.reset:
            self.sim.reset()
            self.simulator_time = 0
        else:
            for sheet in self.sheets.values():
                sheet.prepare_input(self.parameters.null_stimulus_period,self.simulator_time,None,None)

            if self.input_space:
                self.input_layer.provide_null_input(self.input_space,
                                                    self.parameters.null_stimulus_period,
                                                    self.simulator_time)
                                                    
            logger.info("Simulating the network for %s ms with blank stimulus" % self.parameters.null_stimulus_period)
            self.sim.run(self.parameters.null_stimulus_period)
            self.simulator_time+=self.parameters.null_stimulus_period
            
            if (not MPI) or (mpi_comm.rank == MPI_ROOT):
                for sheet in self.sheets.values():    
                    if sheet.to_record != None:
                       sheet.write_neo_object()
                    
        return time.time()-t0    
    

    def register_sheet(self, sheet):
        if sheet.name in self.sheets:
            raise ValueError("ERROR: Sheet %s already registerd" % sheet.name)
        self.sheets[sheet.name] = sheet

    def register_connector(self, connector):
        if connector.name in self.connectors:
            raise ValueError("ERROR: Connector %s already registerd" % connector.name)
        self.connectors[connector.name] = connector

    def neuron_ids(self):
        ids = {}
        for s in self.sheets.values():
            ids[s.name] = [int(a) for a in s.pop.all()]
        return ids
        
    def neuron_positions(self):
        pos = {}
        for s in self.sheets.values():
            pos[s.name] = s.pop.positions
        return pos

    def neuron_annotations(self):
        neuron_annotations = {}
        for s in self.sheets.values():
            neuron_annotations[s.name] = s.get_neuron_annotations()
        return neuron_annotations
