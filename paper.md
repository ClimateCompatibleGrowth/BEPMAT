title: 'Biomass Energy Potential Mapping and Analysis Tool (BEPMAT) using Python based libraries'
tags:
  - Python
  - biomass 
  - energy 
  - crop residues
  
authors:
  - name: Divyansh Singhal
    orcid: 0009-0003-2918-5125
    equal-contrib: true
    affiliation: "1"
  - name: Vignesh Sridharan
    orcid : 0009-0003-2918-5125
    equal-contrib: true 
    affiliation : "2"

affiliations:
 - name: Indian Institute of Technology , Delhi , India
   index: 1
 - name: Imperial College London , London , United Kingdom
   index : 2

date: 7 February 2024
bibliography: paper.bib

# Summary
The Biomass Energy Potential Mapping and Analysis Tool is an open-source software which aims to estimate the theoretical amount of energy that can be extracted from crop residues in a particular place (upto province) , in a particular year (till 2100) under various climate pathways, using different irrigation methods and climate models. We hope that this will help policymakers identify which crops to grow on currently unused land and how much energy they will be able to extract from it. It can also help them identify how much energy they will be able to extract from the existing cropland. This paper just presents a short summary of the methodology of the tool, for further details into how each function works, we suggest you go through with the attached jupyter notebook and the documentation of the tool.    

# Statement of Need 


# Data and Sources
All of the following data has been obtained from the GAEZv4 built my FAOSTAT and IIASA : Classification of land into 57 Agro-Economic Zones , Production values and Harvested Area for 2000 and 2010 , Exclusion Areas and Tree Cover Share , Potential Yield for future years under different RCPs, water conditions and using different models. 

The Pastureland dataset used is SEDAC pastureland 2000 dataset and the shapefiles (GADM boundaries) have been obtained using the python library gadm. The RPR, LHV and SAF data has been obtained from multiple papers and these sources are detailed in the documentation.

# Methodology
The tool first identifies the total available land which can be used for growing crops. This is done by first taking the whole area in the selected geography and then removing various land utilisation types (LUTs) from it which are unfit for growing crops, we further remove protected areas, tree covered regions and water bodies. After this we are left with the total available land. 

This land is further split into two components : cropland and marginal land. The cropland is the land where the crops are currently being grown and we have assumed that this area remains constant thorughout and the yield on this land keeps on varying with tie leading to different levels of crop production. Assuming the same crops grow on same chunks of land, we can obtain an estimate of the amount of energy that can be extracted from cropland. Next we remove this land from the total available land to find the remaining marginal land. On this marginal land, we iterate through all the crops possible and find out which one has the highest yield. Next we select this crop and this is multiplied by the area to get the net production.

After obtaining the production of crop from cropland and marginal land, we use three factors to identify the theoretical amount of energy we can extract from the selected region. The Residue-to-Product Ratio(RPR) , The Surplus Availability Factor(SAF) and The Lower Heating Value(LHV) are used to identify how much amount of residue is produced per kg of crop , then SAF tells us how much of this residue can be used for energy extraction purposes and finally LHV tells us the theoretical amount of energy we can obtain from a particular residue.

# Formulaes and Calculations

For a particular crop: \begin{equation}
\text{Theoretical Energy Potential} = \sum_{i} \text{Yield}_i \times \text{Area}_i \times \text{LHV}_i \times \text{SAF}_i \times \text{RPR}_i
\end{equation}
​
# Features
The tool offers a variety of features which can be explored and understood in much more detail using the jupyter notebooks and the attached documentation:
- The tool offers the ability to download all the data in the form of NetCDF4 files.
- The tool also outputs several interactive plotly graphs which can be used to compare the energy potentials at a glance.
- It provides the ability to get the potential for the future as well as the past. It also provides separate options if the potential is needed for the cropland or marginal land individually.
- The tool also allows for flexibility incase someone wants to change the RPR,LHV and SAF values to suit the region of their choice.
- Finally the Accessing_and_Visualising notebook shows how the data in the generated arrays can be visualised using bokeh plots.

# Figures 
Add figures for a sample country.

# Citations 
Via the paper.bib

# Acknowledgements 


