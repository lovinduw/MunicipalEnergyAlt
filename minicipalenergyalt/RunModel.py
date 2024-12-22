import time
import GetExperiment
import GetData
import CreateModel

db_path="Other" # This should be "CAESAR" when run with the FZJ ICE-2 Cluster else "Other"
switch_industry = 1
case_offshore = "Offshore_S1_Expansive_existing"
pv_groups = 9
experiment_name = "casestudy_test"

# Get the required experiment
print("Getting experiments.json...")
t = time.time()
experiments = GetExperiment.get_experiment(experiment_name,db_path)
experiments[experiment_name]["locations"] = ["053150000000"]
# with open(os.join.path(os.path.dirname(os.path.abspath(__file__)), "Experiments", "all_mun_inclPH.json")) as f:
#     experiments = json.load(f)
print(f"Getting experiments.json took {(time.time()-t)} seconds \n")

# Get the required data
print("Getting data...")
t = time.time()
data = GetData.getData(locations=experiments[experiment_name]["locations"],
        case_wind = experiments[experiment_name]["case_wind"],
        case_ofpv = experiments[experiment_name]["case_ofpv"],
        case_pv = experiments[experiment_name]["case_pv"],
        case_biomass = experiments[experiment_name]["case_biomass"],
        scenario_biomass = experiments[experiment_name]["biomass"]["scenario"],
        db_path= db_path,
        switch_industry=switch_industry,
        sim_year = experiments[experiment_name]["sim_year"],
        pv_groups = pv_groups)
# offshoreData(case_offshore = case_offshore, db_path = db_path, sim_year = sim_year)
print(f"getting data successfull after {(time.time()-t)} seconds \n")

# Creating energy system model
# import CreateModel
print("Creating energy system model...")
t = time.time()
esM = CreateModel.create_model(data,experiments[experiment_name],experiment_name, db_path, dataOffshore=None)
print(f"Energy system model created after {(time.time()-t)} seconds \n")

# Applying time series aggregation
def apply_tsa(_esM):
    segmentation = False
    if bool(experiments[experiment_name]["TSA"]):
        numberOfTypicalPeriods=experiments[experiment_name]["TSA"]["numberOfTypicalPeriods"]
        print(f"Number of Typical Periods: {numberOfTypicalPeriods}")
        numberOfSegmentsPerPeriod=experiments[experiment_name]["TSA"]["numberOfSegmentsPerPeriod"]
        print(f"Number of Segments Per Period: {numberOfSegmentsPerPeriod}")
        #TODO replace cluster() with aggregateTemporally ()
        # esM.aggregateTemporally(numberOfTypicalPeriods=12)
        if experiments[experiment_name]["TSA"]["numberOfSegmentsPerPeriod"] < 24:
            segmentation=True
        _esM.aggregateTemporally(
            numberOfTypicalPeriods=numberOfTypicalPeriods,
            numberOfTimeStepsPerPeriod=24,
            storeTSAinstance=False,
            segmentation=segmentation,
            numberOfSegmentsPerPeriod=numberOfSegmentsPerPeriod,
            clusterMethod="hierarchical",
            representationMethod="durationRepresentation",
            # representationMethod="distributionAndMinMaxRepresentation",
            sortValues=False,
            rescaleClusterPeriods=False
            # rescaleClusterPeriods=True
            )
    return _esM, segmentation

if bool(experiments[experiment_name]["TSA"]):
    print("Applying time series aggregation...")
    esM, segmentation = apply_tsa(esM)
else:
    segmentation = False

# Declaring optimization problem
print("Declaring optimization problem...\n")
esM.declareOptimizationProblem(
            timeSeriesAggregation=bool(experiments[experiment_name]["TSA"]),
            # segmentation=segmentation,
            relaxIsBuiltBinary=False,
        )

# Running optimization
try:
    esM.optimize(timeSeriesAggregation=bool(experiments[experiment_name]["TSA"]), solver='gurobi',
                optimizationSpecs='OptimalityTol=1e-6 method=2 cuts=0 crossover=0',
                declaresOptimizationProblem=False, warmstart=False, relaxIsBuiltBinary=True, threads=0)
except Exception as e:
    print(e)
    print("Retrying with BarHomogeneous")
    esM.optimize(timeSeriesAggregation=bool(experiments[experiment_name]["TSA"]), solver='gurobi',
                 declaresOptimizationProblem=False, optimizationSpecs='OptimalityTol=1e-6 method=2 cuts=0 crossover=0 BarHomogeneous=1',
                 warmstart=False, relaxIsBuiltBinary=True, threads=0)

# Running MGA optimization

esM.mga_optimize(timeSeriesAggregation=bool(experiments[experiment_name]["TSA"]), solver='gurobi',
            optimizationSpecs='OptimalityTol=1e-6 method=2 cuts=0 crossover=0',
            # optimizationSpecs="OptimalityTol=1e-3 method=2 cuts=0 MIPGap=5e-3",
            declaresOptimizationProblem=True, warmstart=False, threads=0,
            slack=0.1, iterations = 4, random_seed = False,
            operationRateinOutput = False, writeSolutionsasExcels = True)