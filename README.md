# MunicipalEnergyAlt

This is an extension of ETHOS.FineRegions with the option to perform a modeling to generate alternatives (MGA) optimization. This model provides alternative capacity and operation rate solutions, (optionally) using MGA. As the energy system model,ETHOS.Fine is used.

# Steps to follow to install fine with MGA optimization as a library

1. Create virtual environment with mamba\
   \
  mamba create -n municipalenergyalt python=3.10                

2. Activate virtual environment\
   \
  mamba activate municipalenergyalt

3. Install fine library from GitHub with all the dependencies\
   \
  pip install git+https://github.com/lovinduw/EnergySysAlternatives#egg=fine

4. Install the municipalenergyalt library from GitHub with all the dependencies\
   \
  pip install git+https://github.com/lovinduw/MunicipalEnergyAlt#egg=municipalenergyalt
