import os
import warnings
import json
from pathlib import Path
import pandas as pd

def get_dataframes(sim_year,datasource_path,location,case,tech): # Getting the energy potential csv files created by Stanley as dataframes
    folder_path = os.path.join(datasource_path,case,f"{tech}_{location}")
    ts_predicted_items = pd.read_csv(os.path.join(folder_path, f"ts_{tech}_{location}_{sim_year}.csv"), index_col= 0)
    predicted_items = pd.read_csv(os.path.join(folder_path, f"{tech}_{location}.csv"), index_col= 0)

    if "Roads" not in tech:
        if os.path.exists(os.path.join(folder_path, f"ts_existing_{tech}_{location}_{sim_year}.csv")):
            ts_existing_items = pd.read_csv(os.path.join(folder_path, f"ts_existing_{tech}_{location}_{sim_year}.csv"), index_col= 0)
        else:
            ts_existing_items = pd.DataFrame()
        if os.path.exists(os.path.join(folder_path, f"existing_{tech}_{location}.csv")):
            existing_items = pd.read_csv(os.path.join(folder_path, f"existing_{tech}_{location}.csv"), index_col= 0)
        else:
            existing_items = pd.DataFrame()

        return ts_predicted_items,predicted_items,ts_existing_items,existing_items
    
    else:
        return ts_predicted_items,predicted_items

