from experiment_config import ModifyExperiments
import Utils

def get_experiment(experiment_name, db_path):
        
    # Get the experiment.json file if it is already created.
    experiments = Utils.get_experiments(experiment_file=None)

    if experiment_name not in experiments.keys():

        print(f"Experiment {experiment_name} not found. Creating experiment...")
        
        # add_experiment_from_jsonFile(
        # desired experiment name, Name of the setup file in data/experiments folder without extension,
        # path to data/experiments folder)
        # This creates a experiments.json file by comparing the selected experiment setup with base experiment.
        if db_path == "CAESAR":
            ModifyExperiments.add_experiment_from_jsonFile(experiment_name, experiment_name, 
                                    r"/fast/home/l-wijesinghe/MGA/regional/experiments/")
        else:
            ModifyExperiments.add_experiment_from_jsonFile(experiment_name, experiment_name, 
                            r"R:\MGA\regional\experiments")
            
        # Get the experiments.json file created in the previous step
        experiments = Utils.get_experiments(experiment_file=None)
        print(f"Experiment {experiment_name} created.")

    # In the stored potential data in the cluster, the wind onshore data is stored as S2_Expansive_optimalTurbine_existing_TopDown
    # But in the experiment setup files it is as S2_Expansive_existing TopDown
    if experiments[experiment_name]["case_wind"] == "S2_Expansive_existing_TopDown":
        experiments[experiment_name]["case_wind"] = "S2_Expansive_optimalTurbine_existing_TopDown"

    return experiments