#If the optimization is done in nuts2 level
    if locations == "nuts2":
        inputDataPath = os.path.join("R:/", "MGA", "regional", "trep-db-Stanley")
        locations = [i for i in range(1,17)]
        print(locations)
        data = {}

        #To DO
        # # Getting rooftop PV
        # roof_pv_cap_pot = pd.read_csv(
        #     os.path.join(inputDataPath, "RooftopPV", "NoNorthernRoofs", "FederalStates","Capacities.csv"),
        #     index_col=0,
        # )
        # roof_pv_cap_pot["Total_GW"] = roof_pv_cap_pot.sum(axis=1)/1000000
        # roof_pv_cap_pot.drop(roof_pv_cap_pot.columns[[i for i in range(roof_pv_cap_pot.shape[1]-1)]],axis=1, inplace=True)
        # roof_pv_cap_pot = roof_pv_cap_pot.squeeze("columns")

        # data.update({"Rooftop PV, capacityPotentialMax": roof_pv_cap_pot})

        # # Getting open field PV
        # of_pv_cap_pot = pd.read_csv(
        #     os.path.join(inputDataPath, "OpenfieldPV", "S3_Combination", "FederalStates","Capacities.csv"),
        #     usecols=["capacity","Region"]
        # )
        # of_pv_cap_pot = of_pv_cap_pot.groupby(["Region"])["capacity"].sum()/1000000

        # data.update({"Openfield PV, capacityPotentialMax": of_pv_cap_pot})

        # # Getting Wind Onshore
        # wind_onshore_cap_pot = pd.read_csv(
        #     os.path.join(inputDataPath, "WindOnshore", "S1_Legislation", "FederalStates","Capacities.csv"),
        #     usecols=["capacity","Region"],
        # )
        # wind_onshore_cap_pot = wind_onshore_cap_pot.groupby(["Region"])["capacity"].sum()/1000000

        # data.update({"Wind (onshore), capacityPotentialMax": wind_onshore_cap_pot})

        # # Getting wind offshore
        # wind_offshore_cap_pot = pd.read_csv(
        #     os.path.join(inputDataPath, "WindOffshore", "S2_Legislation", "FederalStates","Capacities.csv"),
        #     usecols=["capacity","Region"],
        # )
        # for loc in locations:
        #     wind_offshore_cap_pot = pd.concat([wind_offshore_cap_pot,pd.DataFrame({"Region": [loc], "capacity": [0]})],ignore_index=True)
        # wind_offshore_cap_pot = wind_offshore_cap_pot.groupby(["Region"])["capacity"].sum()/1000000

        # data.update({"Wind (offshore), capacityPotentialMax": wind_offshore_cap_pot})

        # # Getting demand data

        # def get_demand_dataframes(demand):
        #     demand_path = r"R:\MGA\regional\DemandData"
        #     folder_path = os.path.join(demand_path,"KSG2045Demand_" + demand)
        #     df = pd.read_csv(os.path.join(folder_path,"KSG2045Demand_" + demand + ".csv"), index_col=0)
        #     df.index = range(0,8760)
        #     return df
        
        # ##### Heat Demands #####
        # demand_heat_cts = get_demand_dataframes("heat_cts")
        # demand_heat_residential = get_demand_dataframes("heat_residential")
        # demand_heat_industry = get_demand_dataframes("heat_industry")

        # ##### Electricity #####
        # demand_electricity_cts = get_demand_dataframes("electricity_cts")
        # demand_electricity_residential = get_demand_dataframes("electricity_residential")
        # demand_electricity_industry = get_demand_dataframes("electricity_industry")
        # demand_electricity_transport = get_demand_dataframes("electricity_transport")

        # ##### Hydrogen #####
        # demand_hydrogen_industry = get_demand_dataframes("hydrogen_industry")
        # demand_hydrogen_transport = get_demand_dataframes("hydrogen_transport")

        # ##### Process heat #####
        # demand_pheat_lowTemperature = get_demand_dataframes("lowTemperature_industry")
        # demand_pheat_mediumTemperature = get_demand_dataframes("mediumTemperature_industry")
        # demand_pheat_highTemperature = get_demand_dataframes("highTemperature_industry")
        # demand_pheat_highTemperature_EAF = get_demand_dataframes("highTemperature_EAF_industry")
        # demand_pheat_highTemperature_Cement = get_demand_dataframes("highTemperature_Cement_industry")

        # ##### Heat demand aggregation #####
        # demand_heat = demand_heat_residential + demand_heat_cts
        # # if switch_industry["include"] == 1:
        # #     demand_heat += demand_heat_industry

        # ##### Electricity demand aggregation #####
        # demand_electricity = demand_electricity_residential + demand_electricity_cts + demand_electricity_transport
        # # if switch_industry["include"] == 1:
        # #     demand_electricity += demand_electricity_industry

        # ##### Hydrogen demand aggregation #####
        # demand_hydrogen = demand_hydrogen_transport
        # # if switch_industry["include"] == 1:
        # #     demand_hydrogen += demand_hydrogen_industry

        # ### District Heating Network Costs ###
        # settlement_path = r"R:\data\s-risch\FINE.Regional\data\settlements"
        # settlements_data = pd.read_csv(os.path.join(settlement_path, "settlement_areas.csv"), dtype={"loc": str})#.set_index("loc")
        # settlements_data['loc_group'] = settlements_data['loc'].astype(str).str[:2]
        # settlements_data = settlements_data.groupby("loc_group")['Settlement Area'].sum()
        
        # settlements_area = {i:0.0 for i in range(1,17)}
        # for loc in settlements_data.index:
        #     settlements_area[int(loc)] = settlements_data.loc[loc]
        # print(settlements_area)
    
    else:
    locations = locations
    mun_locations = locations
    data = {}
    municipalities = pd.Series(index=locations)

    # def get_capacities(location, file_path):
    #     file = os.path.join(inputDataPath, file_path, "Capacities.csv")
    #     df = pd.read_csv(file, dtype={"Region": str})
    #     df["new_Regions"] = df["Region"].apply(lambda x: x if len(x) == 12 else "0" + x)
    #     capacity = df.loc[df["new_Regions"] == location]["capacity"].sum()/1e3 
    #     return capacity

    # def get_dataframes(datasource_path,location,case,tech): # Getting the energy potential csv files created by Stanley as dataframes
    #     folder_path = os.path.join(datasource_path,case,f"{tech}_{location}")
    #     ts_predicted_items = pd.read_csv(os.path.join(folder_path, f"ts_{tech}_{location}_{sim_year}.csv"), index_col= 0)
    #     predicted_items = pd.read_csv(os.path.join(folder_path, f"{tech}_{location}.csv"), index_col= 0)

    #     if "Roads" not in tech:
    #         if os.path.exists(os.path.join(folder_path, f"ts_existing_{tech}_{location}_{sim_year}.csv")):
    #             ts_existing_items = pd.read_csv(os.path.join(folder_path, f"ts_existing_{tech}_{location}_{sim_year}.csv"), index_col= 0)
    #         else:
    #             ts_existing_items = pd.DataFrame()
    #         if os.path.exists(os.path.join(folder_path, f"existing_{tech}_{location}.csv")):
    #             existing_items = pd.read_csv(os.path.join(folder_path, f"existing_{tech}_{location}.csv"), index_col= 0)
    #         else:
    #             existing_items = pd.DataFrame()

    #         return ts_predicted_items,predicted_items,ts_existing_items,existing_items
        
    #     else:
    #         return ts_predicted_items,predicted_items