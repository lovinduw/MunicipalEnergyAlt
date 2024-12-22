import warnings
import fine as fn
import pandas as pd
import os
import numpy as np 
from Utils import get_total_el_demand_from_reference
import sys 
from copy import deepcopy


round_factor = 5
stability_factor = 1000
charge_cost=10**(-6)

def create_esm(data, locations, autarky=None, biomass_limit=True, biogas_limit=False, waste_included=True, experiment_name=None, additional_results_path=None): #TODO Change default for biogas to True when implemented
    """Create EnergySystemModel instance

    Parameters
    ----------
    data : dict
        Dictionary with all relevant data to create model. Can be generated
        with getData.py
    locations : set
        set with locations
    autarky : float or pd.DataFrame, optional
        Either float specifying the balance autarky in the regions as share of 
        demand or pd.DataFrame specifying the limit in absolute values,
        by default None

    Returns
    -------
    fine.EnergySystemModel
        esm instance
    """
    commodities = {"placeholder"}
    commodityUnitsDict = {"placeholder": "placeholder"}
    commodityLimits = pd.DataFrame()
    # Add Waste Limit to commodity limits 
    # TODO implement switch, if wanted
    if waste_included:
        waste_limit = pd.DataFrame(columns=list(locations))
        if isinstance(data["usable waste"], pd.Series):
            waste_limit.loc["waste"] = data["usable waste"]
        else:
            waste_limit.loc["waste"] = data["usable waste"]["Waste Potential"]
        # commodityLimits = commodityLimits.append(waste_limit)
        commodityLimits = pd.concat([commodityLimits, waste_limit])
        

    if biomass_limit:
        biomassLimit_df = add_biomass_limit(data)
    
    if biogas_limit:
        biogasLimit_df = add_biogas_limit(data)

    # Create ESM: Check if autarky is considered
    if autarky is not None:
        # If limit is float:
        if isinstance(autarky, float) or isinstance(autarky, int):
            # Calculate individual electricity demand for each location based on passed autarky float 
            # Assign those values to their corresponding locations in a pd.DataFrame
            autarkyLimit = pd.DataFrame(columns=list(locations))  
            autarkyLimit.loc["el"] = pd.Series([0 for x in autarkyLimit.columns])
            if autarky != 1:
                if additional_results_path is not None:
                    autarkyLimit.loc["el"] = autarkyLimit.apply(lambda x: get_total_el_demand_from_reference(x.name, experiment_name, additional_results_path)) * (1 - autarky)
                else:
                    raise ValueError("additional_results_path has to be defined when running a degree of self sufficiency")
            else:
                autarkyLimit.loc["el"] = 0
            print("------------- Autarky Limit ---------------")
            print(autarkyLimit)
            # commodityLimits = commodityLimits.append(autarkyLimit)  
            commodityLimits = pd.concat([commodityLimits,autarkyLimit])    
            if biomass_limit: 
                # commodityLimits = commodityLimits.append(biomassLimit_df)
                commodityLimits = pd.concat([commodityLimits,biomassLimit_df])
            if biogas_limit: 
                # commodityLimits = commodityLimits.append(biogasLimit_df) #TODO Replace Placeholder
                commodityLimits = pd.concat([commodityLimits,biogasLimit_df])
        # If limit is pd.DataFrame:
        elif isinstance(autarky, pd.DataFrame) or isinstance(autarky, pd.Series):
            # commodityLimits = commodityLimits.append(autarky) 
            commodityLimits = pd.concat([commodityLimits,autarky]) 
            if biomass_limit: 
                # commodityLimits = commodityLimits.append(biomassLimit_df)
                commodityLimits = pd.concat([commodityLimits,biomassLimit_df])
            if biogas_limit: 
                # commodityLimits = commodityLimits.append(biogasLimit_df) #TODO Replace Placeholder
                commodityLimits = pd.concat([commodityLimits,biogasLimit_df])
        esM = fn.EnergySystemModel(locations=locations, commodities=commodities,
                                    numberOfTimeSteps=8760,
                                    commodityUnitsDict=commodityUnitsDict,
                                    hoursPerTimeStep=1, costUnit='1e6 Euro',
                                    lengthUnit='km', verboseLogLevel=0, 
                                    balanceLimit=commodityLimits)
    
    # elif autarky is None and not biomass_limit and not biogas_limit and not waste_limit:
    #     esM = fn.EnergySystemModel(locations=locations, commodities=commodities,
    #                             numberOfTimeSteps=8760,
    #                             commodityUnitsDict=commodityUnitsDict,
    #                             hoursPerTimeStep=1, costUnit='1e6 Euro',
    #                             lengthUnit='km', verboseLogLevel=0
    #                             )
    else:
        # Check if biomass and/or biogas are limited 
        if biomass_limit: 
            # commodityLimits = commodityLimits.append(biomassLimit_df)
            commodityLimits = pd.concat([commodityLimits,biomassLimit_df])
        if biogas_limit:
            # commodityLimits = commodityLimits.append(biogasLimit_df)
            commodityLimits = pd.concat([commodityLimits,biogasLimit_df])
        # print("---------------------------------------")
        # print("---------------------------------------")
        # print(commodityLimits)
        # print("---------------------------------------")
        # commodityLimits = commodityLimits.sum(axis=1)
        # print("---------------------------------------")
        # print("---------------------------------------")
        # print(commodityLimits)
        # print("---------------------------------------")
        if not commodityLimits.empty:
            esM = fn.EnergySystemModel(locations=locations, commodities=commodities,
                                       numberOfTimeSteps=8760,
                                       commodityUnitsDict=commodityUnitsDict,
                                       hoursPerTimeStep=1, costUnit='1e6 Euro',
                                       lengthUnit='km', verboseLogLevel=0,
                                       balanceLimit=commodityLimits
                                       )
        else:
            esM = fn.EnergySystemModel(locations=locations, commodities=commodities,
                                       numberOfTimeSteps=8760,
                                       commodityUnitsDict=commodityUnitsDict,
                                       hoursPerTimeStep=1, costUnit='1e6 Euro',
                                       lengthUnit='km', verboseLogLevel=0)
        

    #TODO Test what happens if no biomass limit is passed as a balance Limit                        
    # Clear placeholders
    esM.commodities.remove("placeholder")
    esM.commodityUnitsDict.pop("placeholder")
    print(commodityLimits)
    return esM

def add_biomass_limit(data):
    # Add biomass limit
    biomassLimit_df = pd.DataFrame()
    biomassLimit_df["biomass"] = data["usable biomass"]
    biomassLimit_df = biomassLimit_df.transpose()
    return biomassLimit_df

def add_biogas_limit(data):
    # Add biogas limit
    biogasLimit_df = pd.DataFrame()
    biogasLimit_df["biogas"] = data["usable biogas"]
    biogasLimit_df = biogasLimit_df.transpose()
    return biogasLimit_df

def add_electricity(esM):
    # Add Electricity commodities.
    esM.commodityUnitsDict.update({'electricity': r'MW$_{el}$', 'electricity_pv_sc': r'MW$_{el}$', 'electricity_pv': r'MW$_{el}$', 'electricity_demand': r'MW$_{el}$', 'electricity_bat': r'GW$_{el}$', 'electricity_bat_ss': r'GW$_{el}$'})
    esM.commodities.update({'electricity', 'electricity_pv_sc', 'electricity_pv', 'electricity_demand', 'electricity_bat', 'electricity_bat_ss'})
    return esM

def add_grid(esM, data, cost_data, factor_grid_cost=1, interestRate=0.06, locationalEligibility=None):
    # Add artificial grid

    # Add Openfield PV (Openfield and side of roads)
    if "electricity_grid" not in esM.commodities:
        esM.commodities.update({'electricity_grid'})
        esM.commodityUnitsDict.update({'electricity_grid': r'MW$_{el}$'})
    # Existing grid can convert to electricity. Is scaled by demand.
    # has no cost and is therefore always used before "building new grid"
    # esM.add(fn.Conversion(esM=esM, name='existing_grid',
    #             physicalUnit=r'MW$_{el}$',
    #             commodityConversionFactors={
    #                 'electricity_grid': -1,
    #                 'electricity': 1
    #             },
    #             hasCapacityVariable=True,
    #             interestRate=interestRate, economicLifetime=40,
    #             investPerCapacity=grid_cost, opexPerCapacity=0,
    #             capacityFix=existing_grid))
    # print(f"Existing grid {existing_grid}")

    # Additional grid has to be built and adds cost for system
    esM.add(fn.Conversion(esM=esM, name='grid',
                    locationalEligibility=locationalEligibility,
                    physicalUnit=r'MW$_{el}$',
                    commodityConversionFactors={
                        'electricity_grid': -1,
                        'electricity': 1
                    },
                    hasCapacityVariable=True,
                    investPerCapacity=cost_data["capex"]*factor_grid_cost, 
                    opexPerCapacity=cost_data["opex_fix"],
                    opexPerOperation=cost_data["opex_var"],  # Schöb
                    interestRate=cost_data["wacc"], 
                    economicLifetime=cost_data["lifetime"]))
    return esM

def add_wind_potential(esM, data, cost_data, share=1.0):
    # import ipdb;ipdb.set_trace()
    # Add potential wind turbines
    # TODO: implement share (i.e.: reduce the worst flh groups)

    # For each group one source is created
    # Commodity is electricity grid (has to be converted by grid)
    for group in data["Wind potential, capacity"].keys():
        if share > 0 and any(data['Wind potential, capacity'][group] > 0):
            esM.add(fn.Source(esM=esM, name=group, commodity='electricity_grid',
                    hasCapacityVariable=True,
                    capacityMax=data['Wind potential, capacity'][group],
                    operationRateMax=data['Wind potential, operationRate'][group],
                    capacityVariableDomain="continuous",
                    investPerCapacity=cost_data["capex"], 
                    opexPerCapacity=cost_data["opex_fix"],
                    opexPerOperation=cost_data["opex_var"],  # Schöb
                    interestRate=cost_data["wacc"], 
                    economicLifetime=cost_data["lifetime"],))

    return esM

def add_offshore_wind_potential(esM, data, cost_data, locationalEligibility=None, share=1.0):
    # Add potential offshore wind turbines

    # For each group one source is created
    # Commodity is electricity grid (has to be converted by grid)
    for group in data["Offshore potential, capacityMax"].keys():
        if share > 0 and any(data['Offshore potential, capacityMax'][group] > 0):
            esM.add(fn.Source(esM=esM, 
                    name=f"Offshore_{group.split('Wind_')[1]}",
                    commodity='electricity', # Cost is already in the distance and component
                    locationalEligibility=locationalEligibility,
                    hasCapacityVariable=True,
                    capacityMax=data['Offshore potential, capacityMax'][group],
                    operationRateMax=data['Offshore potential, operationRateMax'][group],
                    capacityVariableDomain="continuous",
                    investPerCapacity=cost_data["capex"], 
                    opexPerCapacity=cost_data["opex_fix"],
                    opexPerOperation=cost_data["opex_var"],
                    interestRate=cost_data["wacc"], 
                    economicLifetime=cost_data["lifetime"]))
        # TODO Implement costs in a clean way. Therfore, in the 
        # createModelFromJson function the get_cost_data fct has to be 
        # isolated
    return esM

