import json
import os
from copy import deepcopy
from Utils import get_experiments, get_base_experiment, dump_experiments, get_results, get_results_path, getExperimentAsDict, get_max_autarky_from_reference
import numpy as np
def _add_experiment(experiments, base_experiment, name, experiment_dict):
    
    # make a deep copy of the base experiment (https://docs.python.org/3/library/copy.html)
    experiment = deepcopy(base_experiment["BaseExperiment"])
    # go over all keys in the passed experiment dictionary
    for key in experiment_dict.keys():
        # if the key already exists in the copy of the base experiment 
        if key in experiment.keys():
            # check if there is another level of dictionary below the key (e.g. "heat", "electricity"...) 
            if isinstance(experiment[key], dict):
                # for each _key in the sub dictionary 
                for _key in experiment_dict[key].keys():
                    # check if the _key exists in the base experiment
                    if _key in experiment[key].keys():
                        # replace the value of the _key in the copy of the base experiment 
                        # with the responding value from the passed experiment dictionary
                        experiment[key][_key] = experiment_dict[key][_key]
                    else:
                        raise KeyError(_key + f" not implemented. Please specify one of the following " +
                                        f"{experiment[key].keys()} for key {key}")
            else:
                # replace the value of the _key in the copy of the base experiment 
                # with the responding value from the passed experiment dictionary
                experiment[key] = experiment_dict[key]
        else:
            raise KeyError(key + f" not implemented. Please specify one of the following {experiment.keys()}")
    # make a deep copy of the just created experiment and add it to the list of experiments by its passed name
    experiments[name] = deepcopy(experiment)

    #### Debugging ####
    print("Ammount of experiments:")
    print(len(experiments)) 
    return experiments

# use this function to add a "normal" experiment, that you want to run
def add_experiment(**kwargs):
    experiments = get_experiments()
    base_experiment = get_base_experiment()
    experiments = _add_experiment(experiments, base_experiment, **kwargs)
    dump_experiments(experiments)

#use this function to analyse the difference of different selfsufficient degrees for the passed experiment
def add_selfsufficiency_series(name, experiment_dict, locations=None, steps=5, parallel=False, additional_result_folder=None, check_results=None, experiment_file=None):
    if locations is None:
        locations = experiment_dict["locations"]
    else:
        locations = locations
    experiments = get_experiments(experiment_file=experiment_file)
    base_experiment = get_base_experiment()
    if additional_result_folder:
        results_path = os.path.join(get_results_path(), additional_result_folder)
    else:
        results_path = get_results_path()
        
    try: # check if exp_name is in results
        if parallel:
            res_max_autarky = {}
            res_max_autarky["new self sufficiency"] = {}
            for loc in locations:
                _res_max_autarky = get_results(name + f"_{loc}", results_path)
                if np.isclose(_res_max_autarky["equivalent el. demand"][loc], 0, atol=1e-4): 
                    res_max_autarky["new self sufficiency"][loc] = 1
                else:
                    res_max_autarky["new self sufficiency"][loc] = np.round(1 - (_res_max_autarky["el. purchase"][loc] / _res_max_autarky["equivalent el. demand"][loc]), 5)

        else:
            res_max_autarky = get_results(name, results_path)
    except Exception as e: 
        print(e)
        assert(f"{name} could not be found in results. Please run exp first before running a selfsufficiency series.")
    #use range to define the start and ending of the series, as well as the interval size
    #for example: range(0,105,5) -> from 0% selfsuffiency to 100% selfsufficiency with 5% intervals
    for i in range(0, 100+steps, steps):
        _name = name + "_" + str(i) + "selfsufficiency"
        _locations = deepcopy(locations)
        for loc in _locations:
            if res_max_autarky["new self sufficiency"][loc] < i/100*0.999: # 0.999 due to 
                _locations.remove(loc)

        if parallel:
            for loc in _locations:
                results_available = False
                if check_results is not None:
                    result_path1 = os.path.join(check_results, _name + "_" + loc + ".xlsx")
                    result_path2 = os.path.join(check_results, _name + "_" + loc + ".json")
                    if os.path.isfile(result_path1) and os.path.isfile(result_path2):
                        results_available = True
                if not results_available:
                    experiment_dict["locations"] = [loc]
                    if "electricity" not in experiment_dict.keys():
                        experiment_dict.update({"electricity": {"autarky": {"type": "real", "degree": i/100}}})
                    else:
                        experiment_dict["electricity"].update({"autarky": {"type": "real", "degree": i/100}})
                    experiments = _add_experiment(experiments, base_experiment=base_experiment,  name=_name +f"_{loc}", experiment_dict=experiment_dict)
        else:
            if "electricity" not in experiment_dict.keys():
                    experiment_dict.update({"electricity": {"autarky": {"type": "real", "degree": i/100}}})
            else:
                experiment_dict["electricity"].update({"autarky": {"type": "real", "degree": i/100}})
                experiments = _add_experiment(experiments, base_experiment=base_experiment,  name=_name, experiment_dict=experiment_dict)
    dump_experiments(experiments, experiment_file=experiment_file)

# use this fuction to clean the json file containing all experiments
def flush_experiments(experiment_file=None):
    experiments = get_experiments(experiment_file=experiment_file)
    # make a deep copy of all experiments
    _experiments = deepcopy(experiments)
    # loop over all included experiments in the dictionary 
    # if the experiment is not the BaseExperiment, delete it
    for key in experiments.keys():
        if key != "BaseExperiment":
            _experiments.pop(key)
    # convert the cleaned list back to json
    dump_experiments(_experiments, experiment_file=experiment_file)

# Delete a certain experiment from the json file containing all experiments
def flush_experiment(name, experiment_file=None):
    experiments = get_experiments(experiment_file=experiment_file)
    # make sure that the BaseExperiment can not be deleted
    if name != "BaseExperiment":
        del experiments[name]
    else:
        print("Not deleting BaseExperiment")
    dump_experiments(experiments, experiment_file=experiment_file)

def add_experiment_from_jsonFile(experiment_name, experiment_setupFile, experiment_setupFiles_path): 
    add_experiment(name=experiment_name, experiment_dict=getExperimentAsDict(experiment_setupFile, experiment_setupFiles_path))