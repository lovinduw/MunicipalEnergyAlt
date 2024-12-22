import os
import pandas as pd

input_path = r"R:\data\s-risch\db_TREP\biomass_test"
output_path = r"R:\MGA\regional\trep-db-Stanley\Biomass"

locations = []
for i in range(1, 17):
    if len(str(i)) < 2:
        locations.append("0" + str(i))
    else:   
        locations.append(str(i))

data = pd.DataFrame(0.0,index=locations, columns=["BiomassEnergy", "BiogasEnergy"])

# folders = ([name for name in os.listdir(input_path) if os.path.isdir(os.path.join(input_path, name))])
folders = ["Biomass_010010000000"]

for folder in folders:
    
    folder_path = os.path.join(input_path, folder)
    file_path = os.path.join(folder_path, folder + ".csv")
    print(folder_path)
    df = pd.read_csv(file_path)
    loc = folder.split("_")[1][:2]
    biomass = df.loc[df["Biomass/Biogas"] == "Biomass"]["MinEnergy"].sum()
    biogas = df.loc[df["Biomass/Biogas"] == "Biogas"]["MinEnergy"].sum()
    data.loc[loc, "BiomassEnergy"] += biomass
    data.loc[loc, "BiogasEnergy"] += biogas

data.to_csv(os.path.join(output_path, "Biomass.csv"))