def getData(locations, case_wind, case_ofpv, case_pv, case_biomass, scenario_biomass, 
            db_path = "CEASAR",switch_industry = True, sim_year = "2014", pv_groups = 9):
    
    if db_path == "CAESAR": 
        inputDataPath = r"/storage_cluster/internal/data/s-risch"
        datasource_path = r"/storage_cluster/projects/2023_TREP_dev/db_TREP/"

    else:   
        inputDataPath = os.path.join("R:/", "data", "s-risch") # Contains demand data
        datasource_path = os.path.join("R:/","db_TREP") # Contains energy potential data

    locations = locations
    mun_locations = locations
    data = {}
    municipalities = pd.Series(index=locations)
    
    def get_existing_plant_capacities_from_mastr(technology, data_path):
        '''
        Returns the capacities of the existing plants based on the MaStR for the passed technology 

        Parameter
        ---------
        technology: str
            currently supported: run_of_river, tidal, pumped_hydro and wasteplants

        Returns
        -------
        capacity by location: pd.Series
        '''
        df = pd.read_csv(os.path.join(data_path, "mastr", f'{technology}.csv'), dtype={'RS': str, 'ENH_Nettonennleistung': float})
        df = df[['ENH_Nettonennleistung','RS']]
        capacities = {}
        for loc in df.RS.unique():
            capacities[loc] = df.groupby(["RS"]).get_group(loc).sum()["ENH_Nettonennleistung"] * 1e-3
        return pd.Series(capacities)
    
    # Create all relevant instances which are later stored in dictionary for...

    # Onshore Wind
    wind_cap = pd.Series(index=locations)
    wind_or = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    wind_cap_pot = {}
    wind_or_pot = {}
    usable_wind = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    usable_existing_wind = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    usable_predicted_wind = pd.DataFrame(columns=locations, index=list(range(0, 8760)))

    # Open field PV
    ofpv_cap_pot = pd.Series(index=locations)
    ofpv_or_pot = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    ofpv_cap = pd.Series(index=locations)
    ofpv_or = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    ofpv_roads_cap_pot = pd.Series(index=locations)
    ofpv_roads_or_pot = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    usable_ofpv = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    usable_ofpv_roads = pd.DataFrame(columns=locations, index=list(range(0, 8760)))

    # Rooftop PV
    pv_cap = pd.Series(index=locations)
    pv_or = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
    pv_cap = {}
    pv_cap_pot = {}
    pv_or = {}
    flh_wind = {}
    flh_pv = {}
    flh_ofpv = {}
    pv_or_pot = {}
    usable_pv = {}
    
    # Biomass
    usable_biomass = pd.Series(index=locations)
    usable_biogas = pd.Series(index=locations)

    # Waste
    usable_waste = pd.Series(index=locations)

    ###########################################################################################################
    #########################################      POTENTIALS     ############################################# 
    ###########################################################################################################

    for location in locations:

        # Onshore wind
        # file_path = r"PaperPotentials\trep-db\WindOnshore\S1_Legislation\Municipalities"
        ts_predicted_items,predicted_items,ts_existing_items,existing_items = get_dataframes(
            sim_year,datasource_path,location,case=case_wind,tech="Wind")
        
        for group in ts_predicted_items.columns:
            if group not in wind_cap_pot.keys():
                wind_cap_pot[group] = pd.Series(index=locations)
                wind_or_pot[group] = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
                flh_wind[group] = {}
            if group in ts_predicted_items.columns:
                wind_cap_pot[group][location] = \
                    predicted_items.loc[
                        predicted_items[f"group_{sim_year}"] == group].capacity.sum() / 1e3   
                wind_or_pot[group][location] = ts_predicted_items[group]/ 1e3 / wind_cap_pot[group][location]

                if len(wind_or_pot[group][location][wind_or_pot[group][location] < 0]) > 0: # finds the number of negative values in the column wind_or_pot[location]
                    warnings.warn("Replacing neg. value in wind group {} with 0 ".format(group) +
                                "Smallest value was {}".format(wind_or_pot[group][location].min()), UserWarning)
                    # wind_or_pot[group][location][wind_or_pot[group][location] < 0] = 0 
                    wind_or_pot[group].loc[wind_or_pot[group][location] < 0, location] = 0
            else:
                wind_cap_pot[group][location] = 0
                wind_or_pot[group][location] = 0
            flh_wind[group][location] = wind_or_pot[group][location].sum()

        usable_predicted_wind[location] = ts_predicted_items.sum(axis=1) / 1e3

        if len(existing_items) > 0:
            wind_cap[location] = existing_items.capacity.sum() / 1e3
            wind_or[location] = ts_existing_items.sum(axis=1) / 1e3 / wind_cap[location]                
            usable_existing_wind[location] = ts_existing_items.sum(axis=1) / 1e3
            usable_wind[location] = ts_predicted_items.sum(axis=1) / 1e3 \
                                    + ts_existing_items.sum(axis=1) / 1e3
            
            if len(wind_or[location][wind_or[location] < 0]) > 0: # finds the number of negative values in the column wind_or[location]
                warnings.warn("Replacing neg. value in wind group {} with 0 ".format(group) +
                            "Smallest value was {}".format(wind_or_pot[group][location].min()), UserWarning)
                # wind_or[location][wind_or[location] < 0] = 0
                wind_or.loc[wind_or[location] < 0, location] = 0            
        else:
            wind_cap[location] = 0
            wind_or[location] = 0
            usable_wind[location] = ts_predicted_items.sum(axis=1) / 1e3

        for group in wind_cap_pot.keys():
            wind_cap_pot[group] = wind_cap_pot[group].infer_objects().fillna(0)
            wind_or_pot[group] = wind_or_pot[group].infer_objects().fillna(0)
        
        print(f"{location} wind potentials done.")
        #wind_cap[location] = get_capacities(location, file_path)

        # # OpenFieldPV on the side of roads and railways
        # file_path = r"PaperPotentials\trep-db\OpenfieldPV\S3_Combination\Municipalities"
        ts_predicted_items,predicted_items = get_dataframes(
            sim_year,datasource_path,location,case=case_ofpv,tech="OpenfieldPVRoads")

        if case_ofpv == "S2_PoorSoil_existing":
            ofpv_roads_cap_pot[location] = 0
            ofpv_roads_or_pot[location] = 0
            usable_ofpv_roads[location] = 0
        
        else:
            if len(predicted_items) > 0:
                ofpv_roads_cap_pot[location] = predicted_items.capacity.sum() / 1e3
                ofpv_roads_or_pot[location] = ts_predicted_items / 1e3 / ofpv_roads_cap_pot[location]
                usable_ofpv_roads[location] = ts_predicted_items / 1e3

            else:
                ofpv_roads_cap_pot[location] = 0
                ofpv_roads_or_pot[location] = 0
                usable_ofpv_roads[location] = 0

        # OpenFieldPV free field
        ts_predicted_items,predicted_items,ts_existing_items,existing_items = get_dataframes(
            sim_year, datasource_path,location,case=case_ofpv,tech="OpenfieldPV")

        if len(predicted_items) > 0:
            ofpv_cap_pot[location] = predicted_items.capacity.sum() / 1e3
            ofpv_or_pot[location] = ts_predicted_items / 1e3 / ofpv_cap_pot[location]

        else:
            ofpv_cap_pot[location] = 0
            ofpv_or_pot[location] = 0
        
        if len(existing_items) > 0:
            ofpv_cap[location] = existing_items.capacity.sum() / 1e3
            ofpv_or[location] = ts_existing_items / 1e3 / ofpv_cap[location]
            usable_ofpv[location] = ts_existing_items.sum(axis=1) / 1e3 + \
                                    usable_ofpv_roads[location] + \
                                    ts_predicted_items.sum(axis=1) / 1e3
            
        else:
            ofpv_cap[location] = 0
            ofpv_or[location] = 0
            usable_ofpv[location] = usable_ofpv_roads[location] + \
                                    ts_predicted_items.sum(axis=1) / 1e3
            
        flh_ofpv[location] = ofpv_roads_or_pot[location].sum()
        print(f"{location} ofpv potentials done.")
        # ofpv_cap[location] = get_capacities(location, file_path)

        # Rooftop PV 
        def get_rooftop_dataframes(location,folder_path, roof_directions):
            _ts_predicted_items = []
            # Apart from the usual 32 rooftop PV directions, in the stored data some directions are names as "generaion"\
            # These columns should be written in the correct direction
            for direction in roof_directions:
                df = pd.read_csv(os.path.join(folder_path, f"ts_RooftopPV_{location}_{direction}_0_{sim_year}.csv")
                                ,index_col=0)
                if df.columns[0] != direction:
                    column = df.columns[0]
                    df.rename(columns={column: direction}, inplace=True)
                _ts_predicted_items.append(df)

            return ([pd.read_csv(os.path.join(folder_path, f"RooftopPV_{location}_{direction}_0.csv")
                                ,index_col=0) for direction in roof_directions], _ts_predicted_items)
            

        def _group_pv_9(location, locations, df_items, df_ts, cap_dict, or_dict, usable_dict, flh_dict):
            """Aggregate 32 pv groups to 9 pv groups

            Parameters
            ----------
            location : str
            df_items : pd.DataFrame
                df with items
            df_ts : pd.DataFrame
                df with time series
            cap_dict : dict
                dictionary with capacities
            or_dict : dict
                dictionary with operation rates
            usable_dict : dict
                dictionary with usable pv generation
            flh_dict : dict
                dictionary with flh

            Returns
            -------
            cap_dict : dict
                filled dictionary with capacities
            or_dict : dict
                filled dictionary with operation rates
            usable_dict : dict
                filled dictionary with usable pv generation
            flh_dict : dict
                filled dictionary with flh
                """
        
            # directions with "1" at the end will be assigned to a new group called "Flat". 
            # Operation rates and capacities of "1" are summed up. 

            for group in df_ts.columns:
                if group[-1:] == "1":
                    _group = "flat"
                else:
                    _group = group[:-1]
                if _group not in cap_dict.keys():
                    cap_dict[_group] = pd.Series(index=locations, data=0.0)
                    or_dict[_group] = pd.DataFrame(columns=locations, data=0.0, index=list(range(0, 8760)))  
                if _group not in usable_dict.keys():
                    flh_dict[_group] = {}
                    usable_dict[_group] = pd.DataFrame(columns=locations, data=0.0, index=list(range(0, 8760))) 
                if or_dict[_group][location].isna().any():
                    cap_dict[_group][location] = \
                        df_items[df_items.group == _group].capacity.sum() / 1e3 
                    or_dict[_group][location] = df_ts[group] / 1e3
                    usable_dict[_group][location] = df_ts / 1e3 
                else:
                    cap_dict[_group][location] += df_items[df_items.group == _group].capacity.sum() / 1e3
                    or_dict[_group][location] = or_dict[_group][location].add(
                        df_ts[group] / 1e3)
                    usable_dict[_group][location] = usable_dict[_group][location].add(df_ts[group] / 1e3)
            
            for _group in or_dict.keys():
                if cap_dict[_group][location] > 0:
                    or_dict[_group][location] = or_dict[_group][location].divide(cap_dict[_group][location])
                else:
                    or_dict[_group][location] = 0.0
                flh_dict[_group][location] = or_dict[_group][location].sum()
            
            return cap_dict, or_dict, usable_dict, flh_dict                                      
        
        if case_pv == "simplified_PV":
            ts_predicted_items,predicted_items,ts_existing_items,existing_items = get_dataframes(
                sim_year,datasource_path,location,case=case_pv,tech="RooftopPV")
        
        else:
            folder_path = os.path.join(datasource_path,case_pv,f"RooftopPV_{location}")    
            roof_directions = ["E1","S3","NW4","SE2","SW1","SE1","NW3","S2","N3","E3","NW1","W4",
                        "SE4","N2","S1","E4","N4","SE3","SW2","SW4","W2","S4","E2","NE3","N1",
                        "SW3","W3","NW2","NE4","W1","NE1","NE2"]
            
            _predicted_items,_ts_predicted_items = get_rooftop_dataframes(location,folder_path,roof_directions)
            predicted_items = pd.concat(_predicted_items, axis = 0)
            ts_predicted_items = pd.concat(_ts_predicted_items, axis=1)
            ts_existing_items = pd.read_csv(os.path.join(folder_path, f"ts_existing_RooftopPV_{location}_{sim_year}.csv"), index_col= 0)
            existing_items = pd.read_csv(os.path.join(folder_path, f"existing_RooftopPV_{location}.csv"), index_col= 0)
        
        # print(predicted_items.capacity.sum(),flush=True)

        if pv_groups == 1:
            for group in ts_predicted_items.columns:
                if group not in pv_cap_pot.keys():
                    pv_cap_pot[group] = pd.Series(index=locations)
                    pv_or_pot[group] = pd.DataFrame(columns=locations,index=list(range(0, 8760)))
                
                pv_cap_pot[group][location] = predicted_items[predicted_items.group == group].capacity.sum() / 1e3
                pv_or_pot[group][location] = ts_predicted_items[group].sum(axis=1) / 1e3 / pv_cap_pot[group][location]
            usable_pv[location] = ts_predicted_items.sum(axis=1) / 1e3 + ts_predicted_items.sum(axis=1) / 1e3

        elif pv_groups == 9:
            # groups are: "Flat" (all items with tilt 0-20), "S", "W", "N", "E", "SW", "SE", "NW", "NE")

            if len(existing_items) > 0:   
                existing_items["group"] = existing_items.index
                pv_cap, pv_or, usable_pv, flh_pv = \
                _group_pv_9(location=location,
                            locations=locations,
                            df_items=existing_items,
                            df_ts=ts_existing_items,
                            cap_dict=pv_cap,
                            or_dict=pv_or,
                            usable_dict=usable_pv,
                            flh_dict=flh_pv)
            else:
                dummy_groups = ["Flat", "S", "W", "N", "E", "SW", "SE", "NW", "NE"]
                for _group in dummy_groups:
                    if _group not in pv_cap.keys():
                        pv_cap[_group] = pd.Series(index=locations)
                        pv_or[_group] = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
                    pv_cap[_group][location] = 0
                    pv_or[_group][location] = 0
            # print(flh_pv)
            if len(predicted_items) > 0:
                pv_cap_pot, pv_or_pot, usable_pv, flh_pv = \
                    _group_pv_9(location=location,
                                locations=locations,
                                df_items=predicted_items,
                                df_ts=ts_predicted_items,
                                cap_dict=pv_cap_pot,
                                or_dict=pv_or_pot,
                                usable_dict=usable_pv,
                                flh_dict=flh_pv)
            else:
                dummy_groups = ['Flat', 'E', 'N', 'NE', 'NW', 'S', 'SE', 'SW', 'W']
                for _group in dummy_groups:
                    if _group not in pv_cap_pot.keys():
                        pv_cap_pot[_group] = pd.Series(index=locations)
                        pv_or_pot[_group] = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
                    pv_cap_pot[_group][location] = 0
                    pv_or_pot[_group][location] = 0

        elif pv_groups == 32:
            for group in ts_existing_items.columns:
                if group not in pv_cap.keys():
                    pv_cap[group] = pd.Series(index=locations)
                    pv_or[group] = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
                    usable_pv[group] = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
                    flh_pv[group] = {}
                pv_cap[group][location] = existing_items.loc[group].capacity.sum() / 1e3
                pv_or[group][location] = ts_existing_items[group].sum(axis=1) / 1e3 / pv_cap[group][location]
                usable_pv[group][location] = ts_existing_items[group].fillna(0) / 1e3
            
            for group in ts_predicted_items.columns:
                if group not in pv_cap_pot.keys():
                    pv_cap_pot[group] = pd.Series(index=locations)
                    pv_or_pot[group] = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
                if usable_pv[group] is None:
                    usable_pv[group] = pd.DataFrame(columns=locations, index=list(range(0, 8760)))
                    flh_pv[group] = {}
                pv_cap_pot[group][location] = predicted_items[predicted_items.group == group].capacity.sum() / 1e3
                pv_or_pot[group][location] = ts_predicted_items[group].sum(axis=1) / \
                                                predicted_items[predicted_items.group == group].capacity.sum() 
                usable_pv[group][location] = usable_pv[group][location].add(
                                                    ts_predicted_items[group] / 1e3)
            
            for group in ts_predicted_items.columns:
                if pv_or_pot[group].isna().any().any():
                    warnings.warn("nan in pv group " + group, UserWarning)
                pv_or_pot[group] = pv_or_pot[group].fillna(0)
                if len(pv_or_pot[group][pv_or_pot[group] < 0]) > 0: # finds the number of negative values in the column pv_or_pot[group]
                    warnings.warn("Replacing neg. value in {} with 0 ".format(group) +
                                "Smallest value was {}".format(pv_or_pot[group].min().min()), UserWarning)
                    pv_or_pot[group][pv_or_pot[group] < 0] = 0
                    # pv_or_pot.loc[pv_or_pot[group] < 0, group] = 0
                flh_pv[group][location] = pv_or_pot[group][location].sum()

        else:
            raise ValueError(f"{pv_groups} pv groups is not implemented, available options are 9 & 32.")
        # print(flh_pv, flush=True)
        print(f"{location} pv potentials done.")

        # file_path = r"PaperPotentials\trep-db\RooftopPV\NoNorthernRoofs\Municipalities"
        # file = os.path.join(inputDataPath, file_path, "Capacities.csv")
        # df = pd.read_csv(file, index_col=0)
        # indexes = df.index.astype(str)
        # indexes = pd.Series(indexes).apply(lambda x: x if len(x) == 12 else "0" + x)
        # df.index = indexes
        # pv_cap[location] = df.loc[location,:].sum()/1e3

        # Biomass, Biogas
        tech = "Biomass"
        df = pd.read_csv(os.path.join(inputDataPath, "db_TREP",
                                        case_biomass, f"{tech}_{location}", f"{tech}_{location}.csv"))
        usable_biomass[location] = df.loc[df["Biomass/Biogas"] == "Biomass"][f'{scenario_biomass}Energy'].sum()
        usable_biogas[location] = df.loc[df["Biomass/Biogas"] == "Biogas"][f'{scenario_biomass}Energy'].sum()
        print(f"{location} Biomass potentials done.\n")

    ###########################################################################################################
    #########################################        DEMANDS      ############################################# 
    ###########################################################################################################
    
    def get_demand_dataframes(demand):
        demand_path = os.path.join(inputDataPath, "FINE.Regional", "data",
                                    "demand", "KSG2045Demand_" + demand + "_MUN")
        return [pd.read_csv(os.path.join(demand_path, "KSG2045Demand_" + 
                                            demand + "_MUN" + f"_{loc}.csv"), index_col=0)
            for loc in locations]
    
    ##### Heat Demands #####
    demand_heat_residential = pd.concat(get_demand_dataframes("heat_residential"), axis=1)
    demand_heat_cts = pd.concat(get_demand_dataframes("heat_cts"), axis=1)
    demand_heat_industry = pd.concat(get_demand_dataframes("heat_industry"), axis=1)


    ##### Electricity Demands #####
    demand_electricity_residential = pd.concat(get_demand_dataframes("electricity_residential"), axis=1)
    demand_electricity_cts = pd.concat(get_demand_dataframes("electricity_cts"), axis=1)
    demand_electricity_industry = pd.concat(get_demand_dataframes("electricity_industry"), axis=1)
    demand_electricity_transport = pd.concat(get_demand_dataframes("electricity_transport"), axis=1)

    ##### Hydrogen #####
    demand_hydrogen_industry = pd.concat(get_demand_dataframes("hydrogen_industry"), axis=1)
    demand_hydrogen_industry.index = range(0, 8760)
    demand_hydrogen_transport = pd.concat(get_demand_dataframes("hydrogen_transport"), axis=1)
    demand_hydrogen_transport.index = range(0, 8760)

    ##### Process heat #####
    demand_pheat_lowTemperature = pd.concat(get_demand_dataframes("lowTemperature_industry"), axis=1)
    demand_pheat_lowTemperature.index = range(0, 8760)
    demand_pheat_mediumTemperature = pd.concat(get_demand_dataframes("mediumTemperature_industry"), axis=1)
    demand_pheat_mediumTemperature.index = range(0, 8760)
    demand_pheat_highTemperature = pd.concat(get_demand_dataframes("highTemperature_industry"), axis=1)
    demand_pheat_highTemperature.index = range(0, 8760)
    demand_pheat_highTemperature_EAF = pd.concat(get_demand_dataframes("highTemperature_EAF_industry"), axis=1)
    demand_pheat_highTemperature_EAF.index = range(0, 8760)
    demand_pheat_highTemperature_Cement = pd.concat(get_demand_dataframes("highTemperature_cement_industry"), axis=1)
    demand_pheat_highTemperature_Cement.index = range(0, 8760)

    ##### Demand Aggregation #####

    ### Heat Demand ###
    demand_heat = demand_heat_residential + demand_heat_cts
    if switch_industry == 1:
        demand_heat += demand_heat_industry
    demand_heat.index = range(0, 8760)

    ### Electricity Demand ###
    demand_electricity = demand_electricity_residential + demand_electricity_cts + demand_electricity_transport
    if switch_industry == 1:
        demand_electricity += demand_electricity_industry
    demand_electricity.index = range(0, 8760)

    ### Hydrogen Demand ###
    demand_hydrogen = demand_hydrogen_transport
    if switch_industry == 1:
        demand_hydrogen += demand_hydrogen_industry
    demand_hydrogen.index = range(0, 8760)

    ### District Heating Network Costs ###

    def calculate_dhn_investment_cost(area, heat_demand):
        """Calculate cost for district heating network in 1e6 Euro.

        Parameters 
        ----------
        area : float
            settlement area in km²

        heat_demand : float
            heat demand in MWh(th)

        """
        # Calculation based on
        # http://dx.doi.org/10.1016/j.energy.2021.119905

        if area == 0.0 and heat_demand > 0:
            dhn_investment_cost = 0.0
            print("Area is 0 but Heat Demand is not 0. -> Setting District Heating Network Costs to 0.")
        elif area == 0 and heat_demand == 0:
            dhn_investment_cost = 0.0
            print("Area and Heat demand are 0. -> Setting District Heating Network Costs to 0.")
        elif area > 0 and heat_demand == 0:
            dhn_investment_cost = 0.0
            print("Heat Demand is 0. Area is not 0. -> Setting District Heating Network Costs to 0.")
        else:
            heat_density = heat_demand / area
            dhn_investment_cost = 2211.4 * (heat_density / 1000) ** (-0.695)

        return dhn_investment_cost
    
    settlement_area = pd.read_csv(os.path.join(inputDataPath, "FINE.Regional", "data",
                                                'settlements', 'settlement_areas.csv'),
                                dtype={"loc": str}).set_index("loc")
    
    dhn_invest_cost = pd.DataFrame(demand_heat.sum(), columns=["heat demand annually"])

    dhn_invest_cost["investment costs"] = dhn_invest_cost.apply(
        lambda x: calculate_dhn_investment_cost(settlement_area.loc[x.name]["Settlement Area"],
            x["heat demand annually"]),axis=1)
    
    ### Disctrict Heating Capacity Max ###

    def get_cap_max_dhn(location):
        if dhn_invest_cost.loc[location]["investment costs"] == 0:
            return 0.0
        else:
            # Capacity Max = total heat demand + low temperature process heat + 10 % safety margin 
            return (demand_heat[location] + demand_pheat_lowTemperature[location]).max() * 1.1
    
    dhn_invest_cost["capacity max"] = dhn_invest_cost.apply(lambda x: get_cap_max_dhn(x.name), axis=1)

    ##### Get Waste Potentials based on Settlement Areas and Population #####
    population = pd.read_csv(os.path.join(inputDataPath, "FINE.Regional", "data",
                                            'Population', 'population.csv'),
                            dtype={"RS": str}).set_index("RS")
    indexes = population.index.astype(str)
    indexes = pd.Series(indexes).apply(lambda x: x if len(x) == 12 else "0" + x)
    population.index = indexes

    def get_specific_waste_potential(loc):
        ''' returns specific waste potential for passed location based on population density

            Parameters
            ----------
            loc : str 
                location 
            
            Returns 
            -------
            specific waste potential : float
            '''
        ### Specific Waste Potentials ###
        # Source: "Vergleichende Analyse von Siedlungsrestabfällen aus repräsentativen 
        # Regionen in Deutschland zur Bestimmung des Anteils an Problemstoffen 
        # und verwertbaren Materialien"
        # Dornbusch et al. 2020 (UBA)
        # ISSN 1862-4804
        # Potentials of "Altglas", "Metal", "Inertmaterial" and "Problem- und Schadstoffe" are not included 

        rural = 111.1  # kg/(E*a)
        rural_dense = 97.5  # kg/(E*a)
        urban = 135.3  # kg/(E*a)
    
        # Calculate population densitiy in E/km²
        if settlement_area.loc[loc]["Settlement Area"] == 0:
            population_density = 0
            return 0.0
        else:
            population_density = population.loc[loc]["Population"] / settlement_area.loc[loc]["Settlement Area"]
        if population_density < 150:
            return rural
        elif population_density > 150 and population_density < 750:
            return rural_dense
        elif population_density > 750:
            return urban
    
    heating_value_waste = 10 / 3.6 * 1e-3  # MWh/kg Source: "Energieerzeugung aus Abfällen Stand und Potenziale in Deutschland bis 2030", Flamme et al. 2018 (UBA)
    usable_waste = population.loc[locations].apply(
        lambda x: get_specific_waste_potential(x.name) * x * heating_value_waste,
        axis=1).rename(columns={'Population': 'Waste Potential'}) # MWh/a
    
    district_heating_share = pd.Series(index=mun_locations)
    hydro_cap = pd.Series(index=mun_locations)
    hydro_or = pd.DataFrame(columns=mun_locations, index=list(range(0, 8760)))
    bm_cap = pd.Series(index=mun_locations)
    waste_cap_existing = pd.Series(index=mun_locations)

    existing_wasteplants = get_existing_plant_capacities_from_mastr("wasteplants", data_path=os.path.join(
        inputDataPath, "FINE.Regional", "data",))

    for mun in waste_cap_existing.index:
        if mun in existing_wasteplants.index:
            waste_cap_existing[mun] = existing_wasteplants[mun]
        else:
            waste_cap_existing[mun] = 0.0   

    bat_cap = pd.Series(index=locations) # battery capacity dummy?

    # Prevent NaN values if the heat demand of the location is 0
    for location in mun_locations:
        if demand_heat[location].sum() == 0:
            district_heating_share[location] = 0.0
        # TEMP Hard coded District Heat demand for Jülich
        if location == "053580024024":
            district_heating_share[location] = 0.3 
        bat_cap[location] = 0.5
            
    gas_demand = pd.DataFrame(columns=mun_locations, index=list(range(0, 8760)))

    # print("flh wind", flh_wind, flush=True)
    # print("flh pv", flh_pv, flush=True)
    # print("flh ofpv", flh_ofpv, flush=True) 

    print("updating data")
    # Locations
    data.update({"locations": mun_locations})
    # data.update({"municipal areas": municipal_areas})
    # WIND
    data.update({'Wind existing, capacity': wind_cap})  # per group per location existing capacity, unit:MW
    data.update({'Wind potential, capacity': wind_cap_pot}) # per group per location predicted capacity
    data.update({'Wind existing, operationRate': wind_or}) # per group per location existing ts values divided by capacity
    data.update({'Wind potential, operationRate': wind_or_pot}) # per group per location predicted ts values divided by capacity
    data.update({'usable existing wind': usable_existing_wind}) # existing time series summed horizontaly for all wind groups
    data.update({'usable predicted wind': usable_predicted_wind}) # time series summed horizontaly for all wind groups
    data.update({'usable wind': usable_wind}) # usable_existing_wind + usable_predicted_wind
    # OPEN-FIELD PV
    data.update({'OFPV potential, capacity': ofpv_cap_pot}) # per location predicted capacity, unit MW
    data.update({'OFPV potential, operationRateMax': ofpv_or_pot}) # per location predicted ts values divided by capacity
    data.update({'OFPV Roads potential, capacity': ofpv_roads_cap_pot}) # per location predicted capacity, unit MW
    data.update({'OFPV Roads potential, operationRateMax': ofpv_roads_or_pot}) # per location predicted ts values divided by capacity
    data.update({'usable ofpv roads': usable_ofpv_roads}) # predicted time series 
    data.update({'OFPV existing, capacity': ofpv_cap}) # per location existing capacity, unit MW
    data.update({'OFPV existing, operationRateMax': ofpv_or}) # per location existing ts values divided by capacity
    data.update({'usable ofpv': usable_ofpv}) # predicted time series + existing time series + usable_ofpv_roads
    # ROOFTOP PV
    data.update({'PV existing, capacity': pv_cap}) # per group per location existing capacity, unit:MW
    data.update({'PV potential, capacity': pv_cap_pot}) # per group per location predicted capacity
    data.update({'PV existing, operationRateMax': pv_or}) # per group per location existing ts values divided by capacity
    data.update({'PV potential, operationRateMax': pv_or_pot}) # per group per location predicted ts values divided by capacity
    data.update({'usable pv': usable_pv}) # per group per location predicted ts + existing ts
    # BIOMASS
    data.update({'usable biomass': usable_biomass}) # What is the unit? MWh?
    # data.update({'Biomass CHP, capacityFix': bm_cap})
    # BIOGAS
    data.update({'usable biogas': usable_biogas}) # What is the unit? MWh?
    # WASTE
    data.update({'usable waste': usable_waste}) # per location MWh/area
    data.update({'Waste CHP existing, capacityFix': waste_cap_existing}) # per location existing capacity, unit:MW
    # BATTERIES 
    data.update({'Battery, capacityFix': bat_cap}) # per location existing capacity, unit:MWh?
    # DICSTRICT HEATING
    data.update({'District Heating Network, investment costs': dhn_invest_cost['investment costs']})
    data.update({'District Heating Network, capacity max': dhn_invest_cost["capacity max"]})
    # DEMANDS 
    data.update({'Electricity demand, operationRateFix': demand_electricity})
    data.update({'Heat demand, operationRateFix': demand_heat})
    # data.update({'District Heating Share': district_heating_share})
    data.update({'Hydrogen demand, operationRateFix': demand_hydrogen})
    # PROCESS HEAT
    data.update({'Process Heat demand low temperature, operationRateFix': demand_pheat_lowTemperature})
    data.update({'Process Heat demand medium temperature, operationRateFix': demand_pheat_mediumTemperature})
    data.update({'Process Heat demand high temperature, operationRateFix': demand_pheat_highTemperature})
    data.update({'Process Heat demand high temperature EAF, operationRateFix': demand_pheat_highTemperature_EAF})
    data.update({'Process Heat demand high temperature Cement, operationRateFix': demand_pheat_highTemperature_Cement})
    # data.update({'Gas demand, operationRateFix': gas_demand})
    
    for i in data['PV existing, operationRateMax'].keys():
        data['PV existing, operationRateMax'][i] = data['PV existing, operationRateMax'][i].fillna(0)
    
    return data

