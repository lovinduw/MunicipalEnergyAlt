import os
import pandas as pd

mun_path = r"R:\data\s-risch\FINE.Regional\data\demand"
output_path = r"R:\MGA\regional\DemandData"
locations = []
for i in range(1, 17):
    if len(str(i)) < 2:
        locations.append("0" + str(i))
    else:   
        locations.append(str(i))

# folders = ([name for name in os.listdir(mun_path) if os.path.isdir(os.path.join(mun_path, name))])
folders = ["New folder"]
for folder in folders:
    data = {}

    folder_path = os.path.join(mun_path, folder)
    print(folder_path)
    output_folder_path = os.path.join(output_path, folder)    
    try:
        os.mkdir(output_folder_path)
    except Exception as e:
        print(f"An error occurred: {e}")

    files = ([name for name in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, name))])
    df = pd.read_csv(os.path.join(folder_path, files[0]), index_col=0)

    data = pd.DataFrame(0.0,index=df.index,columns=locations)

    for file in files:
        df = pd.read_csv(os.path.join(folder_path, file), index_col=0)
        location = df.columns[0]
        data[location[:2]] += df[location]

    data.to_csv(os.path.join(output_folder_path, folder[:-4] + ".csv"))
