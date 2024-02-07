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
 - name: Imperial College London , London , UK
   index : 2

date: 7 February 2024
bibliography: paper.bib

# Summary
The Biomass Energy Potential Mapping and Analysis Tool is an open-source software which aims to estimate the theoretical amount of energy that can be extracted from crop residues in a particular place (upto province) , in a particular year (till 2100) under various climate pathways, using different irrigation methods and climate models. We hope that this will help policymakers identify which crops to grow on currently unused land and how much energy they will be able to extract from it. It can also help them identify how much energy they will be able to extract from the existing cropland. This paper just presents a short summary of the methodology of the tool, for further details into how each function works, we suggest you go through with the attached jupyter notebook and the documentation of the tool.    

# Statement of Need 
Explain in short the need and the purpose of this tool

# Data and Sources
GAEZv4 and FAOSTAT

# Methodology
The tool first identifies the total available land which can be used for growing crops. This is done by first taking the whole area in the selected geography and then removing various land utilisation types (LUTs) from it which are unfit for growing crops, we further remove protected areas, tree covered regions and water bodies. After this we are left with the total available land. 

This land is further split into two components : cropland and marginal land. The cropland is the land where the crops are currently being grown and we have assumed that this area remains constant thorughout and the yield on this land keeps on varying with tie leading to different levels of crop production. Assuming the same crops grow on same chunks of land, we can obtain an estimate of the amount of energy that can be extracted from cropland. Next we remove this land from the total available land to find the remaining marginal land. On this marginal land, we iterate through all the crops possible and find out which one has the highest yield. Next we select this crop and this is multiplied by the area to get the net production.

After obtaining the production of crop from cropland and marginal land, we use three factors to identify the theoretical amount of energy we can extract from the selected region. The Residue-to-Product Ratio(RPR) , The Surplus Availability Factor(SAF) and The Lower Heating Value(LHV) are used to identify how much amount of residue is produced per kg of crop , then SAF tells us how much of this residue can be used for energy extraction purposes and finally LHV tells us the theoretical amount of energy we can obtain from a particular residue.

# Formulaes and Calculations
ADD THE RPR FORMULAE

# Features

# Figures 
<!-- Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}. -->

# Citations 
Via the paper.bib

# Acknowledgements 

# References 

