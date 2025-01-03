# MunicipalEnergyAlt

This is an extension of ETHOS.FineRegions with the option to perform a modeling to generate alternatives (MGA) optimization. This model provides alternative capacity and operation rate solutions, (optionally) using MGA. As the energy system model,ETHOS.Fine is used.

# Steps to follow to install fine with MGA optimization as a library

1. Clone the repository\
   \
   git clone https://github.com/lovinduw/MunicipalEnergyAlt

2. Create virtual environment with mamba\
   \
  cd municipalenergyalt\
  mamba env create -f requirements.yml                

3. Activate virtual environment\
   \
  mamba activate municipalenergyalt

4. Install EnergySysAlt library from GitHub with all the dependencies to perform modeling to perform alternatives (MGA) optimization\
   \
  pip install git+https://github.com/lovinduw/EnergySysAlt
