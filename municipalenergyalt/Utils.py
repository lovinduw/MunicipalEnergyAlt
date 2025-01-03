import os
import json
import pandas as pd
import geokit as gk
import time
import random

def get_experiment_config_path():
    return os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), "experiment_config"))
def get_experiment_json_path():
    return os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), "experiment_config", "experiments.json"))

def get_base_experiment_json_path():
    return os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), "experiment_config", "base_experiment.json"))

def get_executed_experiments_json_path():
    return os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), "experiment_config", "executed_experiments.json"))

def get_base_experiment():
    with open(get_base_experiment_json_path()) as f:
        base_experiment = json.load(f)
    return base_experiment

# Function that returns one or multiple experiments as a dictionary
def get_experiments(experiment_file=None):
    print(os.path.abspath(__file__))
    if experiment_file is None:
        experiment_file = "experiments.json"
    # if no json file exists for an experiment create a new file with an empty dictionary
    if not os.path.isfile(os.path.join(get_experiment_config_path(), experiment_file)):
        dictionary = {}
        with open(os.path.join(get_experiment_config_path(), experiment_file), "w+") as f:
            json.dump(dictionary, f)
    # if a json file exists for an experiment, load and return the experiment-json file as a dictionary
    with open(os.path.join(get_experiment_config_path(), experiment_file)) as f:
        experiments = json.load(f)
    return experiments

def get_executed_experiments():
    # check if json file already exists 
    # if not create new one
    if not os.path.isfile(get_executed_experiments_json_path()):
        dictionary = {}
        with open(get_executed_experiments_json_path(), "w+") as f:
            json.dump(dictionary, f)
    with open(get_executed_experiments_json_path()) as f:
        executed_experiments = json.load(f)
    return executed_experiments

def dump_experiments(experiments, experiment_file=None):
    if experiment_file is None:
        path = get_experiment_json_path()
    else:
        path = os.path.join(get_experiment_config_path(), experiment_file)
    # Create File to make sure json is not written to twice.
    time.sleep(random.randint(10,100)/10)
    i = 0
    flag_open = path.split("/")[-1].split(".json")[0] + "_json_opened.txt"
    while os.path.isfile(os.path.join(get_experiment_config_path(), flag_open)):
        time.sleep(10)
        i += 1
        if i > 100:
            raise RuntimeError(
                "experiment.json has been opened for too long. Maybe the workflow is corrupt. Try looking at the file.")
    with open(os.path.join(get_experiment_config_path(), flag_open), "w+") as f:
        pass
    with open(path, "w+") as f:
        # convert passed experiments into a json-file
        json.dump(experiments, f)
    os.remove(os.path.join(get_experiment_config_path(), flag_open))
def dump_executed_experiments(executed_experiments):
    with open(get_executed_experiments_json_path(), "w+") as f:
        json.dump(executed_experiments, f)

def get_results_path():
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "data", "output", "experiments")

def get_results(experiment, results_path=None):
    if results_path: 
        with open(os.path.join(results_path, experiment + ".json")) as f:
            results = json.load(f)
    else:
        with open(os.path.join(get_results_path(), experiment + ".json")) as f:
            results = json.load(f)
    return results

def write_experiments_to_text(experiment_file=None):
    if experiment_file is None:
        experiment_file = "experiments.json"
    experiments = get_experiments(experiment_file=experiment_file)
    if experiment_file == "experiments.json":
        txt_name = "experiment_names.txt"
    else:
        txt_name = f"experiment_names_{experiment_file.split('.json')[0].split('experiments_')[1]}.txt"
    with open(os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__)), "experiment_config", txt_name)), "w+") as f:
        for experiment in experiments.keys():
            if experiment != "BaseExperiment":
                f.write(experiment)
                f.write("\n")
    f.close()


def getExperimentAsDict(experiment, experiments_path):
    with open(os.path.join(experiments_path, experiment + ".json")) as json_file:
        return json.load(json_file)

#TODO Move both to one excel sheet 

def write_economic_component_data_to_excel(esM, output_path=None): 
    df = pd.DataFrame(columns=["investPerCapacity", "opexPerCapacity", "opexPerOperation", "economicLifetime"])
    for technology in [technology for technology in esM.componentNames.keys()]:
        if esM.componentNames[technology] == "ConversionModel":
            row = [
                esM.getComponentAttribute(technology, "investPerCapacity")[0],
                esM.getComponentAttribute(technology, "opexPerCapacity")[0],
                esM.getComponentAttribute(technology, "opexPerOperation")[0],
                esM.getComponentAttribute(technology, "economicLifetime")[0]
            ]
            df.loc[technology] = row
    if output_path is not None:
        df.to_excel(os.path.join(output_path, "economic_data_conversions.xlsx"))
    return df

def write_fuel_price_to_excel(esM, output_path=None): 
    df = pd.DataFrame(columns=["fuel price"])
    for technology in [technology for technology in esM.componentNames.keys() 
                            if esM.componentNames[technology] == "SourceSinkModel"
                            and "purchase" in technology]:
            row = [
                esM.getComponentAttribute(technology, "commodityCost")[0],
            ]
            df.loc[technology] = row
    if output_path is not None:
        df.to_excel(os.path.join(output_path, "economic_data_fuel_prices.xlsx"))
    return df


def get_all_municipalities(cluster=False): 
    '''
    Returns all municipalities of germany in a list

    Parameters
    ---------
    cluster: bool 
        False by default. If set to true, the internal cluster path is used instead of the windows network drive path 

    Returns
    -------
    muncipalities
        list of all german municipalities 

    '''
    if cluster is True:
        _path = "/storage_cluster/internal/"
    else:
        _path = r"R:"
    mun_path=os.path.join(_path,"data","s-risch", "shared_datasources",
                                    "germany_administrative",
                                    "2020-01-01",
                                    "vg250_ebenen",
                                    "VG250_GEM.shp")
    municipalities = gk.vector.extractFeatures(mun_path)
    municipalities = municipalities.RS.unique()
    return municipalities


def get_total_el_demand_from_reference(location, exp_name, additional_res_path="casestudy", demand_key="equivalent el. demand"):
    _path = os.path.join(get_results_path(), additional_res_path)
    
    results_dict = get_results(f"{exp_name.split('_')[0]}_{location}", _path)
    print("-------------------")
    print(f"{exp_name.split('_')[0]}_{location}")
    print(results_dict[demand_key][location])
    print("--------------------------") 
    if demand_key in results_dict.keys():
        return results_dict[demand_key][location]
    # TODO!!!
    # _path = os.path.join(get_results_path(), additional_result_path)
    # results_dict = get_results(exp_name, _path) 
    # if "el demand total" in results_dict.keys():
    #     return results_dict["el demand total"][exp_name.split("_")[1]]


def get_max_autarky_from_reference(location):
    _path = os.path.join(get_results_path(), "casestudy")
    results_dict = get_results(f"casestudy_{location}", _path) 
    return results_dict["new self sufficiency"][location]



if __name__ == "__main__":
    pass
    #print(get_total_el_demand_from_reference("053150000000"))