"""
Module containing the experiment API.
"""
import numpy
import resource
import mozaik
from mozaik.stimuli import InternalStimulus
from parameters import ParameterSet

logger = mozaik.getMozaikLogger()


class Experiment(object):
    """
    The abastract class for an experiment. The experiment defines the list of 
    stimuli that it needs to present to the brain.These stimuli presentations have to be independent - e.g. should not
    temporarily depend on each other. Experiment should also specify the analysis of the
    recorded results that it performs. This can be left empty if analysis will
    be done later.
    
    The experiment has to also define the `direct_stimulation` variable which should contain a list of dictionaries one per each stimulus.
    The keys in these dictionaries are sheet names and values are list of :class:`mozail.sheets.direct_stimulator.DirectStimulator` instances,
    that specify what direct stimulations should be applied to given layers during the corresponding stimulus. Layers to which no direct stimulation 
    is applied can stay empty. Also if the direct_stimulation is set to None, empty dictionaries will be automatically passed to the model, 
    indicating no direct stimulation is required.
    
    Parameters
    ----------
    model : Model
          The model on which to execute the experiment.

    NOTE
    ----
    When creating a new Expriment, user inherits from the Experiment class, and in the constructor fills up the `self.stimuli` array with the list of stimuli
    that the experiment presents to the model. One can also implement the do_analysis method, which should perform the analysis that the experiments requires
    at the end. 
    """
    
    def __init__(self, model):
        self.model = model
        self.stimuli = []
        self.direct_stimulation = None
    
    def return_stimuli(self):
        """
        This function is called by mozaik to retrieve the list of stimuli the experiment requires to be presented to the model.
        """
        return self.stimuli
        
    def run(self,data_store,stimuli):
        """
        This function is called to execute the experiment.
        
        Parameters
        ----------
        
        data_store : DataStore
                   The data store into which to store the recorded data.
                   
        stimuli : list(Stimulus)
                The list of stimuli to present to the model.
        
        Returns
        -------
        strsum : int (s)
               The overal simulation time it took to execute the experiment.
                
        Notes
        -----
        The reason why this function gets a list of stimuli as input is that even though the experiment itself defines the list of stimuli
        to present to the model, some of these might have already been presented. The module `mozaik.controller` filters
        the list of stimuli which to present to prevent repetitions, and lets this function know via the stimuli argument which stimuli to actually present.
        """
        srtsum = 0
        for i,s in enumerate(stimuli):
            logger.debug('Presenting stimulus: ' + str(s) + '\n')
            if self.direct_stimulation == None:
               ds = {}
            else:
               ds = self.direct_stimulation[self.stimuli.index(s)]
            (segments,null_segments,input_stimulus,simulator_run_time) = self.model.present_stimulus_and_record(s,ds)
            srtsum += simulator_run_time
            data_store.add_recording(segments,s)
            data_store.add_stimulus(input_stimulus,s)
            
            if null_segments != []:
               data_store.add_null_recording(null_segments,s) 
            
            logger.info('Stimulus %d/%d finished. Memory usage: %iMB' % (i+1,len(stimuli),resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
        return srtsum
        
    def do_analysis(self):
        raise NotImplementedError
        pass

class PoissonNetworkKick(Experiment):
    """
    This experiment does not show any stimulus.
    Importantly for the duration of the experiment it will stimulate neurons 
    definded by the recording configurations in recording_configuration_list
    in the sheets specified in the sheet_list with Poisson spike train of mean 
    frequency determined by the corresponding values in lambda_list.
    
    Parameters
    ----------
    model : Model
          The model on which to execute the experiment.


    duration : str
             The duration of single presentation of the stimulus.
    
    sheet_list : int
               The list of sheets in which to do stimulation

    drive_period : float (ms)
                 The length of the constant drive, after which it will be linearly taken down to 0 at the end of the stimulation.   
                        
    stimulation_configuration : ParameterSet
                              The parameter set for direct stimulation specifing neurons to which the kick will be administered.
                                 
    lambda_list : list
                List of the means of the Poisson spike train to be injected into the neurons specified in stimulation_configuration (one per each sheet).
    
    weight_list : list
                List of spike sizes of the Poisson spike train to be injected into the neurons specified in stimulation_configuration (one per each sheet).
    """
    
    def __init__(self,model,duration,sheet_list,drive_period,stimulation_configuration,lambda_list,weight_list):
            Experiment.__init__(self, model)
            from mozaik.sheets.direct_stimulator import Kick
            
            d  = {}
            for i,sheet in enumerate(sheet_list):
                d[sheet] = [Kick(model.sheets[sheet],ParameterSet({'exc_firing_rate' : lambda_list[i],
                                                      'exc_weight' : weight_list[i],
                                                      'drive_period' : drive_period,
                                                      'population_selector' : stimulation_configuration})
                                )]
            
            self.direct_stimulation = [d]

            self.stimuli.append(
                        InternalStimulus(   
                                            frame_duration=duration, 
                                            duration=duration,
                                            trial=0,
                                            direct_stimulation_name='Kick'
                                         )
                                )
        
class NoStimulation(Experiment):
    """
    This experiment does not show any stimulus for the duration of the experiment.
    
    Notes
    -----
    Unlike :class:`.MeasureSpontaneousActivity` this can be used in model with no sensory input sheet.
    """
    
    def __init__(self,model,duration):
        Experiment.__init__(self, model)
        self.stimuli.append(
                        InternalStimulus(   
                                            frame_duration=duration, 
                                            duration=duration,
                                            trial=0,
                                            direct_stimulation_name='None'
                                         )
                                )