def offshoreData(case_offshore, db_path="CAESAR", sim_year=2014):
    if db_path == "CAESAR": 
        inputDataPath = r"/storage_cluster/internal/data/s-risch"
        datasource_path = r"/storage_cluster/projects/2023_TREP_dev/db_TREP/"

    else:   
        inputDataPath = os.path.join("R:/", "data", "s-risch")
        datasource_path = os.path.join("R:/","db_TREP")

    node_vectors = {}
    offshore_cap = pd.Series(index=["NorthSea", "BalticSea"])
    offshore_or = pd.DataFrame(columns=["NorthSea", "BalticSea"],
                                  index=list(range(0, 8760)))
    offshore_cap_pot = {}
    offshore_or_pot = {}

    for sea in ["NorthSea", "BalticSea"]:
        ts_predicted_items,predicted_items,ts_existing_items,existing_items = get_dataframes(
            sim_year,datasource_path,sea,case=case_offshore,tech="WindOffshore")
        offshore_cap[sea] = existing_items.capacity.sum() / 1e3
        offshore_or[sea] = ts_existing_items.sum(axis=1) / 1e3 / offshore_cap[sea]

        if len(offshore_or[sea][offshore_or[sea] < 0]) > 0:
            warnings.warn(f"Replacing neg. value in offshore ex with 0 " +
                    f"Smallest value was {offshore_or[sea].min()}", UserWarning)
            offshore_or.loc[offshore_or[sea] < 0, sea] = 0
        
        for group in ts_predicted_items.columns:

            if group not in offshore_cap_pot.keys():
                offshore_cap_pot[group] = pd.Series(index=["NorthSea", "BalticSea"])
                offshore_or_pot[group] = pd.DataFrame(columns=["NorthSea", "BalticSea"], 
                                 index=list(range(0, 8760)))
            
            offshore_cap_pot[group][sea] = predicted_items.loc[
                predicted_items[f"group_{sim_year}"] == group].capacity.sum() / 1e3
            offshore_or_pot[group][sea] = ts_predicted_items[group] / 1e3 / offshore_cap_pot[group][sea]

            if len(offshore_or_pot[group][sea][offshore_or_pot[group][sea] < 0]) > 0:
                warnings.warn(f"Replacing neg. value in wind group {group} with 0 " +
                                f"Smallest value was {offshore_or_pot[group][sea].min()}", UserWarning)
                offshore_or_pot[group].loc[offshore_or_pot[group][sea] < 0, sea] = 0
        
        node_vectors[sea] = os.path.join(datasource_path, 
                                case_offshore, 
                                f"WindOffshore_{sea}",
                                "WindOffshore_potential_area.shp")

    data = {}
    data["Node Vector"] = node_vectors
    data["Offshore existing, capacityFix"] = offshore_cap
    data["Offshore existing, operationRateMax"] = offshore_or
    data["Offshore potential, capacityMax"] = offshore_cap_pot
    data["Offshore potential, operationRateMax"] = offshore_or_pot

    return data        

if __name__ == "__main__":

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Experiments", "all_mun_inclPH.json")) as f:
        experiments = json.load(f)
        db_path="Other"
        switch_industry = True
        case_offshore = "Offshore_S1_Expansive_existing"
        pv_groups = 9
        getData(locations=experiments["locations"], 
                case_wind = experiments["case_wind"], 
                case_ofpv = experiments["case_ofpv"], 
                case_pv = experiments["case_pv"], 
                case_biomass = experiments["case_biomass"],
                scenario_biomass = experiments["biomass"]["scenario"], 
                db_path= db_path,
                switch_industry=switch_industry,
                sim_year = experiments["sim_year"], 
                pv_groups = pv_groups)
        # offshoreData(case_offshore = case_offshore, db_path = db_path, sim_year = sim_year)
        print("getData successfull")
        print("Creating energy system model...")

# sim_path = "R:\db_TREP"
# for file_name in os.listdir(sim_path):
#     print(f"Found file: {file_name}")