def add_offshore_wind_existing(esM, data, cost_data, locationalEligibility=None, existing_fixed=False):
    # Add existing turbines
    # Commodity is electricity grid (has to be converted by grid)
    if existing_fixed:
        if any(data["Offshore existing, capacityFix"] > 0):
            esM.add(fn.Source(esM=esM, name='Offshore, existing', commodity='electricity', # Cost is already in the distance and component# Cost is already in the distance and component
                            hasCapacityVariable=True,
                            capacityFix=data['Offshore existing, capacityFix'],
                            operationRateMax=data['Offshore existing, operationRateMax'],
                            capacityVariableDomain="continuous",
                            locationalEligibility=locationalEligibility,
                            investPerCapacity=cost_data["capex"], 
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    else:
        if any(data["Offshore existing, capacityFix"] > 0):
            esM.add(fn.Source(esM=esM, name='Offshore, existing', commodity='electricity', # Cost is already in the distance and component
                            hasCapacityVariable=True,
                            capacityMax=data['Offshore existing, capacityFix'],
                            operationRateMax=data['Offshore existing, operationRateMax'],
                            locationalEligibility=locationalEligibility,
                            investPerCapacity=cost_data["capex"], 
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM


def add_wind_existing(esM, data, cost_data, existing_fixed=False):
    # Add existing turbines
    # Commodity is electricity grid (has to be converted by grid)
    if existing_fixed:
        if any(data["Wind existing, capacity"] > 0):
            esM.add(fn.Source(esM=esM, name='Wind, existing', commodity='electricity_grid',
                            hasCapacityVariable=True,
                            capacityFix=data['Wind existing, capacity'],
                            operationRateMax=data['Wind existing, operationRate'],
                            investPerCapacity=cost_data["capex"], 
                            opexPerCapacity=cost_data["opex_fix"],  # Schöb
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    else:
        if any(data["Wind existing, capacity"] > 0):
            esM.add(fn.Source(esM=esM, name='Wind, existing', commodity='electricity_grid',
                            hasCapacityVariable=True,
                            capacityMax=data['Wind existing, capacity'],
                            operationRateMax=data['Wind existing, operationRate'],
                            investPerCapacity=cost_data["capex"], 
                            opexPerCapacity=cost_data["opex_fix"],  # Schöb
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM

def add_pv_potential(esM, data, cost_data, share=1.0):
    # Add rooftop pv potential
    # TODO: implement share (i.e.: reduce the worst flh groups)
    self_consumption = 0.4
    # Add conversion which splits the generated electricity_pv into el.
    # which has to be transmitted by grid and self consumption
    esM.add(fn.Conversion(esM=esM, name='pv_split',
                        physicalUnit=r'MW$_{el}$',
                        commodityConversionFactors={
                            'electricity_pv': -1,
                            'electricity_grid': 1-self_consumption,
                            'electricity_pv_sc': self_consumption
                        },
                        hasCapacityVariable=True))
    # Self-consumption is only a possibility. Therefore, two conversions are
    # implemented (1. Self-Consumption 2. grid)
    esM.add(fn.Conversion(esM=esM, name='pv_sc',
                        physicalUnit=r'MW$_{el}$',
                        commodityConversionFactors={
                            'electricity_pv_sc': -1,
                            'electricity_demand': 1,
                        },
                        hasCapacityVariable=True))
    esM.add(fn.Conversion(esM=esM, name='pv_grid',
                        physicalUnit=r'MW$_{el}$',
                        commodityConversionFactors={
                            'electricity_pv_sc': -1,
                            'electricity_grid': 1,
                        },
                        hasCapacityVariable=True))
    for group in data['PV potential, capacity'].keys():
        # Process numerical errors (smaller than 0 capacities)
        if (data['PV potential, capacity'][group]<0).any():
            warnings.warn(f"Smaller than 0 capacity in pv-{group} --> setting 0")
            print("Before: ", data['PV potential, capacity'][group], flush=True)
            data['PV potential, capacity'][group][data['PV potential, capacity'][group]<0] = 0
            print("After: ", data['PV potential, capacity'][group], flush=True)
    for group in data['PV potential, capacity'].keys():
        if not all(data['PV potential, capacity'][group] == 0):
            esM.add(fn.Source(esM=esM, name='PV, potential ' + group, commodity='electricity_pv',
                              hasCapacityVariable=True,
                              operationRateMax=data['PV potential, operationRateMax'][group],
                              capacityMin=pd.Series(index=data["PV potential, capacity"][group].index, data=0),
                              capacityMax=data['PV potential, capacity'][group]*share,
                            #   capacityFix=data['PV potential, capacity'][group]*self_consumption,
                              # investPerCapacity=1.5, opexPerCapacity=1.5*0.021, # Source Lopion
                              investPerCapacity=cost_data["capex"], 
                              opexPerCapacity=cost_data["opex_fix"],  # Source Schöb
                              opexPerOperation=cost_data["opex_var"],
                              interestRate=cost_data["wacc"], 
                              economicLifetime=cost_data["lifetime"],))
            
    return esM

def add_pv_existing(esM, data, cost_data, existing_fixed=False):
    # Add existing rooftop pv 
    if existing_fixed:
        for group in data['PV existing, capacity'].keys():
            if not all(data['PV existing, capacity'][group] == 0):
                esM.add(fn.Source(esM=esM, name='PV, existing ' + group, commodity='electricity_grid',
                                hasCapacityVariable=True, operationRateMax=data[
                        'PV existing, operationRateMax'][group],
                                capacityFix=data['PV existing, capacity'][group],
                                # investPerCapacity=1.5, opexPerCapacity=1.5*0.021, # Source Lopiob
                                investPerCapacity=cost_data["capex"], 
                                opexPerCapacity=cost_data["opex_fix"],  # Source Schöb
                                opexPerOperation=cost_data["opex_var"],
                                interestRate=cost_data["wacc"], 
                                economicLifetime=cost_data["lifetime"]))
    else:
        for group in data['PV existing, capacity'].keys():
            if not all(data['PV existing, capacity'][group] == 0):
                esM.add(fn.Source(esM=esM, name='PV, existing ' + group, commodity='electricity_grid',
                                hasCapacityVariable=True, operationRateMax=data[
                        'PV existing, operationRateMax'][group],
                                capacityMax=data['PV existing, capacity'][group],
                                # investPerCapacity=1.5, opexPerCapacity=1.5*0.021, # Source Lopiob
                                investPerCapacity=cost_data["capex"], 
                                opexPerCapacity=cost_data["opex_fix"],  # Source Schöb
                                opexPerOperation=cost_data["opex_var"],
                                interestRate=cost_data["wacc"], 
                                economicLifetime=cost_data["lifetime"]))
    return esM

def add_ofpv_potential(esM, data, cost_data, share_ofpv=1.0, share_ofpv_roads=1.0):
    # Add potential openfielpv for agriculture and at the sides of roads and railways
    # TODO: implement share (i.e.: reduce the worst flh groups)
    if (data.get("OFPV potential, capacity") is not None and not all(data.get("OFPV potential, capacity").values == 0) and
        data.get("OFPV Roads potential, capacity") is not None and not all(data.get("OFPV Roads potential, capacity").values == 0)):
        # Both available
        cap_ofpv = data['OFPV potential, capacity']*share_ofpv + data["OFPV Roads potential, capacity"]*share_ofpv_roads
        or_ofpv = pd.DataFrame(columns=data['OFPV potential, operationRateMax'].columns, index=data['OFPV potential, operationRateMax'].index)
        or_ofpv.loc[: ,cap_ofpv == 0] = 0
        or_ofpv.loc[: ,cap_ofpv != 0] = \
            (data['OFPV potential, operationRateMax'] *
            data['OFPV potential, capacity']*share_ofpv +
            data['OFPV Roads potential, operationRateMax']*
            data["OFPV Roads potential, capacity"]*share_ofpv_roads) / \
                (data['OFPV potential, capacity']*share_ofpv +
                 data["OFPV Roads potential, capacity"]*share_ofpv_roads)
        esM.add(fn.Source(esM=esM, name='OFPV, potential', commodity='electricity_grid',
                        hasCapacityVariable=True,
                        operationRateMax=or_ofpv, # Capacity based weight for OR
                        capacityMin=pd.Series(index=data["OFPV potential, capacity"].index, data=0),
                        capacityMax=cap_ofpv,
                        # investPerCapacity=0.9, opexPerCapacity=0.9 * 0.017,  # Source: Lopion
                            investPerCapacity=cost_data["capex"], 
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],  # Source Schöb
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"],))
                            # QPcostScale=0.3))
    elif data.get("OFPV potential, capacity") is not None and not all(data.get("OFPV potential, capacity").values == 0):
        # Only OFPV
        esM.add(fn.Source(esM=esM, name='OFPV, potential', commodity='electricity_grid',
                        hasCapacityVariable=True, operationRateMax=data['OFPV potential, operationRateMax'],
                        capacityMin=pd.Series(index=data["OFPV potential, capacity"].index, data=0),
                        capacityMax=data['OFPV potential, capacity']*share_ofpv,
                        # investPerCapacity=0.9, opexPerCapacity=0.9 * 0.017,  # Source: Lopion
                            investPerCapacity=cost_data["capex"], 
                            opexPerCapacity=cost_data["opex_fix"],  # Source Schöb
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"],))
                            # QPcostScale=0.3))
    elif data.get("OFPV Roads potential, capacity") is not None and not all(data.get("OFPV Roads potential, capacity").values == 0):
        # Only Roads
        esM.add(fn.Source(esM=esM, name='OFPV, potential', commodity='electricity_grid',
                        hasCapacityVariable=True, operationRateMax=data['OFPV Roads potential, operationRateMax'],
                        capacityMin=pd.Series(index=data["OFPV Roads potential, capacity"].index, data=0),
                        capacityMax=data["OFPV Roads potential, capacity"]*share_ofpv_roads,
                        # investPerCapacity=0.9, opexPerCapacity=0.9 * 0.017,  # Source: Lopion
                            investPerCapacity=cost_data["capex"], 
                            opexPerCapacity=cost_data["opex_fix"],  # Source Schöb
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"],))
                            # QPcostScale=0.3))
    else:
        # No OFPV:
        pass

    return esM

def add_ofpv_existing(esM, data, cost_data, existing_fixed=False):
    # Add existing openfield PV
    if existing_fixed:
        if data.get("OFPV existing, capacity") is not None and not all(data.get("OFPV existing, capacity").values == 0):
            esM.add(fn.Source(esM=esM, name='OFPV, existing', commodity='electricity_grid',
                            hasCapacityVariable=True, operationRateMax=data['OFPV existing, operationRateMax'],
                            capacityFix=data['OFPV existing, capacity'],
                            # investPerCapacity=0.9, opexPerCapacity=0.9 * 0.017,  # Source: Lopion
                                investPerCapacity=cost_data["capex"], 
                                opexPerCapacity=cost_data["opex_fix"],  # Source Schöb
                                opexPerOperation=cost_data["opex_var"],
                                interestRate=cost_data["wacc"], 
                                economicLifetime=cost_data["lifetime"]))
    else:
        if data.get("OFPV existing, capacity") is not None and not all(data.get("OFPV existing, capacity").values == 0):
            esM.add(fn.Source(esM=esM, name='OFPV, existing', commodity='electricity_grid',
                            hasCapacityVariable=True, operationRateMax=data['OFPV existing, operationRateMax'],
                            capacityMax=data['OFPV existing, capacity'],
                            # investPerCapacity=0.9, opexPerCapacity=0.9 * 0.017,  # Source: Lopion
                                investPerCapacity=cost_data["capex"], 
                                opexPerCapacity=cost_data["opex_fix"],  # Source Schöb
                                opexPerOperation=cost_data["opex_var"],
                                interestRate=cost_data["wacc"], 
                                economicLifetime=cost_data["lifetime"]))
    return esM

def add_battery(esM, data, cost_data_largeScale, cost_data_smallScale, locationalEligibility=None):
    # TODO add possibility to use limit
    # Comm. Electricity is used when charging, because it has to go through 
    # grid (i.e. So the commodity has to be converted from 
    # electricity grid to electricty). When discharging it has to go through
    # the grid again..
    esM.add(fn.Conversion(esM=esM,
                          locationalEligibility=locationalEligibility,
                          name='model_stability',
                          physicalUnit=r'MW$_{el}$',
                          commodityConversionFactors={'electricity': -1*stability_factor,
                                                      'electricity_bat': 1}))
    esM.add(fn.Conversion(esM=esM,
                          locationalEligibility=locationalEligibility,
                          name='model_stability_rev',
                          physicalUnit=r'MW$_{el}$',
                          commodityConversionFactors={'electricity_grid': stability_factor,
                                                      'electricity_bat': -1}))
    # Add Large scale Batteries
    esM.add(fn.Storage(esM=esM, name='Li-ion batteries',
                       locationalEligibility=locationalEligibility,
                       commodity='electricity_bat', hasCapacityVariable=True,
                       chargeEfficiency=0.99, cyclicLifetime=None,
                       dischargeEfficiency=0.99,
                       selfDischarge=1 - (1 - 0.03) ** (1 / (30 * 24)),  # From 1node example; Lopion: 0.004
                        # selfDischarge=0, # KSG45
                       chargeRate=1, dischargeRate=1,
                       doPreciseTsaModeling=False, 
                       # More expensive because the storage is in GWh (see above)
                       investPerCapacity=cost_data_largeScale["capex"] * stability_factor,
                       opexPerCapacity=cost_data_largeScale["opex_fix"] * stability_factor, 
                       interestRate=cost_data_largeScale["wacc"],
                       economicLifetime=cost_data_largeScale["lifetime"],
                       opexPerChargeOperation=charge_cost*stability_factor, # Small price so we dont get simultaneous charge and discharge
                       opexPerDischargeOperation=charge_cost*stability_factor
                       ))
    # TODO: cost data
    esM.add(fn.Conversion(esM=esM,
                        locationalEligibility=locationalEligibility,
                        name='model_stability_SS',
                        physicalUnit=r'MW$_{el}$',
                        commodityConversionFactors={'electricity_pv_sc': -1*stability_factor,
                                                    'electricity_bat_ss': 1}))
    esM.add(fn.Conversion(esM=esM,
                          locationalEligibility=locationalEligibility,
                          name='model_stability_rev_SS',
                          physicalUnit=r'MW$_{el}$',
                          commodityConversionFactors={'electricity_pv_sc': stability_factor,
                                                      'electricity_bat_ss': -1}))

    esM.add(fn.Storage(esM=esM, name='Li-ion batteries SS',
                        locationalEligibility=locationalEligibility,
                        commodity='electricity_bat_ss', hasCapacityVariable=True,
                        chargeEfficiency=0.99, cyclicLifetime=None,
                        dischargeEfficiency=0.99,
                           selfDischarge=1 - (1 - 0.03) ** (1 / (30 * 24)),  # From 1node example; Lopion: 0.004
                            # selfDischarge=0, # KSG45
                        chargeRate=1, dischargeRate=1,
                        doPreciseTsaModeling=False, 
                        investPerCapacity=cost_data_smallScale["capex"] * stability_factor,
                        opexPerCapacity=cost_data_smallScale["opex_fix"] * stability_factor, 
                        interestRate=cost_data_smallScale["wacc"],
                        economicLifetime=cost_data_smallScale["lifetime"],
                        opexPerChargeOperation=charge_cost*stability_factor, # Small price so we dont get simultaneous charge and discharge
                        opexPerDischargeOperation=charge_cost*stability_factor
                        ))
    return esM

# def add_hydro_existing():
    # TODO: Hydro
    # esM.add(fn.Source(esM=esM, name='Existing run-of-river plants',
    #                   commodity='electricity',
    #                   hasCapacityVariable=True,
    #                   operationRateFix=data[
    #                     'Existing run-of-river plants, operationRateFix'],
    #                   tsaWeight=0.01,
    #                   capacityFix=data[
    #                     'Existing run-of-river plants, capacityFix'],
    #                   investPerCapacity=1.3,
    #                   opexPerCapacity=1.3*0.04,
    #                   economicLifetime=40))

def add_electricity_purchase(esM, el_price, autarky=None, peak_grid=None, locationalEligibility=None):
    # Add Purchases: check if autarky is considered
    if autarky is None or autarky.get("degree") is None:
        if isinstance(el_price, pd.DataFrame):
            esM.add(fn.Source(esM=esM, name='Electricity purchase',
                            locationalEligibility=locationalEligibility,
                            commodity='electricity_grid', hasCapacityVariable=True,
                            capacityMax=peak_grid,
                            commodityCostTimeSeries=el_price))  # Really big el. price --> Driver to maximize autarky
        else:
            esM.add(fn.Source(esM=esM, name='Electricity purchase',
                locationalEligibility=locationalEligibility,
                commodity='electricity_grid', hasCapacityVariable=True,
                capacityMax=peak_grid,
                commodityCost=el_price))  # Really big el. price --> Driver to maximize autarky

    else:
        if el_price is None:
            esM.add(fn.Source(esM=esM, name='Electricity purchase',
                              locationalEligibility=locationalEligibility,
                              commodity='electricity_grid', hasCapacityVariable=True,
                              capacityMax=peak_grid,
                              balanceLimitID="el"))  # No el. price --> Autarky is driver
        else:
            if isinstance(el_price, pd.DataFrame):
                esM.add(fn.Source(esM=esM, name='Electricity purchase',
                                    locationalEligibility=locationalEligibility,
                                    commodity='electricity_grid', hasCapacityVariable=True,
                                    capacityMax=peak_grid,
                                    commodityCostTimeSeries=el_price,
                                    balanceLimitID="el"))
            else:
                esM.add(fn.Source(esM=esM, name='Electricity purchase',
                                  locationalEligibility=locationalEligibility,
                                    commodity='electricity_grid', hasCapacityVariable=True,
                                    capacityMax=peak_grid,
                                    commodityCost=el_price,
                                    balanceLimitID="el"))
            # esM.add(fn.Source(esM=esM, name='Electricity purchase negative',
            #                     commodity='electricity', hasCapacityVariable=True,
            #                     commodityRevenueTimeSeries=el_price["negative"],
            #                     balanceLimitID="el"))
    return esM

def add_fictional_purchase(esM, el_price, locationalEligibility=None):
    esM.add(fn.Source(esM=esM, name='Fictional electricity purchase',
            locationalEligibility=locationalEligibility,
            commodity='electricity', hasCapacityVariable=True,
            commodityCost=el_price))  # Really big el. price --> Driver to maximize autarky
    return esM

def add_electricity_sale(esM, el_price, autarky=None, peak_grid=None, locationalEligibility=None):
    # Add Purchases: check if autarky is considered
    if autarky is None or autarky.get("degree") is None:
        if isinstance(el_price, pd.DataFrame):
            esM.add(fn.Sink(esM=esM, name='Electricity sale',
                        locationalEligibility=locationalEligibility,
                        commodity='electricity', hasCapacityVariable=True,
                        capacityMax=peak_grid,
                        commodityRevenueTimeSeries=el_price-1e-8))  # Really big el. price --> Driver to maximize autarky
        else:
            esM.add(fn.Sink(esM=esM, name='Electricity sale',
                locationalEligibility=locationalEligibility,
                commodity='electricity', hasCapacityVariable=True,
                capacityMax=peak_grid,
                commodityRevenue=el_price-1e-8))  # Really big el. price --> Driver to maximize autarky

    else:
        if el_price is None:
            esM.add(fn.Sink(esM=esM, name='Electricity sale',
                              locationalEligibility=locationalEligibility,
                              commodity='electricity', hasCapacityVariable=True,
                              capacityMax=peak_grid,
                              balanceLimitID="el"))  # No el. price --> Autarky is driver
        else:
            if isinstance(el_price, pd.DataFrame):
                esM.add(fn.Sink(esM=esM, name='Electricity sale',
                    locationalEligibility=locationalEligibility,
                    commodity='electricity', hasCapacityVariable=True,
                    capacityMax=peak_grid,
                    commodityRevenueTimeSeries=el_price-1e-9,
                    balanceLimitID="el"))
            else:
                esM.add(fn.Sink(esM=esM, name='Electricity sale',
                                    locationalEligibility=locationalEligibility,
                                    commodity='electricity', hasCapacityVariable=True,
                                    capacityMax=peak_grid,
                                    commodityRevenue=el_price-1e-9,
                                    balanceLimitID="el"))
            # esM.add(fn.Sink(esM=esM, name='Electricity purchase negative',
            #                     commodity='electricity', hasCapacityVariable=False,
            #                     commodityRevenueTimeSeries=el_price["negative"],
            #                     balanceLimitID="el"))
    return esM

def add_electricity_demand(esM, data, efficiency_red, locationalEligibility=None):
    # Define Electricity demand conversion commodity (Work-around for pv self-consumption)
    esM.add(fn.Conversion(esM=esM,
                        name='Electricity Demand Conversion',
                        # locationalEligibility=locationalEligibility,
                        physicalUnit=r'MW$_{el}$',
                        commodityConversionFactors={'electricity': -1,
                                                    'electricity_demand': 1}))
    esM.add(fn.Sink(esM=esM, name='Electricity demand',
                    # locationalEligibility=locationalEligibility,
                    commodity='electricity_demand', hasCapacityVariable=False,
                    operationRateFix=data['Electricity demand, operationRateFix']*(1-efficiency_red)
                    ))
    return esM


def add_transmission_components(esM, locations, data=None, AC=False, DC=False, lower_grid=False, gas_grid=False,
                                fixed_cap_transmission=True, connect_all_lower_grid=False, lower_grid_h2=False,
                                allow_DC_expansion=False, fixed_distribution=False, centroid_grid_costs=False,
                                imports_exports=False):
    if data is not None and len(data) > 0:
        if AC:
            # Adding AC component real coupled grid
            args = {
                'esM': esM, 'name': "AC cables", 'hasCapacityVariable': True, 'commodity': "electricity",
                'distances': data['AC cables, distances'],
            }
            capacities = data['AC cables, capacityFix']
            if fixed_cap_transmission:
                args.update({"capacityFix": capacities, "reactances": data['AC cables, reactances']})
                esM.add(fn.LinearOptimalPowerFlow(**args))
            else:
                args.update({"capacityMax": capacities})
                esM.add(fn.Transmission(**args))

        if DC:
            # Add DC component real coupled grid
            args = {
                'esM': esM, 'name': "DC cables", 'hasCapacityVariable': True, 'commodity': "electricity",
                'distances': data['DC cables, distances'],
            }
            capacities = data["DC cables, capacityFix"]
            if fixed_cap_transmission:
                args.update({"capacityFix": capacities})
                esM.add(fn.Transmission(**args))
            else:
                args.update({"capacityMax": capacities})
                esM.add(fn.Transmission(**args))
            if allow_DC_expansion:
                args = {
                    'esM': esM, 'name': "DC cables (expansion)", 'hasCapacityVariable': True, 'commodity': "electricity",
                    'distances': data['DC cables, distances'], "losses": data["DC cables (expansion), losses"],
                    "locationalEligibility": data["DC cables (expansion), locationalEligibility"],
                    "investPerCapacity": data["DC cables (expansion), investPerCapacity"],
                }
                esM.add(fn.Transmission(**args))
        if lower_grid:
            args = {
                'esM': esM, 'hasCapacityVariable': True, 'commodity': "electricity", 'name': "Electricity Grid",
                'locationalEligibility': data["Lower Grid, locationalEligibility"],
            }
            if connect_all_lower_grid:
                # Centroids coupled grid
                if lower_grid_h2:
                    h2_args = deepcopy(args)
                    h2_args.update({
                        'name': "Hydrogen Grid", 'commodity': "hydrogen_grid",
                        'economicLifetime': 40, # FINE.Infrastructure
                        'distances': data["Lower Grid, distances"]})
                    # Hier capex einführen
                    if centroid_grid_costs:
                        h2_args.update({"opexPerOperation": data["Hydrogen Grid, opexPerOperation"]})
                        h2_args.update({"investPerCapacity": data["Hydrogen Grid, investPerCapacity"]})
                    if 'Hydrogen Grid, capacities' in data:
                        h2_args.update({"capacityFix": data['Hydrogen Grid, capacities']})
                    for idx in h2_args["locationalEligibility"].index:
                        if "NorthSea" in idx or "BalticSea" in idx:
                            h2_args["locationalEligibility"].loc[idx] = 0
                    for col in h2_args["locationalEligibility"].columns:
                        if "NorthSea" in col or "BalticSea" in col:
                            h2_args["locationalEligibility"][col] = 0
                    esM.add(fn.Transmission(**h2_args))

                el_args = deepcopy(args)
                for key in {'losses': data["Lower Grid, losses"], 'distances': data["Lower Grid, distances"], 'economicLifetime': 40}:
                    if data.get(f"Lower Grid, {key}") is not None:
                        el_args.update(
                            {key: data[f"Lower Grid, {key}"]}
                            )
                el_args.update({
                    "economicLifetime": 40
                        })
                if centroid_grid_costs:
                    el_args.update({'investPerCapacity': data["Lower Grid, investPerCapacity"]})
                if 'Electricity Grid, capacities' in data:
                    el_args.update({"capacityFix": data['Electricity Grid, capacities']})
                print(el_args)
                esM.add(fn.Transmission(**el_args))
            else:
                # Lower grid in the Real coupled grid
                low_args = args.copy()
                low_args.update({'name': "Distribution Grid", 'commodity': "electricity", 'distances': None})
                if fixed_distribution:
                    low_args.update({"capacityMax": data["Lower Grid, CapacityMax"]})
                esM.add(fn.Transmission(**low_args))

        if gas_grid:
            # Adding h2 grid in real coupled grid
            args = {
                'esM': esM, 'hasCapacityVariable': True, 'distances': data["H2 Grid, distances"],
                'capacityMin': data["H2 Grid, capacityMin"], 'name': "Hydrogen Grid", 'commodity': "hydrogen_grid",
                "opexPerOperation": data["H2 Grid, opexPerOperation"]}
            if fixed_cap_transmission:
                capacityMax = data["H2 Grid, capacityMax"]
                args.update({"capacityMax": capacityMax})
            esM.add(fn.Transmission(**args))

    return esM

def add_hydrogen_purchase(esM, cost, locationalEligibility):
    """
    Adds the imports for the energy cells that are not feasible in the Centroid grid
    :param esM:
    :param data:
    :return:
    """
    if locationalEligibility is not None:
        operationRateFix = pd.DataFrame(
                          index=range(0,8760),
                          columns=esM.locations,
                          data={location: 8760*[locationalEligibility[location]] for location in esM.locations})
    else:
        operationRateFix = pd.DataFrame(
                          index=range(0,8760),
                          columns=esM.locations,
                          data={location: 8760*[1] for location in esM.locations})
    print(f"Hydrogen cost {cost}")
    esM.add(fn.Source(esM=esM, name='hydrogen purchase',
                      commodity='hydrogen_grid',
                      hasCapacityVariable=True,
                      operationRateFix=operationRateFix,
                      commodityCost=cost,
                      locationalEligibility=locationalEligibility
                      ))
    return esM

def add_centroid_grid_purchase(esM, data):
    """
    Adds the imports for the energy cells that are not feasible in the Centroid grid
    :param esM:
    :param data:
    :return:
    """
    esM.add(fn.Source(esM=esM, name='Hydrogen purchase targeted cells',
                      commodity='hydrogen_grid',
                      hasCapacityVariable=True,
                      commodityCost=data["Energy cells purchase, hydrogenCost"],
                      locationalEligibility=data["Energy cells purchase, locationalEligibility"]
                      ))
    return esM


###########################################################################################################################################################
###############################                                 Heat Commodities and Demands                                ###############################
###########################################################################################################################################################

# Commodity for overall heat demand
def add_heat(esM):
    # Add heat commodities
    esM.commodities.update({'heat'})
    esM.commodityUnitsDict.update({'heat': r'MW$_{th}$'})
    return esM

# # Commodity for heat, that is produced locally
# def add_decentral_heat(esM):
#     esM.commodities.update({'decentral heat'})
#     esM.commodityUnitsDict.update({'decentral heat': r'MW$_{th}$'})

# Commodity for heat, that is delivered over the district heating network
def add_district_heating(esM):
    esM.commodities.update({'district_heating'})
    esM.commodityUnitsDict.update({'district_heating': r'MW$_{th}$'})
    return esM



def add_heat_demand(esM, data, renovation_red, locationalEligibility=None):
    esM.add(fn.Sink(esM=esM, name='Heat demand',
                #   locationalEligibility=locationalEligibility,
                  commodity='heat', hasCapacityVariable=False,
                  operationRateFix=data['Heat demand, operationRateFix']*(1-renovation_red)
                  ))
    return esM




# def add_heat_demand(esM, data, x_district_heating=None):
#     # Add heat demand, split in district heating and decentralized heating
#     if x_district_heating is None:
#         x_district_heating = data["District Heating Share"]

#     # if not np.isclose(x_district_heating, 0):
#     esM.commodities.update({'district_heating'})
#     esM.commodityUnitsDict.update({'district_heating': r'MW$_{th}$'})
#     esM.add(fn.Sink(esM=esM, name='District Heating demand',
#                     commodity='district_heating', hasCapacityVariable=False,
#                     operationRateFix=data['Heat demand, operationRateFix'] * x_district_heating))

#     esM.add(fn.Sink(esM=esM, name='Heat demand',
#                     commodity='heat', hasCapacityVariable=False,
#                     operationRateFix=data['Heat demand, operationRateFix']*(1-x_district_heating)))
#     #import ipdb;ipdb.set_trace()
#     return esM


# Add Process Heat Commodities 
def add_processHeat(esM):
    # Low Temperature Process Heat 
    esM.commodities.update({'processHeat_lowTemp'})
    esM.commodityUnitsDict.update({'processHeat_lowTemp': r'MW$_{th}$'})
    # Medium Temperature Process Heat
    esM.commodities.update({'processHeat_mediumTemp'})
    esM.commodityUnitsDict.update({'processHeat_mediumTemp': r'MW$_{th}$'})
    # High Temperature Process Heat
    esM.commodities.update({'processHeat_highTemp_combustion', 'processHeat_highTemp_EAF', 'processHeat_highTemp'})
    esM.commodityUnitsDict.update({'processHeat_highTemp_combustion': r'MW$_{th}$', "processHeat_highTemp_EAF": r'MW$_{th}$', 'processHeat_highTemp': r'MW$_{th}$'})
    return esM


# Add Process Heat Demands
def add_processHeat_demand(esM, data, efficiency_red, locationalEligibility=None):
    # Low Temperature Process Heat 
    esM.add(fn.Sink(esM=esM, 
                    name='Process Heat Demand Low Temperature',
                    # locationalEligibility=locationalEligibility,
                    commodity='processHeat_lowTemp', 
                    hasCapacityVariable=False,
                    operationRateFix=data['Process Heat demand low temperature, operationRateFix']*(1-efficiency_red)
                    ))
    # Medium Temperature Process Heat
    esM.add(fn.Sink(esM=esM, 
                    name='Process Heat Demand Medium Temperature',
                    # locationalEligibility=locationalEligibility,
                    commodity='processHeat_mediumTemp', 
                    hasCapacityVariable=False,
                    operationRateFix=data['Process Heat demand medium temperature, operationRateFix']*(1-efficiency_red)
                    ))
    # # High Temperature Process Heat (Non Electrifiable), Cement
    esM.add(fn.Sink(esM=esM, 
                    name='Process Heat Demand High Temperature Combustion',
                    # locationalEligibility=locationalEligibility,
                    commodity='processHeat_highTemp_combustion', 
                    hasCapacityVariable=False,
                    operationRateFix=data['Process Heat demand high temperature Cement, operationRateFix']*(1-efficiency_red)
                    ))
    # # High Temperature Process Heat (Non Electrifiable), and no biocoal EAF
    esM.add(fn.Sink(esM=esM, 
                    name='Process Heat Demand High Temperature EAF',
                    # locationalEligibility=locationalEligibility,
                    commodity='processHeat_highTemp_EAF', 
                    hasCapacityVariable=False,
                    operationRateFix=data['Process Heat demand high temperature EAF, operationRateFix']*(1-efficiency_red)
                    ))
    # # High Temperature Process Heat, 
    esM.add(fn.Sink(esM=esM, 
                    name='Process Heat Demand High Temperature',
                    # locationalEligibility=locationalEligibility,
                    commodity='processHeat_highTemp', 
                    hasCapacityVariable=False,
                    operationRateFix=data['Process Heat demand high temperature, operationRateFix']*(1-efficiency_red)
                    ))
    esM.add(fn.Conversion(esM=esM,
                name="Combustion to PHHT", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors={
                    'processHeat_highTemp': 1,
                    'processHeat_highTemp_combustion': -1
                },
                hasCapacityVariable=False, 
                )) 
    esM.add(fn.Conversion(esM=esM,
                name="EAF to Combustion", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors={
                    'processHeat_highTemp_combustion': 1,
                    'processHeat_highTemp_EAF': -1
                    
                },
                hasCapacityVariable=False, 
                )) 
    return esM

###########################################################################################################################################################
###############################                        District Heating Network Conversions                                 ###############################
###########################################################################################################################################################

def add_dh_network_existing(esM, data): 
    esM.add(fn.Conversion(esM=esM,
                name="DH Network existing", 
                physicalUnit= r'MW$_{th}$', #TODO -> Einheit muss mit Kosten passen...je nachdem was wir mit den Kosten machen, nochmal ändern! 
                commodityConversionFactors={
                    'heat': 1,
                    'district_heating': -1.13 #TODO + Verluste 
                }, 
                hasCapacityVariable=True, 
                capacityMax= 630, # 20% von "Ausbau ohne Kosten" (ca. 3160 MW)
                # Alternativ Capacity Fix? #TODO Add capacity of exiting DHN for each location 
                # OperationRateFix = 1 würde ja dafür sorgen, dass zu jedem Zeitpunkt das gesamte Netz voll ausgelastet werden muss, das is ja quatsch 
                # Eigentlich brauchen wir das gar nicht oder? Läuft alles über CapacityFix...
                # Wenns gar nicht anders geht, eventuell über noch eine "distric heating demand" conversion mit nem Faktor, wie vorher..
                # operationRateFix= 1, # Existing DHN has to be used!
                #investPerCapacity= 0, # Keine Kosten, weil Bestand.
                #opexPerCapacity= 0, #TODO Add costs...
                opexPerOperation= 0.02, #TODO Wahrscheinlich nicht benötigt. 
                interestRate= 0.06, #TODO 
                economicLifetime=25 #TODO Check for real value! 
                )) 
    return esM


def add_dh_network_new(esM, data, cost_factor):
    esM.add(fn.Conversion(esM=esM,
                name="DH Network new", 
                physicalUnit= r'MW$_{th}$',  
                commodityConversionFactors={
                    'heat': 1,
                    'district_heating': -1.13 # 13% losses - Source: AGFW – Hauptbericht 2020
                }, 
                hasCapacityVariable=True, 
                capacityMax = data['District Heating Network, capacity max'],
                opexPerCapacity= 0.002, # 2 €/KW Source: https://doi.org/10.1016/j.energy.2018.03.155 
                # opexPerOperation= data['District Heating Network, investment costs'] * 1e-6 * cost_factor, # €/MWh -> Mio. €/MWh  ## use cost_factor for scenarios
                opexPerOperation=0.0,
                investPerCapacity=data['District Heating Network, investment costs'] * 1e-6 * cost_factor * 2155, # AGFW oder 2155 Hauptbericht 2020
                interestRate= 0.06, 
                economicLifetime=40
                )) 
    return esM




###########################################################################################################################################################
###############################                          Conversions Process Heat                                           ###############################
###########################################################################################################################################################

def add_processHeat_LT_conversion(esM, locationalEligibility=None):
    ### Add Low Temperature Process Heat###
    # Low Temperature PH demand can be satisfied by disrict heating 
    # Just one conversion for tracking 
    esM.add(fn.Conversion(esM=esM, 
                name="Process Heat - Low Temperature", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'district_heating': -1,
                    'processHeat_lowTemp': 1
                },
                hasCapacityVariable=False
            ))
    return esM
# Industrial Heatpump is added for Low Temperature PH unter Heatpumps


### Medium Temperature Process Heat ###
def add_processHeat_MT_EBoiler(esM, eta, cost_data, locationalEligibility=None):
    # Industrial E-Boiler
    esM.add(fn.Conversion(esM=esM, 
                name="PH-MT Industrial E-Boiler", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'electricity': np.round(-1/eta, round_factor),
                    'processHeat_mediumTemp': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM

def add_processHeat_MT_bgHP(esM, eta, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, 
                name="PH-MT Biogas HP", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'biogas': np.round(-1/eta, round_factor),
                    'processHeat_mediumTemp': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM

def add_processHeat_MT_bmHP(esM, eta, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, 
                name="PH-MT Biomass HP", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'biomass': -1/eta,
                    'processHeat_mediumTemp': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM

def add_processHeat_MT_wasteHP(esM, eta, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, 
                name="PH-MT Waste HP", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'waste': np.round(-1/eta, round_factor),
                    'processHeat_mediumTemp': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM

### Add High Temperature Process Heat ###
def add_processHeat_HT_h2Furnace(esM, eta, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, 
                name="PH-HT Industrial Furnace (H2)", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'hydrogen': np.round(-1/eta, round_factor),
                    'processHeat_highTemp_EAF': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM

def add_processHeat_HT_bmFurnace(esM, eta, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, 
                name="PH-HT Industrial Furnace (Biocoal)", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'biocoal': np.round(-1/eta, round_factor),
                    'processHeat_highTemp_combustion': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM    

def add_processHeat_HT_bgFurnace(esM, eta, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, 
                name="PH-HT Industrial Furnace (Biogas)", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'biogas': np.round(-1/eta, round_factor),
                    'processHeat_highTemp_EAF': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM

def add_processHeat_HT_elFurnace(esM, eta, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, 
                name="PH-HT Industrial Furnace (Electrical)", 
                locationalEligibility=locationalEligibility,
                physicalUnit= r'MW$_{th}$',
                commodityConversionFactors= {
                    'electricity': np.round(-1/eta, round_factor),
                    'processHeat_highTemp': 1
                },
                hasCapacityVariable= True,
                investPerCapacity=cost_data['capex'], 
                opexPerCapacity=cost_data['opex_fix'],
                opexPerOperation=cost_data["opex_var"],
                interestRate=cost_data["wacc"], 
                economicLifetime=cost_data["lifetime"]
            ))
    return esM

###########################################################################################################################################################
###############################                                  Waste  Technologies                                        ###############################
###########################################################################################################################################################

# Add waste commodity
def add_waste(esM):
    if "waste" not in esM.commodities:
        esM.commodities.update({'waste'})
        esM.commodityUnitsDict.update({"waste": r'MWh$_{LHV}$'})
    return esM    

# Add waste source as purchase
def add_waste_purchase(esM):
    esM.add(fn.Source(esM=esM, name='Waste purchase', commodity='waste',
                      hasCapacityVariable=False,
                      #commodityCost=0,  #TODO add costs? 
                      balanceLimitID="waste"
                      )) 
    return esM

## Waste CHP
def add_waste_chp(esM, eta_el, eta_heat, data, cost_data, existing_only=True, existing_fixed=False, locationalEligibility=None):
    if "district_heating" in esM.commodities:
        if existing_fixed:
            esM.add(fn.Conversion(esM=esM, name='Waste CHP existing',
                                physicalUnit=r'MW$_{el}$',
                                # TODO Factor between waste electricity and heat
                                commodityConversionFactors={'electricity_grid': 1,
                                                            "district_heating": np.round(eta_heat / eta_el, round_factor),
                                                            'waste': np.round(-1 / eta_el, round_factor)},  # Lopion
                                hasCapacityVariable=True,
                                capacityFix=data['Waste CHP existing, capacityFix'],
                                investPerCapacity= cost_data['capex'],
                                opexPerCapacity= cost_data['opex_fix'],
                                opexPerOperation=cost_data["opex_var"],
                                interestRate=cost_data["wacc"], 
                                economicLifetime=cost_data["lifetime"]
                    ))
        else:
            esM.add(fn.Conversion(esM=esM, name='Waste CHP existing',
                                    physicalUnit=r'MW$_{el}$',
                                    # TODO Factor between waste electricity and heat
                                    commodityConversionFactors={'electricity_grid': 1,
                                                                "district_heating": np.round(eta_heat / eta_el, round_factor),
                                                                'waste': np.round(-1 / eta_el, round_factor)},  # Lopion
                                    hasCapacityVariable=True,
                                    capacityMax=data['Waste CHP existing, capacityFix'],
                                    investPerCapacity= cost_data['capex'],
                                    opexPerCapacity= cost_data['opex_fix'],
                                    opexPerOperation=cost_data["opex_var"],
                                    interestRate=cost_data["wacc"], 
                                    economicLifetime=cost_data["lifetime"]
                        ))
    if "district_heating" in esM.commodities and not existing_only:
        esM.add(fn.Conversion(esM=esM, name='Waste CHP',
                            physicalUnit=r'MW$_{el}$',
                            locationalEligibility=locationalEligibility,
                            # TODO Factor between waste electricity and heat
                            commodityConversionFactors={'electricity_grid': 1,
                                                        "district_heating": np.round(eta_heat / eta_el, round_factor),
                                                        'waste': np.round(-1 / eta_el, round_factor)},  # Lopion
                            hasCapacityVariable=True,
                            investPerCapacity= cost_data['capex'],
                            opexPerCapacity= cost_data['opex_fix'],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]
                ))
    return esM

# Waste Heat Plant
def add_waste_hop(esM, eta_heat, cost_data, locationalEligibility=None):
    if "district_heating" in esM.commodities:
        esM.add(fn.Conversion(esM=esM, name='Waste HOP',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{th}$',
                            # TODO Factor between waste electricity and heat
                            commodityConversionFactors={"district_heating": 1,
                                                        'waste': np.round(-1/eta_heat, round_factor)}, 
                            hasCapacityVariable=True,
                            investPerCapacity= cost_data['capex'],
                            opexPerCapacity= cost_data['opex_fix'],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]
                ))
    return esM

# Waste Power Plant
def add_waste_pp(esM, eta_el, cost_data):
    esM.add(fn.Conversion(esM=esM, name='Waste PP',
                        physicalUnit=r'MW$_{el}$',
                        # TODO Factor between waste electricity and heat
                        commodityConversionFactors={'electricity_grid': 1,
                                                    'waste': np.round(-1 / eta_el, round_factor)},  # Lopion
                        hasCapacityVariable=True,
                        investPerCapacity= cost_data['capex'],
                        opexPerCapacity= cost_data['opex_fix'],
                        opexPerOperation=cost_data["opex_var"],
                        interestRate=cost_data["wacc"], 
                        economicLifetime=cost_data["lifetime"]
            ))
    return esM    



###########################################################################################################################################################
###############################                                    Bio Technologies                                         ###############################
###########################################################################################################################################################

# Add biomass commodity 
def add_biomass(esM):   
    if "biomass" not in esM.commodities:
        esM.commodities.update({'biomass'})
        esM.commodityUnitsDict.update({'biomass': r'MWh$_{LHV}$'}) #Changed Unit to MWH(LHV) -> Lower heating value 
    return esM

def add_biomass_purchase(esM, fuel_price, biomass_limit):
    # Add biomass purchase as a source for biomass 
    if biomass_limit: 
        esM.add(fn.Source(esM=esM, name='Biomass purchase', commodity='biomass',
                        hasCapacityVariable=False,
                        commodityCost=fuel_price * 1e3* 1e-6, # €/kWh * 1000 kWh/MWh * 1e-6 Mio€/€ = [Mio€/MWh]
                        balanceLimitID="biomass", 
                        )) 
    else:
        esM.add(fn.Source(esM=esM, name='Biomass purchase', commodity='biomass',
                        hasCapacityVariable=False,
                        commodityCost=fuel_price * 1e3* 1e-6, # €/kWh * 1000 kWh/MWh * 1e-6 Mio€/€ = [Mio€/MWh]
                        )) 
    return esM

# Add biogas commodity 
def add_biogas(esM):   
    if "biogas" not in esM.commodities:
        esM.commodities.update({'biogas'})
        esM.commodityUnitsDict.update({'biogas': r'MWh$_{LHV}$'}) 
    return esM

def add_biogas_purchase(esM, fuel_price, biogas_limit):
    # Add biomass purchase as a source for biomass 
    if biogas_limit: 
        esM.add(fn.Source(esM=esM, name='Biogas purchase', commodity='biogas',
                        hasCapacityVariable=False,
                        commodityCost=fuel_price * 1e3* 1e-6, # €/kWh * 1000 kWh/MWh * 1e-6 Mio€/€ = [Mio€/MWh]
                        balanceLimitID="biogas", 
                        )) 
    else:
        esM.add(fn.Source(esM=esM, name='Biogas purchase', commodity='biogas',
                        hasCapacityVariable=False,
                        commodityCost=fuel_price * 1e3* 1e-6, # €/kWh * 1000 kWh/MWh * 1e-6 Mio€/€ = [Mio€/MWh]
                        )) 
    return esM 


def add_bg_pp(esM, eta_el, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, name='Biogas PP',
                          locationalEligibility=locationalEligibility,
                          physicalUnit=r'MW$_{el}$',
                          # TODO Factor between biomass electricity and heat
                          commodityConversionFactors={
                                                      'electricity_grid': 1,
                                                    #   'district_heating': np.round(eta_heat/eta_el,round_factor) ,
                                                      'biogas': np.round(-1/eta_el, round_factor)},  # Lopion
                          hasCapacityVariable=True,
                          investPerCapacity=cost_data['capex'], 
                          opexPerCapacity=cost_data['opex_fix'],
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"], 
                          economicLifetime=cost_data["lifetime"]
                          ))
    return esM

def add_bg_chp(esM, eta_el, eta_heat, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, name='Biogas CHP',
                          physicalUnit=r'MW$_{el}$',
                          locationalEligibility=locationalEligibility,
                          # TODO Factor between biomass electricity and heat
                          commodityConversionFactors={
                                                      'electricity_grid': 1,
                                                      'district_heating': np.round(eta_heat/eta_el,round_factor) ,
                                                      'biogas': np.round(-1/eta_el, round_factor)},  # Lopion
                          hasCapacityVariable=True,
                          investPerCapacity=cost_data['capex'], 
                          opexPerCapacity=cost_data['opex_fix'],
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"], 
                          economicLifetime=cost_data["lifetime"]
                          ))
    return esM


# Biocoal Commodity and Torrefaction
def add_biocoal(esM, eta_torrefaction, cost_data, locationalEligibility=None):
    if "biocoal" not in esM.commodities:
        esM.commodities.update({'biocoal'})
        esM.commodityUnitsDict.update({'biocoal': r'MWh$_{LHV}$'}) 
    esM.add(fn.Conversion(esM=esM, name='Biocoal Torrefaction',
                          locationalEligibility=locationalEligibility,
                          physicalUnit=r'MWh$_{LHV}$',
                          # TODO Factor between biomass electricity and heat
                          commodityConversionFactors={
                                                      'biocoal': 1,
                                                      'biomass': np.round(-1/eta_torrefaction, round_factor)
                          },
                          hasCapacityVariable=True,
                          investPerCapacity=cost_data['capex'], 
                          opexPerCapacity=cost_data['opex_fix'],
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"], 
                          economicLifetime=cost_data["lifetime"]
                        ))
    return esM



def add_bm_chp(esM, eta_el, eta_heat, cost_data, locationalEligibility=None):
    # DISCLAIMER: Currently hard coded for "Medium Wood Chips" 
    # TODO Change to get data from excel and implement an option to decide which technology is beeing used 

    # # CHP Properties 
    # # Annahme zu Kosten: Für alle Modi gleich, weil selbes Kraftwerk. TODO gglfs höhere Kosten ansetzen, da extraction mehr kostet als normal backpressure CHP
    # properties = {
    #     "type": technology,
    #     "fuel": technology_data.get("fuel"),
    #     "capacity_feed": technology_data.get("capacity_feed"), 
    #     "eta_chp_el": technology_data.get("eta_chp_el"), # <- Dansk "Electricity efficiency, net (%), name plate"
    #     "eta_chp_heat": technology_data.get("eta_chp_heat"), # <- Dansk "Heat efficiency, net (%), name plate"
    #     "pth_ratio": technology_data.get("pth_ratio"),
    # }

    #TODO: Ggfls zu einem Model wechseln in welchem ein extraction turbine plant als beispiel genommen wird und dann der Wirkungsgrad entsprechend 
    # der Wärmeauskopplung mittels des Cv und Cb Wertes berechnet werden 

    # # Calculate plant indicators
    # # Capacity El
    # if "capacity_el" not in properties:
    #     properties.update({"capacity_el": properties["capacity_feed"]*properties['eta_chp_el']})
    
    # # Capacity Heat
    # if "capacity_heat" not in properties:
    #     properties.update({"capacity_heat": properties["capacity_feed"]*properties['eta_chp_heat']})

    # # Power to Heat Ratio
    # if "pth_ratio" not in properties: 
    #     properties.update()


    
    # Add CHP Conversion for CHP in full cogeneration (CHP) mode 
    esM.add(fn.Conversion(esM, name='Biomass CHP', 
                            physicalUnit= r'MW$_{el}$',
                            locationalEligibility=locationalEligibility,
                            commodityConversionFactors= {
                                'electricity_grid': 1,
                                'district_heating': np.round(eta_heat / eta_el, round_factor), 
                                'biomass': np.round(-1 / eta_el, round_factor)    
                            },
                            hasCapacityVariable= True,
                            investPerCapacity= cost_data['capex'],
                            opexPerCapacity= cost_data['opex_fix'],
                            opexPerOperation=cost_data["opex_var"], 
                            interestRate= cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM

def add_bm_hop(esM, eta_heat, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM, name='Biomass Heat Plant', 
                            locationalEligibility=locationalEligibility,
                            physicalUnit= r'MW$_{th}$',
                            commodityConversionFactors= {
                                'district_heating': 1, 
                                'biomass': np.round(-1 / eta_heat, round_factor)    
                            },
                            hasCapacityVariable= True,
                            investPerCapacity= cost_data['capex'],
                            opexPerCapacity= cost_data['opex_fix'],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate= cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM


def add_bm_pp(esM, eta_el, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM, name='Biomass Power Plant', 
                            locationalEligibility=locationalEligibility,
                            physicalUnit= r'MW$_{el}$',
                            commodityConversionFactors= {
                                'electricity_grid': 1, 
                                'biomass': np.round(-1 / eta_el, round_factor)    
                            },
                            hasCapacityVariable= True,
                            investPerCapacity= cost_data['capex'],
                            opexPerCapacity= cost_data['opex_fix'], 
                            opexPerOperation=cost_data["opex_var"],
                            interestRate= cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))    
    return esM




###########################################################################################################################################################
###############################                                 Heatpumps and ORC                                           ###############################
###########################################################################################################################################################

def calc_cop(esM, t_hot=50, t_cold="t_ambient", efficiency=0.45, weather_path=None):
    # Calc cop for heat pumps based on weather data
    # Read weather year. TODO: maybe move to getData..
    data = pd.read_csv(weather_path,
            sep=r"\s+", skiprows=([i for i in range(0, 32)]), header=0)
    data = data.drop(index=0)
    if t_cold=="t_ambient":
        t_a = [t + 273.15 for t in data["t"].values]
    else:
        t_a = 365*24*[t_cold+273.15]
    t_h = 365*24*[t_hot+273.15]
    # daily_profile = 6 * [1.2] + 12 * [2] + 6 * [1.5]
    conv_fac = pd.DataFrame(columns=list(esM.locations))
    cop = []
    # cop = carnot*0.45 (@Kevin Knosala)
    for i, t in enumerate(t_a):
        cop.append(round(t_h[i]/(t_h[i]-t_a[i])*efficiency, 4))
    for loc in esM.locations:
        conv_fac[loc] = cop
    return conv_fac.round(4) #TODO!!!!!

def add_heatpump(esM, capacity, cost_data, weather_path=None, locationalEligibility=None):
    # Add heatpump with calculated cop
    conv_fac = calc_cop(esM, weather_path=weather_path)
    esM.add(fn.Conversion(esM=esM, name='heatpump',
                          locationalEligibility=locationalEligibility,
                          physicalUnit=r'MW$_{th}$',
                          commodityConversionFactors={
                            "electricity": -1/conv_fac,
                            "heat": 1
                          },
                          hasCapacityVariable=True,
                        #   capacityMax=capacity,
                          investPerCapacity=cost_data["capex"], 
                          opexPerCapacity=cost_data["opex_fix"], # Schöb
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"], 
                          economicLifetime=cost_data["lifetime"]))
    return esM


def add_heatpump_dh(esM, capacity, cost_data, weather_path=None, locationalEligibility=None):
    # Add large scale heatpump for district heating
    if "district_heating" in esM.commodities:
        conv_fac = calc_cop(esM, weather_path=weather_path)
        esM.add(fn.Conversion(esM=esM, name='heatpump dh',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{th}$',
                            commodityConversionFactors={
                                'electricity': -1/conv_fac,
                                "district_heating": 1
                            },
                            hasCapacityVariable=True,
                            investPerCapacity=cost_data["capex"],
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM

def add_geothermal_heatpump_dh(esM, cost_data, weather_path=None, locationalEligibility=None):
    # Add large scale geothermal heatpump for district heating
    if "district_heating" in esM.commodities:
        conv_fac = calc_cop(esM, t_cold=11, weather_path=weather_path)
        esM.add(fn.Conversion(esM=esM, name='geothermal heatpump dh',
                            physicalUnit=r'MW$_{th}$',
                            locationalEligibility=locationalEligibility,
                            commodityConversionFactors={
                                'electricity': -1/conv_fac,
                                'district_heating': 1
                            },
                            hasCapacityVariable=True,
                            #   capacityMax=capacity,
                            investPerCapacity=cost_data["capex"],
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM

def add_electro_vessel_dh(esM, eta_h,  cost_data, weather_path=None, locationalEligibility=None):
    # Add el. vessel for district heating
    if "district_heating" in esM.commodities:
        esM.add(fn.Conversion(esM=esM, name='electro vessel dh',
                            physicalUnit=r'MW$_{el}$',
                            locationalEligibility=locationalEligibility,
                            commodityConversionFactors={
                                'electricity': -1,
                                'district_heating': eta_h
                            },
                            hasCapacityVariable=True,
                            #   capacityMax=capacity,
                            investPerCapacity=cost_data["capex"],
                            opexPerCapacity=cost_data["opex_fix"], # Schöb
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM

def add_orc_for_chp(esM, capacity=None, interestRate=0.05, locationalEligibility=None):
    # Add orc process for district heating 
    esM.add(fn.Conversion(esM=esM, name='ORC',
                          physicalUnit=r'MW$_{el}$',
                          locationalEligibility=locationalEligibility,
                          commodityConversionFactors={
                              # 10% efficiency
                              'district_heating': -10,
                              'electricity': 1,
                          },
                          hasCapacityVariable=True,
                          capacityMax=capacity,
                          investPerCapacity=3.0, 
                          opexPerCapacity=3.0 * 0.007,
                          interestRate=interestRate, 
                          economicLifetime=25))
    return esM

def add_industrial_heatpump(esM, weather_path=None, locationalEligibility=None):
    ### Alternative for municipalities that have no district heating network ###
    # Values based on Air source heat pumps 3 MW from 
    # Danish Energy Agency and Energinet: Technology Data - Energy Plants for Electricity and District heating generation 
    conv_fac = calc_cop(esM, weather_path=weather_path)
    esM.add(fn.Conversion(esM=esM, name='Industrial Heatpump',
                          locationalEligibility=locationalEligibility,
                          physicalUnit=r'MW$_{th}$',
                          commodityConversionFactors={
                              'electricity': -1/conv_fac,
                              'processHeat_lowTemp': 1
                          },
                          hasCapacityVariable=True,
                          investPerCapacity=0.860, 
                          opexPerCapacity=0.025*0.860, # Same as Small Scale Heatpump
                          opexPerOperation=0,
                          interestRate=0.04, # Same as Small Scale Heatpump
                          economicLifetime=20))
    return esM

###########################################################################################################################################################
###############################                           Heat Storage (Large Scale and decentralized)                      ###############################
###########################################################################################################################################################

def add_heat_storage(esM, cost_data, capacityMax=None, locationalEligibility=None):
    # Add large scale heat storage for district heating
    # Paramters from Acatech per month https://www.acatech.de/wp-content/uploads/2018/03/ESYS_Technologiesteckbrief_Energiespeicher.pdf
    # new parameters from nestor
    if "district_heating" in esM.commodities:
        if 'heat_storage' not in esM.commodities:
            esM.commodityUnitsDict.update({'heat_storage': r'GW$_{th}$'})
            esM.commodities.update({'heat_storage'})
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_heat',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{th}$',
                            commodityConversionFactors={'district_heating': -1*stability_factor,
                                                        'heat_storage': 1}))
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_rev_heat',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{th}$',
                            commodityConversionFactors={'district_heating': stability_factor,
                                                        'heat_storage': -1}))
        esM.add(fn.Storage(
            esM=esM,
            name="Heat Storage",
            locationalEligibility=locationalEligibility,
            commodity="heat_storage",
            capacityMax=capacityMax,
            chargeEfficiency=0.99,
            cyclicLifetime=120000,
            dischargeEfficiency=0.99,
            # selfDischarge=1 - (1 - 0.5) ** (1 / (30 * 24)),  # 40-70%
            selfDischarge=0.00007, # Nestor
            chargeRate=1,
            dischargeRate=1,
            doPreciseTsaModeling=False,
            investPerCapacity=cost_data["capex"] * stability_factor,
            opexPerCapacity=cost_data["opex_fix"] * stability_factor,
            interestRate=cost_data["wacc"],
            opexPerChargeOperation=charge_cost*stability_factor, # Small price so we dont get simultaneous charge and discharge
            opexPerDischargeOperation=charge_cost*stability_factor,
        ))
    return esM


# TODO Get Data from Nestor excel instead of hard coded values 
def add_decentralized_heat_storage(esM, cost_data, locationalEligibility=None):
    if 'heat_storage_decentralized' not in esM.commodities:
        esM.commodityUnitsDict.update({'heat_storage_decentralized': r'GW$_{th}$'})
        esM.commodities.update({'heat_storage_decentralized'})
    esM.add(fn.Conversion(esM=esM,
                            name='model_stability_heat_decentralized',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{th}$',
                            commodityConversionFactors={'heat': -1*stability_factor,
                                                        'heat_storage_decentralized': 1}))
    esM.add(fn.Conversion(esM=esM,
                            name='model_stability_rev_heat_decentralized',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{th}$',
                            commodityConversionFactors={'heat': stability_factor,
                                                        'heat_storage_decentralized': -1}))
    esM.add(fn.Storage(
        esM = esM, 
        name="Decentralized Heat Storage", 
        commodity="heat_storage_decentralized", 
        locationalEligibility=locationalEligibility,
        chargeEfficiency=0.99, 
        cyclicLifetime=120000, #<- TEMP TODO Find correct value
        dischargeEfficiency=0.99,
        selfDischarge=0.0035,
        chargeRate=1, #<- TEMP TODO Find correct value
        dischargeRate=1, #<- TEMP TODO Find correct value
        doPreciseTsaModeling=False, #<- TEMP TODO Find correct value
        investPerCapacity=cost_data["capex"] * stability_factor,
        opexPerCapacity=cost_data["opex_fix"] * stability_factor,
        interestRate=cost_data["wacc"],
        opexPerChargeOperation=charge_cost*stability_factor,  #<- TEMP TODO Find correct value
        opexPerDischargeOperation=charge_cost*stability_factor,  #<- TEMP TODO Find correct value

    ))
    return esM

###########################################################################################################################################################
###############################                                 Hydrogen Technologies                                       ###############################
###########################################################################################################################################################

def add_hydrogen(esM):
    esM.commodities.update({'hydrogen', 'hydrogen_grid'})
    esM.commodityUnitsDict.update({'hydrogen': r'MW$_{_{2},LHV}$', 'hydrogen_grid': r'MW$_{_{2},LHV}$'})
    return esM

def add_hydrogen_grid(esM, cost_data, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, name='hydrogen_grid',
                        physicalUnit=r'MW$_{el}$',
                        locationalEligibility=locationalEligibility,
                        commodityConversionFactors={
                            'hydrogen_grid': -1,
                            'hydrogen': 1
                        },
                        hasCapacityVariable=True,
                        investPerCapacity=cost_data["capex"],
                        opexPerCapacity=cost_data["opex_fix"],
                        opexPerOperation=cost_data["opex_var"],
                        interestRate=cost_data["wacc"], 
                        economicLifetime=cost_data["lifetime"]))
    return esM

def add_hydrogen_demand_industry(esM, data, locationalEligibility=None):
    esM.add(fn.Sink(esM=esM, name="Hydrogen Demand Industry",
                    # locationalEligibility=locationalEligibility,
                    commodity='hydrogen', 
                    hasCapacityVariable=False,
                    operationRateFix=data['Hydrogen demand, operationRateFix']
            ))
    return esM

def add_electrolyzer(esM, eta_h2, cost_data, capacity=None, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, name='Electrolyzer',
                          physicalUnit=r'MW$_{el}$',
                          locationalEligibility=locationalEligibility,
                          commodityConversionFactors={
                              'hydrogen_grid': eta_h2,
                              #'hydrogen': 0.65,
                              'electricity': -1,
                          },
                          hasCapacityVariable=True,
                          capacityMax=capacity,
                          investPerCapacity=cost_data["capex"],
                          opexPerCapacity=cost_data["opex_fix"],
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"], 
                          economicLifetime=cost_data["lifetime"]))
    return esM


def add_hydrogenStorageUnderground(esM, cost_data, capacityMax=None, locationalEligibility=None):
    # TODO Add Potentials, Minimum soc
    # https://www.acatech.de/wp-content/uploads/2018/03/ESYS_Technologiesteckbrief_Energiespeicher.pdf
    if not 'hydrogen_storageUGS' in esM.commodityUnitsDict.keys():
        esM.commodityUnitsDict.update({'hydrogen_storageUGS': r'GW$_{_{2},LHV}$'})
        esM.commodities.update({'hydrogen_storageUGS'})
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_h2_ugs',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{_{2},LHV}$',
                            commodityConversionFactors={'hydrogen_grid': -1*stability_factor,
                                                        'hydrogen_storageUGS': 1}))
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_rev_h2_ugs',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{_{2},LHV}$',
                            commodityConversionFactors={'hydrogen_grid': stability_factor,
                                                        'hydrogen_storageUGS': -1}))
    esM.add(fn.Storage(esM=esM, name='Hydrogen Storage Under Ground',
                        commodity='hydrogen_storageUGS', hasCapacityVariable=True,
                        capacityMax=capacityMax,
                        locationalEligibility=locationalEligibility,
                        chargeEfficiency=1, cyclicLifetime=None,
                        dischargeEfficiency=0.998, # Modeled through electrolyzer and fuel cell, discharge=0.45
                        selfDischarge=0,
                        stateOfChargeMin=0,
                        chargeRate=1, dischargeRate=1, 
                        doPreciseTsaModeling=False, investPerCapacity=cost_data["capex"] * stability_factor,
                        opexPerCapacity=cost_data["opex_fix"] * stability_factor,
                        interestRate=cost_data["wacc"],
                        economicLifetime=cost_data["lifetime"],
                        opexPerChargeOperation=charge_cost*stability_factor, # Small price so we dont get simultaneous charge and discharge
                        opexPerDischargeOperation=charge_cost*stability_factor,
                        ))
    return esM

def add_hydrogenStorageUndergroundExisting(esM, cost_data, capacityMax=None, locationalEligibility=None):
    # TODO Add Potentials, Minimum soc
    # https://www.acatech.de/wp-content/uploads/2018/03/ESYS_Technologiesteckbrief_Energiespeicher.pdf
    if not 'hydrogen_storageUGS' in esM.commodityUnitsDict.keys():
        esM.commodityUnitsDict.update({'hydrogen_storageUGS': r'GW$_{_{2},LHV}$'})
        esM.commodities.update({'hydrogen_storageUGS'})
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_h2_ugs',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{_{2},LHV}$',
                            commodityConversionFactors={'hydrogen_grid': -1*stability_factor,
                                                        'hydrogen_storageUGS': 1}))
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_rev_h2_ugs',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{_{2},LHV}$',
                            commodityConversionFactors={'hydrogen_grid': stability_factor,
                                                        'hydrogen_storageUGS': -1}))
    esM.add(fn.Storage(esM=esM, name='Hydrogen Storage Under Ground existing',
                        commodity='hydrogen_storageUGS', hasCapacityVariable=True,
                        capacityMax=capacityMax,
                        locationalEligibility=locationalEligibility,
                        chargeEfficiency=1, cyclicLifetime=None,
                        dischargeEfficiency=0.998, # Modeled through electrolyzer and fuel cell, discharge=0.45
                        selfDischarge=0,
                        stateOfChargeMin=0,
                        chargeRate=1, dischargeRate=1, 
                        doPreciseTsaModeling=False, investPerCapacity=cost_data["capex"] * stability_factor,
                        opexPerCapacity=cost_data["opex_fix"] * stability_factor,
                        interestRate=cost_data["wacc"],
                        economicLifetime=cost_data["lifetime"],
                        opexPerChargeOperation=charge_cost*stability_factor, # Small price so we dont get simultaneous charge and discharge
                        opexPerDischargeOperation=charge_cost*stability_factor,
                        ))
    return esM

def add_hydrogenStorageAboveground(esM, cost_data, cost_factor, capacity=None, locationalEligibility=None):
    # Add hydrogen tanks above ground
    if not 'hydrogen_storage' in esM.commodityUnitsDict.keys():
        esM.commodityUnitsDict.update({'hydrogen_storage': r'GW$_{_{2},LHV}$'})
        esM.commodities.update({'hydrogen_storage'})
        # Add conversion to GW for stability reasons
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_h2',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{_{2},LHV}$',
                            commodityConversionFactors={'hydrogen_grid': -1*stability_factor,
                                                        'hydrogen_storage': 1}))
        esM.add(fn.Conversion(esM=esM,
                            name='model_stability_rev_h2',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{_{2},LHV}$',
                            commodityConversionFactors={'hydrogen_grid': stability_factor,
                                                        'hydrogen_storage': -1}))
    print(cost_data["capex"])
    esM.add(fn.Storage(esM=esM, name='Hydrogen Storage Above Ground',
                        commodity='hydrogen_storage', hasCapacityVariable=True,
                        locationalEligibility=locationalEligibility,
                        chargeEfficiency=1, cyclicLifetime=10000,
                        dischargeEfficiency=1, # Modeled through electrolyzer and fuel cell, discharge=0.45
                        selfDischarge=0,
                        stateOfChargeMin=0, # TODO
                        chargeRate=1, dischargeRate=1,
                        capacityMax=None,
                        doPreciseTsaModeling=False, 
                        # TODO CHANGE BACK TO cost_data["capex"] if you want to use high nestor prices of 18 €/kWh 
                        investPerCapacity=cost_data["capex"] * stability_factor, 
                        # Source for costs: 10.1016/j.apenergy.2018.09.217 (6.67-33.33)
                        opexPerCapacity=cost_data["opex_fix"] * stability_factor,
                        interestRate=cost_data["wacc"],
                        economicLifetime=cost_data["lifetime"],
                        opexPerChargeOperation=charge_cost*stability_factor, # Small price so we dont get simultaneous charge and discharge
                        opexPerDischargeOperation=charge_cost*stability_factor
                        ))
    return esM

def add_h2_boiler(esM, eta_heat, cost_data, capacity_max=None, locationalEligibility=None):
    # Add h2 boiler for decentralized heating
    # Parameters from nestor
    esM.add(fn.Conversion(esM=esM, name='H2 Condensing Boiler',
                          physicalUnit=r'MW$_{th}$',
                          locationalEligibility=locationalEligibility,
                          commodityConversionFactors={
                              'hydrogen': -1/eta_heat,
                              'heat': 1
                              #'heat': 0.98
                          },
                          hasCapacityVariable=True,
                          capacityMax=capacity_max,
                          investPerCapacity=cost_data["capex"],
                          opexPerCapacity=cost_data["opex_fix"],
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"],
                          economicLifetime=cost_data["lifetime"]))
    return esM

def add_h2_mini_chp(esM, eta_el, eta_heat, cost_data, capacity_max=None, locationalEligibility=None):
    # Add h2 mini chp for district heating
    if "district_heating" in esM.commodities:
        esM.add(fn.Conversion(esM=esM, name='H2 mini CHP',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{el}$',
                            commodityConversionFactors={
                                'hydrogen': np.round(-1/eta_el, round_factor),
                                'district_heating': np.round(eta_heat/eta_el, round_factor),
                                #'district_heating': 0.41,
                                'electricity_grid': 1
                                #'electricity_grid': 0.49
                            },
                            hasCapacityVariable=True,
                            capacityMax=capacity_max,
                            investPerCapacity=cost_data["capex"],
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"],
                            economicLifetime=cost_data["lifetime"]))
    return esM


def add_fuelCell_LS(esM, eta_el, eta_heat, cost_data, capacity=None, locationalEligibility=None):
    # Add fuel cell and chp fuel cell to model
    esM.add(fn.Conversion(esM=esM, name='Fuel Cell LS',
                          locationalEligibility=locationalEligibility,
                          physicalUnit=r'MW$_{el}$',
                          commodityConversionFactors={
                              'electricity_grid': 1,
                              #'electricity_grid': 0.65,
                              'hydrogen_grid': -1/0.65,
                          },
                          hasCapacityVariable=True,
                          capacityMax=capacity,
                          investPerCapacity=cost_data["capex"],
                          opexPerCapacity=cost_data["opex_fix"],
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"], 
                          economicLifetime=cost_data["lifetime"]))
    if "district_heating" in esM.commodities:
        esM.add(fn.Conversion(esM=esM, name='Fuel Cell CHP LS',
                            physicalUnit=r'MW$_{el}$',
                            locationalEligibility=locationalEligibility,
                            # Nestor efficiencies
                            commodityConversionFactors={
                                'electricity_grid': 1,
                                #'electricity_grid': 0.51, 
                                'district_heating': np.round(eta_heat/eta_el, round_factor),
                                #'district_heating': 0.44,
                                'hydrogen_grid': np.round(-1/eta_el,round_factor),
                            },
                            hasCapacityVariable=True,
                            capacityMax=capacity,
                            investPerCapacity=cost_data["capex"],
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))

    return esM


def add_fuelCell_SS(esM, eta_el, eta_heat, cost_data, capacity=None, locationalEligibility=None):
    esM.add(fn.Conversion(esM=esM, name='Fuel Cell CHP SS',
                            locationalEligibility=locationalEligibility,
                            physicalUnit=r'MW$_{el}$',
                            # Nestor efficiencies
                            commodityConversionFactors={
                                'electricity': 1,
                                # TODO Change to district_heating or leave as heat 
                                'heat': np.round(eta_heat/eta_el, round_factor),
                                'hydrogen': np.round(-1/eta_el, round_factor),
                            },
                            hasCapacityVariable=True,
                            capacityMax=capacity,
                            investPerCapacity=cost_data["capex"],
                            opexPerCapacity=cost_data["opex_fix"],
                            opexPerOperation=cost_data["opex_var"],
                            interestRate=cost_data["wacc"], 
                            economicLifetime=cost_data["lifetime"]))
    return esM

def add_h2Turbine_LS(esM, eta, eta_heat, cost_data, locationalEligibility):
    esM.add(fn.Conversion(esM=esM, name='H2 Turbine LS',
                        physicalUnit=r'MW$_{el}$',
                        commodityConversionFactors={
                            'electricity_grid': 1, 
                            'district_heating': np.round(eta_heat/eta, round_factor),
                            'hydrogen_grid': np.round(-1/eta, round_factor),
                        },
                        locationalEligibility=locationalEligibility,
                        hasCapacityVariable=True,
                        investPerCapacity=cost_data["capex"],
                        opexPerCapacity=cost_data["opex_fix"],
                        opexPerOperation=cost_data["opex_var"],
                        interestRate=cost_data["wacc"], 
                        economicLifetime=cost_data["lifetime"]))
    return esM
def add_h2Turbine(esM, eta_el, eta_heat, cost_data, capacity=None, locationalEligibility=None):
    # https://www.acatech.de/wp-content/uploads/2018/03/ESYS_Technologiesteckbrief_Energiespeicher.pdf

    esM.add(fn.Conversion(esM=esM, name='H2 Turbine LS',
                          locationalEligibility=locationalEligibility,
                          physicalUnit=r'MW$_{el}$',
                          commodityConversionFactors={
                              'electricity_grid': 1, 
                              'hydrogen_grid': np.round(-1/0.38, round_factor), # Dänische Daten 0.38 Mittelwert, 0.75M€/MW Mittelwert
                          },
                          hasCapacityVariable=True,
                          capacityMax=capacity,
                        #   investPerCapacity=cost_data["capex"],
                          investPerCapacity=0.68,
                        #   opexPerCapacity=cost_data["opex_fix"],
                          opexPerCapacity=0.68*0.02,
                          opexPerOperation=cost_data["opex_var"],
                          interestRate=cost_data["wacc"], 
                          economicLifetime=cost_data["lifetime"]))


    # if "district_heating" in esM.commodities:
    #     esM.add(fn.Conversion(esM=esM, name='H2 Turbine CHP',
    #                     physicalUnit=r'MW$_{el}$',
    #                     commodityConversionFactors={
    #                         'electricity_grid': 1,
    #                         'district_heating': np.round(eta_heat/eta_el,round_factor),
    #                         'hydrogen': np.round(-1/eta_el, round_factor),
    #                     },
    #                     hasCapacityVariable=True,
    #                     capacityMax=capacity,
    #                     investPerCapacity=cost_data["capex"],
    #                     opexPerCapacity=cost_data["opex_fix"],
    #                     opexPerOperation=cost_data["opex_var"],
    #                     interestRate=cost_data["wacc"], economicLifetime=cost_data["lifetime"]))

    return esM
