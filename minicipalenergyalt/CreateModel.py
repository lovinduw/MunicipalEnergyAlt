import os
import json
import pandas as pd
import numpy as np
import AddComponents as add_components
import GetData
import GetExperiment
def create_model(data, dict, experiment_name, db_path,dataOffshore=None, 
                 dataSaltCaverns=None, onshoreLocationalEligibility=None):
    
    """Creates model from dictionary

    Parameters
    ----------
    data : dict
        Dictionary with all relevant data to create model. Can be generated
        with getData.py
    dict : dict
        Dictionary with parameters for scenario definition

    Returns
    -------
    fine.EnergySystemModel
        esm instance for regarded scenario
    """

    def _interpolate(year, val1, val2, year1, year2):
        return round(val1 + (val2-val1) * (year - year1) / (year2 - year1), 4)
    def get_cost_data(sheet, technology, cost_factor, year=2020):
        """get cost data for certain technology

        Parameters
        ----------
        sheet : pd.DataFrame
            DataFrame with sheet from Nestor cost data 
        technology : str
            Technology name in excel
        year : int, optional
            year used for cost data options are [2020, 2030, 2040, 2050],
            by default 2020

        Returns
        -------
        Dictionary
            dict with capex, opex_fix, opex_var, lifetime and wacc
        """
        costs = sheet.loc[technology]

        def next_ten(x, base=10):
            return base * int(x/base)
        if "capex" + str(year)[-2:] not in costs.index:
            # Use linear interpolation to get the value based on the 10 years before and 10 years after values
            _year = int(str(year)[-2:])
            lower_year = next_ten(_year)
            higher_year = next_ten(_year) + 10
            capex = _interpolate(
                year=_year,
                val1=float(costs.loc["capex" + str(lower_year)] / 1e3),
                val2=float(costs.loc["capex" + str(higher_year)] / 1e3),
                year1=lower_year,
                year2=higher_year)
        else:
            capex = float(costs.loc["capex" + str(year)[-2:]] / 1e3)
        if cost_factor != 1:
            print(f"Cost Factor={cost_factor} for {technology}")
            print(f"capex before: {capex} Mio€/commodityUnit")
            capex *= cost_factor
            print(f"capex after: {capex} Mio€/commodityUnit")
        opex_fix = costs.loc["opex_fix"] * capex  # Per capacity in Mio. €
        opex_var = float(costs.loc["opex_var"] / 1e3) 
        lifetime = float(costs.loc["lifetime"])
        wacc = costs.loc["WACC"]
        if wacc == "None":
            wacc = general_cost_data.loc["WACC", "Value"]
        cost_data = {"capex": capex,
                    "opex_fix" : opex_fix,
                    "opex_var" : opex_var,
                    "lifetime": lifetime,
                    "wacc": wacc}
        # DEBUGGING
        # print(technology, cost_data, flush=True)
        return cost_data

    def get_efficiency_from_data(technology, output_hub, year=2050):
        """get cost data for certain technology

            Parameters
            ----------
            technology : str
                Technology name in excel sheet "Connectors"

            output_hub : str
                Name of the Output-Hub in NESTOR Database. Is used as a secondary
                identifier 

            year : int, optional
                year used for efficiency data options are [2020, 2030, 2040, 2050],
                by default 2050

            Returns
            -------
            Float
                efficiency for the combination of technology and identifier as number
            """
        efficiencies = efficiency_data_nestor.loc[[technology]]
        efficiencies = efficiencies.loc[efficiencies["output"] == output_hub]
        def next_ten(x, base=10):
            return base * int(x/base)
        if "efficiency" + str(year)[-2:] not in efficiencies.columns:
            _year = int(str(year)[-2:])
            lower_year = next_ten(_year)
            higher_year = next_ten(_year) + 10
            efficiency = _interpolate(
                year=_year,
                val1=float(efficiencies["efficiency"+ str(lower_year)].item()),
                val2=float(efficiencies["efficiency"+ str(higher_year)].item()),
                year1=lower_year,
                year2=higher_year)
        else:
            year_key = "efficiency"+ str(year)[-2:]
            efficiency = float(efficiencies[year_key].item())
        return efficiency

    if db_path == "CAESAR": 
        inputDataPath = r"/storage_cluster/internal/data/s-risch/FINE.Regional/data"

    else:   
        inputDataPath = os.path.join("R:/", "data", "s-risch", "FINE.Regional","data") # Contains demand data

    weather_path=os.path.join(inputDataPath, "weather",
                              "tsib_data_weatherdata_TRY2015_mittel_TRY2015_37935002691500_Jahr.dat")
    
    # Load cost data from Nestor
    general_cost_data = pd.read_excel(os.path.join(inputDataPath, "costs", "Energysystemdaten_GER2050_V33_sch_THGneutral_45.xlsx"), sheet_name="Optimization", index_col=0).fillna("None")
    sources_cost_data = pd.read_excel(os.path.join(inputDataPath, "costs", "Energysystemdaten_GER2050_V33_sch_THGneutral_45.xlsx"), sheet_name="Sources", index_col=0).fillna("None")
    conversion_cost_data = pd.read_excel(os.path.join(inputDataPath, "costs", "Energysystemdaten_GER2050_V33_sch_THGneutral_45.xlsx"), sheet_name="Transformers", index_col=0).fillna("None")
    heatpump_cost_data = pd.read_excel(os.path.join(inputDataPath, "costs", "Energysystemdaten_GER2050_V33_sch_THGneutral_45.xlsx"), sheet_name="HeatPumps", index_col=0).fillna("None")
    storages_cost_data = pd.read_excel(os.path.join(inputDataPath, "costs", "Energysystemdaten_GER2050_V33_sch_THGneutral_45.xlsx"), sheet_name="Storages", index_col=0).fillna("None")
    fuel_cost_data = pd.read_excel(os.path.join(inputDataPath, "costs", "Energysystemdaten_GER2050_V33_sch_THGneutral_45.xlsx"), sheet_name="Fuel Prices", index_col=0).fillna("None")

    # Load efficiencies from NESTOR
    efficiency_data_nestor = pd.read_excel(os.path.join(inputDataPath, "costs", "Energysystemdaten_GER2050_V33_sch_THGneutral_45.xlsx"), sheet_name="Connectors", index_col=0).fillna("None")    

    locations = set(data["locations"])
    # locations = data["locations"]
    if dict.get("waste").get("include") == 0:
        waste_included = False
    elif dict.get("waste").get("include") == 1:
        waste_included = True
    if dict.get("biomass").get("include") == 0:
        biomass_limit = False
    elif dict.get("biomass").get("include") == 1:
        biomass_limit = (dict.get("biomass").get("limit") == 1)
    if dict.get("biogas").get("include") == 0:
        biogas_limit = False
    elif dict.get("biogas").get("include") == 1:
        biogas_limit = (dict.get("biogas").get("limit") == 1)
    if dict.get("electricity").get("autarky").get("type") != "peak":
        additional_results_path = None # ToDO implement this
        esM = add_components.create_esm(data, locations=locations,
                                        autarky=dict.get("electricity").get("autarky").get("degree"),
                                        biomass_limit=biomass_limit, biogas_limit=biogas_limit,
                                        waste_included=waste_included, experiment_name=experiment_name, additional_results_path=additional_results_path)
    else:
        print("Autarky None")
        esM = add_components.create_esm(data, locations=locations, autarky=None, biomass_limit=biomass_limit, biogas_limit=biogas_limit)
    
    if dict.get("electricity").get("include") == 1:
        esM = add_components.add_electricity(esM)
        esM = add_components.add_electricity_demand(esM=esM, data=data, efficiency_red=dict.get("efficiency").get("fixed reduction"), locationalEligibility=onshoreLocationalEligibility)
        cost_data = get_cost_data(conversion_cost_data, "OnshoreGrid31", year=dict.get("year"), cost_factor=1)
        esM = add_components.add_grid(esM=esM, data=data, cost_data=cost_data, factor_grid_cost=dict.get("factor_grid_cost"), locationalEligibility=onshoreLocationalEligibility)               
        if dict.get("electricity").get("battery").get("include") != 0:
            if "cost factor" in dict.get("electricity").get("battery"):
                cost_data_largeScale = get_cost_data(storages_cost_data, "LS-BatteryStorage", year=dict.get("year"), cost_factor=dict.get("electricity").get("battery").get("cost factor"))
                cost_data_smallScale = get_cost_data(storages_cost_data, "SS-BatteryStorage", year=dict.get("year"), cost_factor=dict.get("electricity").get("battery").get("cost factor"))
            else:
                cost_data_largeScale = get_cost_data(storages_cost_data, "LS-BatteryStorage", year=dict.get("year"), cost_factor=1)
                cost_data_smallScale = get_cost_data(storages_cost_data, "SS-BatteryStorage", year=dict.get("year"), cost_factor=1)

            esM = add_components.add_battery(esM=esM, data=data, cost_data_largeScale=cost_data_largeScale, cost_data_smallScale=cost_data_smallScale, locationalEligibility=onshoreLocationalEligibility)

        # Self-Sufficiency Options:
        if dict.get("electricity").get("autarky").get("type")=="peak":
            peak_grid = dict.get("electricity").get("autarky").get("degree")
            if isinstance(peak_grid, str):
                if len(locations) > 1:
                    raise NotImplementedError("Only Implemented for single-node")
                with open(os.path.join("/storage_cluster/internal/home/s-risch/git/regioncasestudy/regioncasestudy/data/output/experiments/", peak_grid.split("_")[1], f"{peak_grid.split('_')[1]}_{list(locations)[0]}.json")) as f:
                    res_dict = json.load(f)
                peak_ref_experiment = max(res_dict["el. purchase peak"][list(locations)[0]], res_dict["el. sale peak"][list(locations)[0]])
                peak_grid = float(peak_grid.split("Share")[0]) * peak_ref_experiment
                print(f"peak grid {peak_grid}")
        else:
            peak_grid = None

        # function to get ts price:
        def get_price(price_input):
            if isinstance(price_input, str):
                if price_input in [file[:-4] for file in os.listdir(os.path.join(inputDataPath, "costs")) if file[-4:] == ".csv" and file[:11]=="ts_el_price"]:
                    _el_price = pd.read_csv(os.path.join(inputDataPath, "costs", f"{price_input}.csv"), index_col=0)
                    el_price = pd.DataFrame(range(0, 8760), columns=esM.locations)
                    for loc in el_price.columns:
                        el_price[loc] = _el_price[_el_price.columns[0]].divide(1e6).values
                else:
                    raise ValueError(f"String with value {dict.get('electricity').get('import').get('costs')} is not supported as input for el. import costs")
            else:
                el_price = dict.get("electricity").get("import").get("costs")*1e-6 # €/MWh --> 1e6 €/MWh
            return el_price

        if dict.get("electricity").get("autarky").get("type") is None:
            import_price = get_price(dict.get('electricity').get('import').get('costs'))
            if dict.get('electricity').get('export').get('costs') is not None:
                export_price = get_price(dict.get('electricity').get('export').get('costs'))
            else:
                export_price = import_price
            if dict.get("electricity").get("import").get("include") == 1:
                esM = add_components.add_electricity_purchase(esM=esM, el_price=import_price, autarky=None, peak_grid=None, locationalEligibility=onshoreLocationalEligibility)
            if dict.get("electricity").get("export").get("include") == 1:
                esM = add_components.add_electricity_sale(esM=esM, el_price=export_price, autarky=None, peak_grid=None, locationalEligibility=onshoreLocationalEligibility)
        else:
            if dict.get("electricity").get("autarky").get("type")=="net" or \
                dict.get("electricity").get("autarky").get("type")=="peak" or \
                    dict.get("electricity").get("autarky").get("degree") != 1:
                if dict.get("electricity").get("import").get("costs"):
                    # _el_price = pd.read_csv(r"data/costs/Gro_handelspreise_201901010000_201912312359.csv", sep=";")
                    # _el_price = _el_price["Deutschland/Luxemburg[€/MWh]"].apply(lambda x: x.replace(",", ".")).apply(lambda x: float(x))
                    # _el_price = pd.concat([_el_price[_el_price>=0], _el_price[_el_price<=0]], axis=1)
                    # _el_price.columns = ["positive", "negative"]
                    # # €/MWh --> 1e6 €/MWh
                    # _el_price = _el_price/1e6
                    # el_price = {"positive": pd.DataFrame(columns=locations, index=range(0,8760)),
                    #             "negative": pd.DataFrame(columns=locations, index=range(0,8760))}
                    # for loc in locations:
                    #     el_price["positive"][loc] = _el_price["positive"].fillna(0)
                    #     el_price["negative"][loc] = _el_price["negative"].multiply(-1).fillna(0)
                    el_price = get_price(dict.get('electricity').get('import').get('costs'))
                    
                else:
                    el_price = None
            # For 100% real self-sufficiency (island system) we don't need import
            if dict.get("electricity").get("autarky").get("type") == "real" and dict.get("electricity").get("autarky").get("degree") == 1:
                dict["electricity"]["import"]["include"] = 0
            if dict.get("electricity").get("autarky").get("type")=="peak":
                esM = add_components.add_electricity_purchase(esM=esM, el_price=el_price, autarky=None, peak_grid=peak_grid, locationalEligibility=onshoreLocationalEligibility)
            else:
                if dict.get("electricity").get("import").get("include") == 1:
                    esM = add_components.add_electricity_purchase(esM=esM, el_price=el_price, autarky=dict.get("electricity").get("autarky"), peak_grid=peak_grid, locationalEligibility=onshoreLocationalEligibility)

            if dict.get("electricity").get("autarky").get("type") == "net" or dict.get("electricity").get("autarky").get("type") == "peak":
                # if dict.get("electricity").get("import costs"):
                #     el_price = dict.get("electricity").get("import costs")*1e-6 # €/MWh --> 1e6 €/MWh
                # else:
                #     el_price = None
                if dict.get("electricity").get("autarky").get("type")=="peak":
                    esM = add_components.add_electricity_sale(esM=esM, el_price=el_price, autarky=None, peak_grid=peak_grid, locationalEligibility=onshoreLocationalEligibility)
                else:
                    esM = add_components.add_electricity_sale(esM=esM, el_price=el_price, autarky=dict.get("electricity").get("autarky"), peak_grid=peak_grid, locationalEligibility=onshoreLocationalEligibility)
            # Add expensive purchase so results are generated for infeasible net self sufficiency 
            if dict.get("electricity").get("autarky").get("type") == "net" or dict.get("electricity").get("autarky").get("type") == "peak":
                esM = add_components.add_fictional_purchase(esM=esM, el_price=100000*1e-6)
            if dict.get("electricity").get("Transmission") != 0:
                esM = add_components.add_transmission_components(esM, locations)

    if dict.get("heat").get("include") == 1:
        esM = add_components.add_heat(esM)
        esM = add_components.add_heat_demand(esM=esM, data=data, renovation_red=dict.get("renovation").get("fixed reduction"), locationalEligibility=onshoreLocationalEligibility)
        if dict.get("district heating").get("include") == 1:
            esM = add_components.add_district_heating(esM=esM)
            #esM = add_components.add_dh_network_existing(esM=esM, data=data)
            cost_factor = dict.get("district heating").get("cost factor")
            esM = add_components.add_dh_network_new(esM=esM, data=data, cost_factor=cost_factor)
        if dict.get("heat").get("ORC").get("include") != 0:
            # cost_data = get_cost_data(conversion_cost_data, ) # Own source
            esM = add_components.add_orc_for_chp(esM, capacity=dict.get("heat").get("orc"), locationalEligibility=onshoreLocationalEligibility)
        if dict.get("heat").get("Heatpump").get("include") != 0:
            cost_data = get_cost_data(heatpump_cost_data, "SS-Heatpump", year=dict.get("year"), cost_factor=dict.get("heat").get("Heatpump").get("cost factor"))
            esM = add_components.add_heatpump(esM, capacity=dict.get("heat").get("Heatpump").get("include"), cost_data=cost_data, 
                weather_path=weather_path, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("heat").get("Heatpump DH").get("include") != 0 and dict.get("district heating").get("include") == 1:
            cost_data = get_cost_data(heatpump_cost_data, "LS-Heatpump", year=dict.get("year"), cost_factor=dict.get("heat").get("Heatpump DH").get("cost factor"))
            esM = add_components.add_heatpump_dh(esM, capacity=dict.get("heat").get("Heatpump DH").get("include"), cost_data=cost_data,
                weather_path=weather_path, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("heat").get("Heatpump DH Geothermal").get("include") != 0 and dict.get("district heating").get("include") == 1:
            cost_data = get_cost_data(heatpump_cost_data, "LS-GeothermHeatpump", year=dict.get("year"), cost_factor=dict.get("heat").get("Heatpump DH Geothermal").get("cost factor"))
            esM = add_components.add_geothermal_heatpump_dh(esM, cost_data=cost_data,
                weather_path=weather_path, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("heat").get("Electro Vessel DH").get("include") != 0 and dict.get("district heating").get("include") == 1:
            cost_data = get_cost_data(conversion_cost_data, "ElectroVessel", year=dict.get("year"), cost_factor=dict.get("heat").get("Electro Vessel DH").get("cost factor"))
            esM = add_components.add_electro_vessel_dh(esM, eta_h=get_efficiency_from_data("ElectroVessel", "LHHub"), cost_data=cost_data,
                weather_path=weather_path, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("heat").get("Heat Storage LS").get("include") != 0:
            cost_data = get_cost_data(storages_cost_data, "LS-HeatStorage", year=dict.get("year"), cost_factor=dict.get("heat").get("Heat Storage LS").get("cost factor"))
            if onshoreLocationalEligibility is not None:
                heatStorageLocationalEligibility = onshoreLocationalEligibility.copy()
                for col in data['Heat demand, operationRateFix'].columns:
                    if data['Heat demand, operationRateFix'][col].sum() == 0:
                        heatStorageLocationalEligibility[col] = 0.0
                        print(col)
                        print("LocationalEligibility HeatStorage = 0")
            else:
                heatStorageLocationalEligibility = None
            esM = add_components.add_heat_storage(esM, cost_data=cost_data, locationalEligibility=heatStorageLocationalEligibility)
        if dict.get("heat").get("Decentral Heat Storage").get("include") != 0:
            cost_data = get_cost_data(storages_cost_data, "SS-HeatStorage", year=dict.get("year"), cost_factor=dict.get("heat").get("Decentral Heat Storage").get("cost factor"))
            esM = add_components.add_decentralized_heat_storage(esM, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)

    if dict.get("waste").get("include") == 1:
        esM = add_components.add_waste(esM=esM)
        esM = add_components.add_waste_purchase(esM=esM)
        if dict.get("waste").get("existing only") == 1:
            existing_only = True
            if dict.get("waste").get("Waste CHP").get("include") != 0 and dict.get("district heating").get("include") == 1:
                cost_data = get_cost_data(conversion_cost_data, "WasteCHP", year=dict.get("year"), cost_factor=dict.get("waste").get("Waste CHP").get("cost factor"))
                eta_el = get_efficiency_from_data("WasteCHP", "TransGrid-EHub", year=dict.get("year"))
                eta_heat = get_efficiency_from_data("WasteCHP", "DHHub", year=dict.get("year"))
                esM = add_components.add_waste_chp(esM, eta_el, eta_heat, data=data, cost_data=cost_data, existing_only=existing_only, locationalEligibility=onshoreLocationalEligibility)
        else:
            existing_only = False
            if dict.get("waste").get("Waste CHP").get("include") != 0 and dict.get("district heating").get("include") == 1:
                cost_data = get_cost_data(conversion_cost_data, "WasteCHP", year=dict.get("year"), cost_factor=dict.get("Waste CHP").get("cost factor"))
                eta_el = get_efficiency_from_data("WasteCHP", "TransGrid-EHub", year=dict.get("year"))
                eta_heat = get_efficiency_from_data("WasteCHP", "DHHub", year=dict.get("year"))
                esM = add_components.add_waste_chp(esM, eta_el, eta_heat, data=data, cost_data=cost_data, existing_only=existing_only, locationalEligibility=onshoreLocationalEligibility)
            if dict.get("Waste HOP").get("include") != 0 and dict.get("district heating").get("include") == 1:
                cost_data = get_cost_data(conversion_cost_data, "WasteHP", year=dict.get("year"), cost_factor=dict.get("Waste CHP").get("cost factor"))
                eta_heat = get_efficiency_from_data("WasteHP", "HTHHub", year=dict.get("year"))
                esM = add_components.add_waste_hop(esM, eta_heat, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
            if dict.get("Waste PP").get("include") != 0:
                cost_data = get_cost_data(conversion_cost_data, "WastePP", year=dict.get("year"), cost_factor=dict.get("Waste PP").get("cost factor"))
                eta_el = get_efficiency_from_data("WastePP", "TransGrid-EHub", year=dict.get("year"))
                esM = add_components.add_waste_pp(esM, eta_el, cost_data=cost_data)

    if dict.get("hydrogen").get("include") == 1:
        esM = add_components.add_hydrogen(esM)
        cost_data = get_cost_data(conversion_cost_data, "H2DistrGrid1", year=dict.get("year"), cost_factor=1)
        esM = add_components.add_hydrogen_grid(esM, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("hydrogen").get("import").get("include") != 0: 
            print(f"Hydrogen costs {dict.get('hydrogen').get('import').get('costs')*1e-6}")
            esM = add_components.add_hydrogen_purchase(esM, cost=dict.get("hydrogen").get("import").get("costs")*1e-6, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("hydrogen").get("Electrolyzer").get("include") != 0:
            cost_data = get_cost_data(conversion_cost_data, "LS-Electrolysis", year=dict.get("year"), cost_factor=dict.get("hydrogen").get("Electrolyzer").get("cost factor"))
            # Kai: Efficiencies do not change between SS-Electrolysis and LS-Electrolysis
            eta_h2 = get_efficiency_from_data("SS-Electrolysis", "HH-H2Hub", year=dict.get("year"))
            esM = add_components.add_electrolyzer(esM, eta_h2, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("hydrogen").get("Hydrogen Storage Above Ground").get("include") != 0:
            cost_data = get_cost_data(storages_cost_data, "SS-H2Storage", year=dict.get("year"), cost_factor=dict.get("hydrogen").get("Hydrogen Storage Above Ground").get("cost factor"))
            esM = add_components.add_hydrogenStorageAboveground(esM, cost_data=cost_data, cost_factor=cost_factor, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("hydrogen").get("Fuel Cell LS").get("include") != 0:
            cost_data = get_cost_data(conversion_cost_data, "LS-FuelCell", year=dict.get("year"), cost_factor=dict.get("hydrogen").get("Fuel Cell LS").get("cost factor"))
            eta_el = get_efficiency_from_data("LS-FuelCell", "DistrGrid-EHub", year=dict.get("year"))
            eta_heat = get_efficiency_from_data("LS-FuelCell", "LHHub", year=dict.get("year"))
            esM = add_components.add_fuelCell_LS(esM, eta_el, eta_heat, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
            
        if dict.get("hydrogen").get("Fuel Cell SS").get("include") != 0:
            cost_data = get_cost_data(conversion_cost_data, "SS-FuelCell", year=dict.get("year"), cost_factor=1)
            eta_el = get_efficiency_from_data("SS-FuelCell", "Demand-EHub", year=dict.get("year"))
            eta_heat = get_efficiency_from_data("SS-FuelCell", "DCHHub", year=dict.get("year"))
            esM = add_components.add_fuelCell_SS(esM, eta_el, eta_heat, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)

        if dict.get("hydrogen").get("H2 Turbine").get("include") != 0:
            cost_data = get_cost_data(conversion_cost_data, "H2GT", year=dict.get("year"), cost_factor=dict.get("hydrogen").get("H2 Turbine").get("cost factor"))
            eta_el = get_efficiency_from_data("H2GT", "TransGrid-EHub", year=dict.get("year"))
            eta_heat = get_efficiency_from_data("H2GT", "DHHub", year=dict.get("year"))
            esM = add_components.add_h2Turbine(esM, eta_el, eta_heat, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("hydrogen").get("H2 Boiler").get("include") != 0:
            cost_data = get_cost_data(conversion_cost_data, "H2CondensingBoiler", year=dict.get("year"), cost_factor=dict.get("hydrogen").get("H2 Boiler").get("cost factor"))
            eta_heat = get_efficiency_from_data("H2CondensingBoiler", "DCHHub", year=dict.get("year"))
            esM = add_components.add_h2_boiler(esM, eta_heat, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("hydrogen").get("H2 Mini CHP").get("include") != 0 and dict.get("district heating").get("include") == 1:
            cost_data = get_cost_data(conversion_cost_data, "H2MiniCHP", year=dict.get("year"), cost_factor=dict.get("hydrogen").get("H2 Mini CHP").get("cost factor"))
            eta_el = get_efficiency_from_data("H2MiniCHP", "DistrGrid-EHub", year=dict.get("year"))
            eta_heat = get_efficiency_from_data("H2MiniCHP", "LHHub", year=dict.get("year"))
            esM = add_components.add_h2_mini_chp(esM, eta_el, eta_heat, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
        if dataSaltCaverns is not None:
            cost_data_ugs = get_cost_data(storages_cost_data, "LS-H2StorageNewCaverns", year=dict.get("year"), cost_factor=1)
            esM = add_components.add_hydrogenStorageUnderground(esM, cost_data=cost_data_ugs, capacityMax=dataSaltCaverns["SaltCaverns planned, capacity"], locationalEligibility=dataSaltCaverns["locationalEligibility planned"])
            cost_data_ugs_ex = get_cost_data(storages_cost_data, "LS-H2Storage", year=dict.get("year"), cost_factor=1)
            esM = add_components.add_hydrogenStorageUndergroundExisting(esM, cost_data=cost_data_ugs_ex, capacityMax=dataSaltCaverns["SaltCaverns existing, capacity"], locationalEligibility=dataSaltCaverns["locationalEligibility existing"])
            cost_data = get_cost_data(conversion_cost_data, "H2GT", year=dict.get("year"), cost_factor=dict.get("hydrogen").get("H2 Turbine").get("cost factor"))
            eta_el = get_efficiency_from_data("H2GT", "TransGrid-EHub", year=dict.get("year"))
            eta_heat = get_efficiency_from_data("H2GT", "DHHub", year=dict.get("year"))
            h2gt_locations = dataSaltCaverns["locationalEligibility planned"] + dataSaltCaverns["locationalEligibility existing"]
            h2gt_locations[h2gt_locations > 1] = 1
            esM = add_components.add_h2Turbine_LS(esM, eta_el, eta_heat, cost_data=cost_data, locationalEligibility=h2gt_locations)

    if dict.get("biogas").get("include") == 1:
        esM = add_components.add_biogas(esM=esM)
        #TODO Replace with real value!
        fuel_price = 0.08 * dict.get("biogas").get("cost factor") # 8 ct/kWh -> 80€/MWh (https://biogas.fnr.de/daten-und-fakten/faustzahlen)
        #Kai: Preis im Verhältnis zu anderen Brennstoffkosten relativ hoch...
        esM = add_components.add_biogas_purchase(esM=esM, fuel_price=fuel_price, biogas_limit=biogas_limit)
        if dict.get("biogas").get("Biogas CHP").get("include") != 0 and dict.get("district heating").get("include") == 1:
            # Biogas chp from nestor is in original source power plant!
            cost_data = get_cost_data(conversion_cost_data, "BiogasCHP", year=dict.get("year"), cost_factor=dict.get("biogas").get("Biogas CHP").get("cost factor"))
            eta_el = get_efficiency_from_data("BiogasCHP", "DistrGrid-EHub", year=dict.get("year"))
            # Therefore, no correct cost data for biogas chp -> not included
            # eta_heat = get_efficiency_from_data("BiogasCHP", "LHHub", year=dict.get("year"))
            # esM = add_components.add_bg_chp(esM=esM, eta_el=eta_el, eta_heat=eta_heat, cost_data=cost_data)
            esM = add_components.add_bg_pp(esM=esM, eta_el=eta_el, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)
    
    if dict.get("biomass").get("include") == 1:
        esM = add_components.add_biomass(esM)
        # TODO Ret hink the fuel price implementation. Especially if different biomasses are added to the ESM
        # TODO If better implemented in this "centralized" way -> remove fuel prices from technologies below!
        # Get fuel price based on fuel of chosen technoloy from NESTOR DB
        # !!! Currently hard coded for WoodChip !!!
        fuel_price = fuel_cost_data.loc["WoodChip"].loc["Price50"] * dict.get("biomass").get("cost factor")
        esM = add_components.add_biomass_purchase(esM=esM, fuel_price=fuel_price, biomass_limit=biomass_limit)

        if dict.get("biomass").get("Biomass CHP").get("include") != 0 and dict.get("district heating").get("include") == 1:
            cost_data = get_cost_data(conversion_cost_data, "WoodCHP_MS", year=dict.get("year"), cost_factor=dict.get("biomass").get("Biomass CHP").get("cost factor"))
            eta_el = get_efficiency_from_data("WoodCHP_MS", "TransGrid-EHub", year=dict.get("year"))
            eta_heat = get_efficiency_from_data("WoodCHP_MS", "LHHub", year=dict.get("year"))
            esM = add_components.add_bm_chp(esM, eta_el=eta_el, eta_heat=eta_heat, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)

        if dict.get("biomass").get("Biomass HOP").get("include") != 0 and dict.get("district heating").get("include") == 1:
            cost_data = get_cost_data(conversion_cost_data, "WoodHP", year=dict.get("year"), cost_factor=dict.get("biomass").get("Biomass HOP").get("cost factor"))
            eta_heat = get_efficiency_from_data("WoodHP", "DHHub", year=dict.get("year"))
            esM = add_components.add_bm_hop(esM, eta_heat, cost_data=cost_data,locationalEligibility=onshoreLocationalEligibility)
        if dict.get("biomass").get("Biomass PP").get("include") != 0:
            cost_data = get_cost_data(conversion_cost_data, "WoodPP", year=dict.get("year"), cost_factor=dict.get("biomass").get("Biomass PP").get("include"))
            eta_el = get_efficiency_from_data("WoodPP", "TransGrid-EHub", year=dict.get("year"))
            esM = add_components.add_bm_pp(esM, eta_el, cost_data=cost_data, locationalEligibility=onshoreLocationalEligibility)

    #### Industry  ###    
    if dict.get("industry").get("include") == 1: 
        if dict.get("industry").get("Process Heat") != 0: 
            # Add Commodity
            esM = add_components.add_processHeat(esM)
            esM = add_components.add_processHeat_demand(esM, data=data, efficiency_red=dict.get("efficiency").get("fixed reduction"), locationalEligibility=onshoreLocationalEligibility)
            # Add Biocoal Commodity and Torrefaction
            cost_data_torrefaction = get_cost_data(conversion_cost_data, "WoodTorrefaction", year=dict.get("year"), cost_factor=1)
            eta_torrefaction = get_efficiency_from_data("WoodTorrefaction", "BioCoalHub", year=dict.get("year"))
            esM = add_components.add_biocoal(esM, eta_torrefaction=eta_torrefaction, cost_data=cost_data_torrefaction,locationalEligibility=onshoreLocationalEligibility)
            # Add PH-LT Conversion
            esM = add_components.add_processHeat_LT_conversion(esM,locationalEligibility=onshoreLocationalEligibility)
            esM = add_components.add_industrial_heatpump(esM, weather_path=weather_path,locationalEligibility=onshoreLocationalEligibility)
            # Add PH-MT Conversions
            # Industrial E-Boiler
            cost_data_eboiler = get_cost_data(conversion_cost_data, "LS-E-Boiler", year=dict.get("year"), cost_factor=1)
            eta_eboiler = get_efficiency_from_data("LS-E-Boiler", "HTHHub", year=dict.get("year"))
            esM = add_components.add_processHeat_MT_EBoiler(esM, eta=eta_eboiler, cost_data=cost_data_eboiler, locationalEligibility=onshoreLocationalEligibility)
            # Biogas HP
            cost_data_bghp = get_cost_data(conversion_cost_data, "GasHP", year=dict.get("year"), cost_factor=1)
            eta_bghp = get_efficiency_from_data("GasHP", "HTHHub", year=dict.get("year"))
            esM = add_components.add_processHeat_MT_bgHP(esM, eta=eta_bghp, cost_data=cost_data_bghp, locationalEligibility=onshoreLocationalEligibility)
            # Biomass HP -> asumption, biomass is mainly wood -> WoodHP
            cost_data_bmhp = get_cost_data(conversion_cost_data, "WoodHP", year=dict.get("year"), cost_factor=1)
            eta_bmhp = get_efficiency_from_data("WoodHP", "DHHub", year=dict.get("year"))
            esM = add_components.add_processHeat_MT_bmHP(esM, eta=eta_bmhp, cost_data=cost_data_bmhp, locationalEligibility=onshoreLocationalEligibility)
            # Waste HP
            cost_data_wastehp = get_cost_data(conversion_cost_data, "WasteHP", year=dict.get("year"), cost_factor=1)
            eta_wastehp = get_efficiency_from_data("WasteHP", "HTHHub", year=dict.get("year"))
            esM = add_components.add_processHeat_MT_wasteHP(esM, eta=eta_wastehp, cost_data=cost_data_wastehp, locationalEligibility=onshoreLocationalEligibility)
            # Add PH-HT Conversions
            # Industrial Furnace (Hydrogen)
            if dict.get("hydrogen").get("include") == 1:
                cost_data_furnaceH2 = get_cost_data(conversion_cost_data, "H2IndustrialFurnace", year=dict.get("year"), cost_factor=1)
                eta_furnaceH2 = get_efficiency_from_data("H2IndustrialFurnace", "PH3Hub", year=dict.get("year"))
                esM = add_components.add_processHeat_HT_h2Furnace(esM, eta=eta_furnaceH2, cost_data=cost_data_furnaceH2, locationalEligibility=onshoreLocationalEligibility)
            # Industrial Furnace (Biocoal)
            cost_data_furnaceCoal = get_cost_data(conversion_cost_data, "CoalIndustrialFurnace", year=dict.get("year"), cost_factor=1)
            eta_furnaceCoal = get_efficiency_from_data("CoalIndustrialFurnace", "PH3Hub", year=dict.get("year"))
            esM = add_components.add_processHeat_HT_bmFurnace(esM, eta=eta_furnaceCoal, cost_data=cost_data_furnaceCoal, locationalEligibility=onshoreLocationalEligibility)
            # Industrial Furnace (Biogas), 
            cost_data_furnaceGas = get_cost_data(conversion_cost_data, "GasIndustrialFurnace", year=dict.get("year"), cost_factor=1)
            eta_furnaceGas = get_efficiency_from_data("GasIndustrialFurnace", "PH3Hub", year=dict.get("year"))
            esM = add_components.add_processHeat_HT_bgFurnace(esM, eta=eta_furnaceGas, cost_data=cost_data_furnaceGas, locationalEligibility=onshoreLocationalEligibility)
            # Industrial Furnace (Electrical)
            cost_data_furnaceE = get_cost_data(conversion_cost_data, "E-IndustrialFurnace", year=dict.get("year"), cost_factor=1)
            eta_furnaceE = get_efficiency_from_data("E-IndustrialFurnace", "PH3Hub", year=dict.get("year"))
            esM = add_components.add_processHeat_HT_elFurnace(esM, eta=eta_furnaceE, cost_data=cost_data_furnaceE, locationalEligibility=onshoreLocationalEligibility)
        if dict.get("industry").get("Hydrogen Demand") != 0:
            if dict.get("hydrogen").get("include") == 1:
                esM = add_components.add_hydrogen_demand_industry(esM, data=data,locationalEligibility=onshoreLocationalEligibility)

    # Clustering should come next. Did not include it from Stanley's code.
    if dict.get("electricity").get("include") == 1:
        if dict.get("electricity").get("Wind, potential").get("include") != 0:
            # In percentage of potential
            cost_data = get_cost_data(sources_cost_data, "OnshoreEnergy-31", year=dict.get("year"), cost_factor=dict.get("electricity").get("Wind, potential").get("cost factor"))
            esM = add_components.add_wind_potential(esM=esM, data=data,
                                                    cost_data=cost_data,
                                                    share=dict.get("electricity").get("Wind, potential").get("include"))
        if dict.get("electricity").get("Wind, existing").get("include") != 0:
            cost_data = get_cost_data(sources_cost_data, "OnshoreEnergy-31", year=dict.get("year"), cost_factor=dict.get("electricity").get("Wind, existing").get("cost factor"))
            esM = add_components.add_wind_existing(esM=esM, data=data, cost_data=cost_data)
        if dataOffshore is not None:
            cost_data = get_cost_data(sources_cost_data, "OffshoreEnergy", year=dict.get("year"), cost_factor=1)
            esM = add_components.add_offshore_wind_potential(esM, dataOffshore, cost_data, dataOffshore["locationalEligibility"])
            esM = add_components.add_offshore_wind_existing(esM, dataOffshore, cost_data, dataOffshore["locationalEligibility"])
        if dict.get("electricity").get("PV, potential").get("include") != 0:
            cost_data = get_cost_data(sources_cost_data, "SolarEnergyRTPV", year=dict.get("year"), cost_factor=dict.get("electricity").get("PV, potential").get("cost factor"))
            # In percentage of potential
            esM = add_components.add_pv_potential(esM=esM, data=data,
                                                  cost_data=cost_data,
                                                  share=dict.get("electricity").get("PV, potential").get("include"))
        if dict.get("electricity").get("PV, existing").get("include") != 0:
            cost_data = get_cost_data(sources_cost_data, "SolarEnergyRTPV", year=dict.get("year"), cost_factor=dict.get("electricity").get("PV, existing").get("cost factor"))
            esM = add_components.add_pv_existing(esM=esM, data=data, cost_data=cost_data)
        if dict.get("electricity").get("OFPV, potential").get("include") != 0 or dict.get("electricity").get("OFPV Roads, potential") != 0:
            cost_data = get_cost_data(sources_cost_data, "SolarEnergyOFPV", year=dict.get("year"), cost_factor=dict.get("electricity").get("OFPV, potential").get("cost factor"))
            # In percentage of potential
            esM = add_components.add_ofpv_potential(esM=esM, data=data, cost_data=cost_data,
                                                    share_ofpv=dict.get("electricity").get("OFPV, potential").get("include"),
                                                    share_ofpv_roads=dict.get("electricity").get("OFPV Roads, potential").get("include"))
        if dict.get("electricity").get("OFPV, existing").get("include") != 0:
            cost_data = get_cost_data(sources_cost_data, "SolarEnergyOFPV", year=dict.get("year"), cost_factor=dict.get("electricity").get("OFPV, existing").get("cost factor"))
            esM = add_components.add_ofpv_existing(esM=esM, data=data, cost_data=cost_data)

    return esM

if __name__ == "__main__":
    db_path="Other"
    switch_industry = 1
    case_offshore = "Offshore_S1_Expansive_existing"
    pv_groups = 9
    experiment_name = "casestudy_test"

    # Get the required experiment
    experiments = GetExperiment.get_experiment(experiment_name,db_path)
    # experiments[experiment_name]["locations"] = ["053150000000"]
    # with open(os.join.path(os.path.dirname(os.path.abspath(__file__)), "Experiments", "all_mun_inclPH.json")) as f:
    #     experiments = json.load(f)
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
    print("getData successfull")
    print("Creating energy system model...")
    esM = create_model(data,experiments[experiment_name],experiment_name, db_path, dataOffshore=None)
    print("Eenergy system model created")