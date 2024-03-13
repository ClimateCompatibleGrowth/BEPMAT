#!/usr/bin/env python
# coding: utf-8

# # Biomass Energy Potential Mapping Tool 

# This notebook contains all the functions used in the project along with data used. We request you to kindly go through the paper first to get an idea of the objectives and the methodology.

# ## Loading all the CSVs containing the required raster files

# In[1]:


# Importing a few important libraries essential to the work.
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

# Importing the Geoprocessing libraries 
import rasterio
from rasterio.mask import mask
from rasterio.plot import show
from rasterio.crs import CRS
from rasterio.transform import from_origin
from rasterio.transform import Affine
from rasterio import transform
from rasterio.enums import Resampling
from rasterio.io import MemoryFile

import geopandas as gpd
from shapely.geometry import Point

# Importing required libraries for plotting interactive rasters 
from bokeh.plotting import figure
from bokeh.plotting import show as bokeh_show
from bokeh.models import LinearColorMapper, ColorBar, HoverTool, GeoJSONDataSource
import bokeh.palettes as bp
import bokeh.plotting as bpl
import matplotlib.patches as mpatches
import plotly
import plotly.graph_objects as go
import plotly.io as pio

# Importing required libraries to obtain shapefiles
import gadm
from gadm import GADMDownloader


# In[3]:


# Uploading all the CSVs into pandas DataFrmes

potential_yield = pd.read_csv("./dataset/potentialyield.csv")
harvested_area = pd.read_csv("./dataset/harvest_data_actual.csv") #The year is integer type
production_values= pd.read_csv("./dataset/productionvalues_actualyield.csv")
exclusion_areas= pd.read_csv("./dataset/Exclusionareas.csv")
tree_cover_share= pd.read_csv("./dataset/Treecover_share_GAEZ.csv")
aez_classification = pd.read_csv("./dataset/Classificationzones57.csv")


# The production_values defined here will be used for calculating crop residue from the year 2000 and 2010 
# under different conditions. The harvested area will be used for future residue from cropland calculations
# and the potential yield will be used for future residue from cropland as well as biomass potential from future
# marginal land. The remaining will be used to find the Total Available Land.


# ## Creating a shapefile generator which can generate the gadm shapefile for any region.

# In[4]:


def shapefile_generator(country, province=None):
    downloader = GADMDownloader(version="4.0")
    
    if province:
        # Download shapefile for a specific province
        ad_level = 1
        country_name = country
        gdf_country = downloader.get_shape_data_by_country_name(country_name=country_name, ad_level=ad_level)
        gdf_province = gdf_country[gdf_country["NAME_1"] == province]
        return gdf_province
    else:
        # Download shapefile for the entire country
        ad_level = 0
        gdf_country = downloader.get_shape_data_by_country_name(country_name=country, ad_level=ad_level)
        return gdf_country


# ## Notebook workflow: 
# 1. We start with the simplest calculations of the raw biomass energy we could have obtained from the harvests in the past using the 2000 and 2010 data (This is only applicable for cropland since this was the land that was actually harvested and we are keeping the marginal for maximizing the energy output in the future).
# 2. Next we will calculate the residue and the raw biomass energy potential from the cropland in the future 
# 3. Finally we will calculate the residue and the raw biomass energy potential from the marginal land in the future
# 
# We will keep defining the many helper functions along the way wherever they are required.

# ## I. Raw Biomass Energy Potential from Agricultural Residues using Actual Yields and Production (2000 and 2010) [GAEZv4 Theme: 5]

# ### Creating the dataset for calculating the biomass energy potential from the production values

#  To be able to calculate the Biomass potential we will need the crop Residue-to-Product Ratio, Surplus Availability Factor/
#  Availability Factor and Lower Heating Value. The following table summarizes these values for the crops we have from the 
#  actual yields and production data:
# 
# | Crop         | Residue Type  | RPR   | SAF   | LHV (MJ/kg) | Sources         |
# |--------------|---------------|-------|-------|-------------|-----------------|
# | Maize        | Stalk         | 2     | 0.8   | 16.3        | a, b, j         |
# |              | Cob           | 0.273 | 1     | 16.63       |                 |
# |              | Husk          | 0.2   | 1     | 15.56       |                 |
# | Rice         | Straw         | 1.757 | 0.684 | 8.83        | b, d, e         |
# |              | Husk          | 0.23  | 0.83  | 12.9        | c, e, f         |
# | Sorghum      | Straw         | 1.25  | 0.8   | 12.38       | a, b            |
# |              | Husk          | 1.4   | 1     | 13          | c, j            |
# | Millet       | Straw         | 1.4   | 1     | 13          | c, j            |
# |              | Stalk         | 1.75  | 0.8   | 15.51       | a, b, f         |
# | Wheat        | Straw         | 1.2   | 0.29  | 15.6        | b, j            |
# |              | Husk          | 0.23  | 0.29  | 12.9        | b, f            |
# | Cassava      | Stalk         | 0.062 | 0.407 | 16.99       | a, d, e         |
# |              | Peelings      | 3     | 0.2   | 10.61       | a, i            |
# | Cocoyam      | Peelings      | 0.2   | 0.8   | 10.61       | i, j            |
# | Sweet potato | Peelings      | 0.6   | 0.8   | 10.61       | b, j            |
# | Yam          | Peelings      | 0.2   | 0.8   | 10.61       | i, j            |
# | Potatoes     | Peelings      | 0.75  | 0.8   | 10.61       | i, j            |
# | Groundnuts   | Shells/husks  | 0.477 | 1     | 15.56       | a, i, c         |
# |              | Straw         | 2.3   | 1     | 17.58       | a               |
# | Palm oil     | Fiber         | 0.147 | 1     | 19.94       | a, i            |
# |              | Shells        | 0.049 | 1     | 21.1        | a, i            |
# |              | Fronds        | 2.604 | 1     | 7.97        | i               |
# |              | Empty bunches | 0.428 | 1     | 19.41       | a, i            |
# |              | Male bunches  | 0.233 | 1     | 14.86       | i, j            |
# | Beans(In Pulses)| Straw      | 2.5   | 1     | 12.38       | j               |
# | Soybean      | Straw         | 2.66  | 0.8   | 18          | b, f            |
# |              | Pods          | 1     | 0.8   | 18          | a, b, f         |
# | Banana       | leaves        | 0.35  | 1     | 11.37       | g               |
# |              | stem          | 5.6   | 1     | 11.66       | a, j            |
# |              | peels         | 0.25  | 1     | 17          | h, j            |
# | Plantain(With Bananas)| leaves| 0.35 | 0.8   | 12.12       | g, i            |
# |              | stem          | 3.91  | 0.8   | 10.9        | g, i            |
# |              | peels         | 0.25  | 1     | 12.56       | a, h            |
# | Sugar Cane   | baggase       | 0.25  | 1     | 6.43        | b, c            |
# |              | tops/leaves   | 0.32  | 0.8   | 15.8        | b, c            |
# | Coffee       | husk          | 1     | 1     | 12.8        | b, c            |
# | Cocoa        | pods/husks    | 1     | 1     | 15.48       | j               |
# | Cotton       | stalk         | 2.1   | 1     | 15.9        | c, i            |
# | Barley       | straw         | 0.75  | 0.15  | 17.5        | k               |
# |              | stalk         | 1.60  | 0.60  | 18.5        | k               |
# | Tobacco      | stalk         | 1.20  | 0.60  | 16.1        | k               |
# | Sunflower    | stalk         | 2.50  | 0.60  | 14.2        | k               |
# | Sugarbeet    | residue       | 0.66  | 0.09  | 20.85       | p,q             |
# | Rapeseed     | straw         | 1.58  | 0.23  | 14.55       | l               |    
# | Olives       | cake          | 0.40  | 0.90  | 19.7        | k               |
# | Lettuce      | waste         |1.2    | 0.50  | 12.8        | l               |
# | Tomatoes     | stem          |0.3    | 0.50  | 13.7        | l               |
# | Tomatoes     | leaves        |0.3    | 0.50  | 13.7        | l               |
# | Green peppers| residues      |0.45   | 0.50  | 12.0        | l               |
# | Red Peppers  | residues      |0.45   | 0.50  | 12.0        | l               |
# | Other Cereals| straw         | 1.2   | 0.40  | 16.845      | n,o             |
# | Rest of Crops| residue       | 0     | 0     | 0           | Not found       |
# | Fodder Crops | straw         | 0.4   | 0     | 0           | p               |   
# | Tur          | stalk         | 2.5   | 0.38  |18.58        | m               |
# | Lentils      | stalk         | 1.8   | 0.38  |14.65        | m               |
# | Gaur         | stalk         | 1.0   | 0.38  |16.02        | m               |
# | Gram         | stalk         | 1.1   | 0.38  |16.02        | m               |
# | Fruits and Nuts|pruning      | 0     | 0     |0            | Not found       |

# So for calculating the biomass potential of residues we have the production values data from GAEZ v4 for the years 2000 and 2010 which we will be using. The data in these rasters gives us the production of the particular crop in 1000 tonnes or 1 mln GK\\$. The other unit present in the data is mln GK\\$ which is used by FAO for crop groups like Fodder Crops, Pulses, Vegetables etc.
# 
# The documentation of the GAEZ v4 describes the yield as either tonnes/hectare or 1000 GK\\$/hectare. From this, we derive that 1 million GK\\$ = 1000 tonnes.
# 
# The following group contains the following crops according the GAEZ v4 Documentation:
# - Fodder Crops: All commodities in FAOSTAT primary crop production domain ranging from forage and silage, maize to vegetables and roots fodders.
# - Pulses: Bambara beans; beans, dry; broad beans, dry; chick peas; cow peas, dry;lentils; peas, dry; pigeon peas; pulses, other
# - Other cereals: Buckwheat; canary seed; fonio; mixed grain; oats; pop corn; quinoa; rye; triticale;
# - Yams and other roots: Taro; yautia; yams; roots and tubers;
# - Other crops: Includes all other crops from FAOSTAT production domain not covered by 25 crop groups above and excluding coir, vegetable tallow, oil of stillinga, oil of citronella, essential oils and rubber, natural.
# 
# 
# Assumptions made on the basis of GAEZ V4 documentation, from which we are using actual yield data:
# - Stimulants in the GAEZ v4 includes Cocoa Beans, Coffee, Green Tea, Tea. We have till now considered only Cocoa and Coffee.
# - In Yams and other roots, till now we have only included Yams and CocoYams(Taro)
# - In Vegetables we have taken Green and Red Peppers (Residues), Tomatoes (Stem and Leaves) and Lettuce (Waste) (We will take their mean value for RPR, SAF, and LHV since individual weightage in the crop yield is not available.)
# - In Pulses, we have taken Tur, Gaur, Gram, Beans and Lentils.(We will use their average based on same reason as above).
# - In Other Cereals, we have taken oats and rye.(We will use their average based on same reason as above).
# 
# 

# ## References for the above data:
# RPR and LHV values given were obtained from already published studies conducted in other countries, such as Ghana, Uganda, Zambia and China.
# 
# A source for most of these references was: https://www.aimspress.com/article/doi/10.3934/energy.2023002?viewType=HTML.
# The references are as follows:
# - a. Jekayinfa SO, Scholz V (2009) Potential availability of energetically usable crop residues in Nigeria. Energy Sources, Part A: Recovery, Util, Environ Effects 31: 687–697. https://doi.org/10.1080/15567030701750549 doi: 10.1080/15567030701750549.
# - b. Gabisa EW, Gheewala SH (2018) Potential of bio-energy production in Ethiopia based on available biomass residues. Biomass Bioenergy 111: 77–87. https://doi.org/10.1016/j.biombioe.2018.02.009 doi: 10.1016/j.biombioe.2018.02.009.
# - c. Okello C, Pindozzi S, Faugno S, et al. (2013) Bioenergy potential of agricultural and forest residues in Uganda. Biomass Bioenergy 56: 515–525. https://doi.org/10.1016/j.biombioe.2013.06.003 doi: 10.1016/j.biombioe.2013.06.003.
# - d. Koopmans A, Koppenjan J (1998) The Resource Base. Reg Consult Mod Appl Biomass Energy, 6–10.
# - e. San V, Ly D, Check NI (2013) Assessment of sustainable energy potential on non-plantation biomass resources in Sameakki Meanchey district in Kampong Chhnan pronice, Cambonia. Int J Environ Rural Dev 4: 173–178.
# - f. Yang J, Wang X, Ma H, et al. (2014) Potential usage, vertical value chain and challenge of biomass resource: Evidence from China's crop residues. Appl Energy 114: 717–723. https://doi.org/10.1016/j.apenergy.2013.10.019 doi: 10.1016/j.apenergy.2013.10.019.
# - g. Patiño FGB, Araque JA, Kafarov DV (2016) Assessment of the energy potential of agricultural residues in non-interconnected zones of Colombia: Case study of Chocó and Putumayo katherine Rodríguez cáceres. Chem Eng Trans 50: 349–354. https://doi.org/10.3303/CET1650059 doi: 10.3303/CET1650059.
# - h. Milbrandt A (2011) Assessment of biomass resources in Liberia. Liberia: Dev Resour, 117–166.
# - i.Kemausuor F, Kamp A, Thomsen ST, et al. (2014) Assessment of biomass residue availability and bioenergy yields in Ghana. Resou Conser Recycl 86: 28–37. https://doi.org/10.1016/j.resconrec.2014.01.007 doi: 10.1016/j.resconrec.2014.01.007.
# - j. Mboumboue E, Njomo D (2018) Biomass resources assessment and bioenergy generation for a clean and sustainable development in Cameroon. Biomass Bioenergy 118: 16–23. https://doi.org/10.1016/j.biombioe.2018.08.002 doi: 10.1016/j.biombioe.2018.08.002.
# - k. https://www.researchgate.net/publication/342000532_Agricultural_Residues_Potential_of_Hatay.
# - l. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9941997/.
# - m. https://www.saarcenergy.org/wp-content/uploads/2020/03/Final-Draft-SEC-report-on-crop-residue_14022020-1540-IM-1.pdf.
# - n. https://www.sciencedirect.com/science/article/pii/S0956053X10002436?via%3Dihub.
# - o. https://www.sciencedirect.com/science/article/pii/S0921344920305280.
# - p. https://www.diva-portal.org/smash/get/diva2:1208954/FULLTEXT01.pdf.
# - q.https://www.researchgate.net/publication/317490809_VALORIZATION_OF_SUGAR_BEET_PULP_RESIDUE_AS_A_SOLID_FUEL_VIA_TORREFACTION

# Now the final table sorted on the crop names which will be converted into a pandas dataframe for us to use will contain: 
# - All the vegetables combined into Vegetables row.
# - Coffee & Cocoa combined under stimulants row.
# - All the pulses as mentioned above will be grouped under pulses row.
# 
# <h2><center>Final Crop Table with RPR, SAF and LHV values</center></h2>
# 
# | Crop         | Residue Type  | RPR   | SAF   | LHV (MJ/kg) |
# |--------------|---------------|-------|-------|-------------|
# | Banana       | leaves        | 0.35  | 0.9   | 11.745      |
# | Banana       | peels         | 0.25  | 1     | 14.78       |
# | Banana       | stem          | 4.90  | 0.9   | 11.66       |
# | Barley       | stalk         | 1.60  | 0.60  | 18.5        |
# | Barley       | straw         | 0.75  | 0.15  | 17.5        |
# | Cassava      | Peelings      | 3     | 0.2   | 10.61       |
# | Cassava      | Stalk         | 0.062 | 0.407 | 16.99       |
# | Cotton       | stalk         | 2.1   | 1     | 15.9        |
# | Fodder Crops | straw         | 0.4   | 0     | 0           |
# |Fruits and nuts| pruning      | 0     | 0     | 0           |
# | Groundnut    | Shells/husks  | 0.477 | 1     | 15.56       |
# | Groundnut    | Straw         | 2.3   | 1     | 17.58       |
# | Maize        | Cob           | 0.273 | 1     | 16.63       |
# | Maize        | Husk          | 0.2   | 1     | 15.56       |
# | Maize        | Stalk         | 2     | 0.8   | 16.3        |
# | Millet       | Stalk         | 1.75  | 0.8   | 15.51       |
# | Millet       | Straw         | 1.4   | 1     | 13          |
# | Other Cereals| straw         | 1.2   | 0.40  | 16.845      |
# | Oil palm     | Empty bunches | 0.428 | 1     | 19.41       |
# | Oil palm     | Fiber         | 0.147 | 1     | 19.94       |
# | Oil palm     | Fronds        | 2.604 | 1     | 7.97        |
# | Oil palm     | Male bunches  | 0.233 | 1     | 14.86       |
# | Oil palm     | Shells        | 0.049 | 1     | 21.1        |
# | Olive        | Cake          | 0.40  | 0.9   | 19.7        |
# | Potato and Sweet Potato | Peelings | 0.675 |0.8  |10.61|
# | Pulses       | stalk         | 1.78  | 0.504 |15.53        |
# | Rapeseed     | straw         | 1.58  | 0.23  | 14.55       |
# | Wetland rice | Husk          | 0.23  | 0.83  | 12.9        |
# | Wetland rice | Straw         | 1.757 | 0.684 | 8.83        |
# | Sorghum      | Husk          | 1.4   | 1     | 13          |
# | Sorghum      | Straw         | 1.25  | 0.8   | 12.38       |
# | Soybean      | Pods          | 1     | 0.8   | 18          |
# | Soybean      | Straw         | 2.66  | 0.8   | 18          |
# | Stimulants   | husks         | 1     | 1     | 14.14       |
# | Sugar Cane   | baggase       | 0.25  | 1     | 6.43        |
# | Sugar Cane   | tops/leaves   | 0.32  | 0.8   | 15.8        |
# | Sugarbeet    | residue       | 0.66  | 0.09  | 20.85       |
# | Sunflower    | stalk         | 2.50  | 0.60  | 14.2        |
# | Tobacco      | stalk         | 1.20  | 0.60  | 16.1        |
# | Vegetables   | residue       | 0.675 | 0.50  | 12.625      |
# | Wheat        | Husk          | 0.23  | 0.29  | 12.9        |
# | Wheat        | Straw         | 1.2   | 0.29  | 15.6        |
# | Yam and others| Peelings     | 0.2   | 0.8   | 10.61       |
# | Rest of crops| Resdiue       | 0.0   | 0.0   | 0           |
# |
# 

# ### REMARK : Incase you have your own RPR , SAF and LHV values for your region, we request you to fork this repository and modify the values accordingly to obtain more region specific results.

# In[5]:


# Now importing the table in pandas format so that we can use it for geospatial analysis
# Defining the table data
data = [
    ['Banana', 'leaves', 0.35, 0.9, 11.745],
    ['Banana', 'peels', 0.25, 1, 14.78],
    ['Banana', 'stem', 4.90, 0.9, 11.66],
    ['Barley', 'stalk', 1.60, 0.60, 18.5],
    ['Barley', 'straw', 0.75, 0.15, 17.5],
    ['Cassava', 'Peelings', 3, 0.2, 10.61],
    ['Cassava', 'Stalk', 0.062, 0.407, 16.99],
    ['Cotton', 'stalk', 2.1, 1, 15.9],
    ['Fodder crops', 'straw', 0.4, 0, 0],
    ['Fruits and nuts', 'Pruning' , 0, 0, 0],
    ['Groundnut', 'Shells/husks', 0.477, 1, 15.56],
    ['Groundnut', 'Straw', 2.3, 1, 17.58],
    ['Maize', 'Cob', 0.273, 1, 16.63],
    ['Maize', 'Husk', 0.2, 1, 15.56],
    ['Maize', 'Stalk', 2, 0.8, 16.3],
    ['Millet', 'Stalk', 1.75, 0.8, 15.51],
    ['Millet', 'Straw', 1.4, 1, 13],
    ['Other cereals', 'straw', 1.2, 0.40, 16.845],
    ['Oil palm', 'Empty bunches', 0.428, 1, 19.41],
    ['Oil palm', 'Fiber', 0.147, 1, 19.94],
    ['Oil palm', 'Fronds', 2.604, 1, 7.97],
    ['Oil palm', 'Male bunches', 0.233, 1, 14.86],
    ['Oil palm', 'Shells', 0.049, 1, 21.1],
    ['Olive' , 'Cake', 0.4, 0.9, 19.7],
    ['Potato and Sweet Potato', 'Peelings', 0.675, 0.8, 10.61],
    ['Pulses', 'stalk', 1.78, 0.504, 15.53],
    ['Rapeseed', 'straw', 1.58, 0.23, 14.55],
    ['Wetland rice', 'Husk', 0.23, 0.83, 12.9],
    ['Wetland rice', 'Straw', 1.757, 0.684, 8.83],
    ['Sorghum', 'Husk', 1.4, 1, 13],
    ['Sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Soybean', 'Pods', 1, 0.8, 18],
    ['Soybean', 'Straw', 2.66, 0.8, 18],
    ['Stimulants', 'husks', 1, 1, 14.14],
    ['Sugarcane', 'baggase', 0.25, 1, 6.43],
    ['Sugarcane', 'tops/leaves', 0.32, 0.8, 15.8],
    ['Sugarbeet', 'residue', 0.66, 0.09, 20.85],
    ['Sunflower', 'stalk', 2.50, 0.60, 14.2],
    ['Tobacco', 'stalk', 1.20, 0.60, 16.1],
    ['Vegetables', 'residue', 0.675, 0.50, 12.625],
    ['Wheat', 'Husk', 0.23, 0.29, 12.9],
    ['Wheat', 'Straw', 1.2, 0.29, 15.6],
    ['Yams and other roots', 'Peelings', 0.2, 0.8, 10.61],
    ['Rest of crops', 'Residue' , 0, 0, 0]
]

# Defining the column names
columns = ['Crop', 'Residue Type', 'RPR', 'SAF', 'LHV (MJ/kg)']

# Create the DataFrame
residue_values = pd.DataFrame(data, columns=columns)


# ### Defining the function for calculating raw biomass energy potential in the past (2000 and 2010)
# It outputs an xarray containing all the crops and their corresponding biomass energy potential in each pixel and a final xarray called 'Combined' which gives the sum of all of these.

# In[6]:


# The band dimension comes up in a lot of places and is not needed for our calculations
def remove_band_dimension(array):
    if array.ndim == 3:
        return array[0]
    return array


# In[7]:


def get_lat_lon_from_transform(transform, shape):
    ny, nx = shape
    lons , lats = transform * np.mgrid[:nx, :ny]
    return lats, lons


# In[8]:


def biomass_potential_past(shapefile, time_period, water_supply):

    unique_crops_actual = production_values['Crop'].unique()

    filtered_production_values = production_values[(production_values['Time Period'] == time_period) &
                                               (production_values['Water Supply'] == water_supply)]
    required_production_values = filtered_production_values[['Crop', 'Download URL']]

    # For defining size of the array to be used 
    with rasterio.open(potential_yield.iloc[2, 14].strip()) as src:
        clipped_shapefile_init, transform_init = mask(src, shapefile.geometry, crop=True)
        clipped_shapefile_init = remove_band_dimension(clipped_shapefile_init)
        lats_init, lons_init = get_lat_lon_from_transform(transform_init, clipped_shapefile_init.shape)

    # Create xarray Dataset to store individual biomass potentials for each crop
    individual_biomass_potentials = {}

    # Variable to hold the net sum of all crops and their residues
    net_sum = 0.0

    # Initialize 'net_biomass_potential_array' before the loop
    net_biomass_potential_array = xr.DataArray(data=np.zeros_like(clipped_shapefile_init,  dtype='float32'),
                                               dims=('y', 'x'),
            coords={'y': range(clipped_shapefile_init.shape[0]), 'x': range(clipped_shapefile_init.shape[1]),
                                'latitude': (('x', 'y'), lats_init), 'longitude': (('x', 'y'), lons_init)},
                                               attrs={'units': 'PetaJoules',
                                                      'sum production': 0.0})  # Add initial sum as an attribute

    for crop in unique_crops_actual:
        required_url = required_production_values[required_production_values['Crop'] == crop]['Download URL'].values[0].strip()

        with rasterio.open(required_url) as src:
            crs_crop = src.crs
            clipped_shapefile, clipped_transform = mask(src, shapefile.geometry, crop=True)
            clipped_shapefile = remove_band_dimension(clipped_shapefile)
            sum_value_shapefile = np.nansum(clipped_shapefile)

        # Get the residues for the current crop
        residue_rows = residue_values.loc[residue_values['Crop'] == crop]

        # Calculate the sum of residues for the current crop
        crop_residue_sum = 0.0
        crop_residue_shapefile= np.zeros_like(clipped_shapefile)
        
        for _, residue_row in residue_rows.iterrows():
            LHV = residue_row['LHV (MJ/kg)']
            SAF = residue_row['SAF']
            RPR = residue_row['RPR']
            crop_residue_sum += sum_value_shapefile * LHV * SAF * RPR # Unit conversion for MJ to J and 
            # 1000 tonnes to kilograms ; Then multiplying by 10**-12 for PetaJoules
            crop_residue_shapefile += clipped_shapefile * LHV * SAF * RPR 

    # Calculate the net sum for all crops and their residues
        net_sum += crop_residue_sum

    # Create xarray DataArray to store individual biomass potential for the current crop
        crop_biomass_potential_array = xr.DataArray(data=crop_residue_shapefile,
                                                    dims=('y', 'x'),
            coords={'y': range(clipped_shapefile_init.shape[0]), 'x': range(clipped_shapefile_init.shape[1]),
                                'latitude': (('x', 'y'), lats_init), 'longitude': (('x', 'y'), lons_init)},
                                                    attrs={'units': 'PetaJoules',
                                                           'sum_production': crop_residue_sum})  # Add sum as an attribute

        # Sum the individual biomass potential with the net biomass potential
        net_biomass_potential_array += crop_biomass_potential_array

        # Store the individual biomass potential for the current crop in the dictionary
        individual_biomass_potentials[crop] = crop_biomass_potential_array

    # Create xarray Dataset to hold all the individual biomass potentials for each crop
    biomass_potentials_dataset = xr.Dataset(individual_biomass_potentials)

    # Add the net sum of all crops and their residues as an attribute to the Dataset
    biomass_potentials_dataset.attrs['Net Potential in PetaJ'] = net_sum

    # Add the net_biomass_potential_array as a new variable named 'combined' to the biomass_potentials_dataset
    biomass_potentials_dataset['Combined'] = net_biomass_potential_array
    
    biomass_potentials_dataset['Combined'].attrs['sum_production'] = net_sum

    return biomass_potentials_dataset


# #### Additional functions:
# The following functions are available if you just need the final numbers for the raw biomass energy potential for the region. It has two options either it can give you the net or it can give you the values for a specific crop as well.

# In[9]:


def get_actual_data_biomass_potential_all(shapefile, time_period, water_supply):
    
    value = biomass_potential_past(shapefile, time_period, water_supply)
    
    answer = value.attrs['net_sum']
    
    return answer

def get_actual_data_biomass_potential_crop(shapefile, time_period, water_supply, crop):
    
    value = biomass_potential_past(shapefile, time_period, water_supply)
    
    answer = value[crop].attrs['sum_production']
    
    return answer


# So the above functions and code finishes our task of getting the Raw Biomass Energy Potential from the Cropland in the past. Next we will see the functions for calculating the Raw Biomass Energy Potential from the Cropland in the future years.

# ## II. Raw Biomass Energy Potential from Agricultural Residues using Actual Yields and Production for Harvested Area and Agro-Climatic Potential Yield for future yields [GAEZv4 Theme: 5 and 3 respectively]

# Now since the future cropland data area data is not available to us we will be making an assumption. The assumption is that in the future the area under cropland which is required for us to ensure food security will remain the same as is was in the year 2010. So the harvest area data that we had from actual yields and production will serve as the cropland area for all future calculations. But since, with time the yield will vary and so will the residue from each crop. 
# 
# Assuming that RPR, SAF and LHV values also remain same for the crops in the future we will get the harvested area from the 2010 data for any shapefile and then multiply it with the future yield to get the future production. This will further be multiplied by RPR, SAF and LHV giving us raw biomass energy potential from cropland in the future. These values can then be compared with the past values calculated in part I to give us an idea as to how different future conditions affect the energy poential of the cropland. 

# In[10]:


def future_potential_cropland(time_period, climate_model, rcp, water_supply_future, input_level, shapefile_path, water_supply_2010):
    
    merged_df = pd.merge(harvested_area, potential_yield, on='Crop', how='inner')
    unique_crops = merged_df['Crop'].unique()
    
    filtered_harvested_area = harvested_area[(harvested_area['Time Period'] == 2010) &
                                             (harvested_area['Water Supply'] == water_supply_2010)]
    required_harvested_area = filtered_harvested_area[['Crop', 'Download URL']]

    filtered_potential_yield = potential_yield[(potential_yield['Time Period'] == time_period) &
                                               (potential_yield['Climate Model'] == climate_model) &
                                               (potential_yield['RCP'] == rcp) &
                                               (potential_yield['Water Supply'] == water_supply_future) &
                                               (potential_yield['Input Level'] == input_level)]
    required_potential_yields = filtered_potential_yield[['Crop', 'Download URL']]
    
    # For defining size of the xarray
    with rasterio.open(potential_yield.iloc[2, 14].strip()) as src:
        clipped_shapefile_init, transform_init = mask(src, shapefile_path.geometry, crop=True)
        clipped_shapefile_init = remove_band_dimension(clipped_shapefile_init)
        lats_init, lons_init = get_lat_lon_from_transform(transform_init, clipped_shapefile_init.shape)


    # Create xarray DataArray to store the net biomass potential for each pixel
    net_biomass_potential_array = xr.DataArray(data=0.0,
                                               dims=('y', 'x'),
            coords={'y': range(clipped_shapefile_init.shape[0]), 'x': range(clipped_shapefile_init.shape[1]),
                                'latitude': (('x', 'y'), lats_init), 'longitude': (('x', 'y'), lons_init)},
                                               attrs={'units': 'PetaJoules'})
    

    # Create xarray Dataset to store individual biomass potentials for each crop
    individual_biomass_potentials = {}

    # Variable to store the net sum of sum products
    net_sum = 0.0
    net_multiple = 0

    for crop in unique_crops:
        harvested_raster_url = required_harvested_area[required_harvested_area['Crop'] == crop]['Download URL'].values[0].strip()
        potential_yield_raster_url = required_potential_yields[required_potential_yields['Crop'] == crop]['Download URL'].values[0].strip()

        with rasterio.open(harvested_raster_url) as src:
            clipped, _ = mask(src, shapefile_path.geometry, crop=True)

        with rasterio.open(potential_yield_raster_url.strip()) as src:
            clipped_2, _ = mask(src, shapefile_path.geometry, crop=True)
        
        clipped_1 = np.nan_to_num(clipped)
        clipped_3 = np.nan_to_num(clipped_2)
        
         # Remove the 'bands' dimension if it exists (since it's not needed)
        clipped_1 = remove_band_dimension(clipped_1)
        clipped_3 = remove_band_dimension(clipped_3)

        product = np.multiply(clipped_1, clipped_3)
        sum_product = np.nansum(product)

        # Extract RPR, SAF, and LHV values for the crop
        residue_rows = residue_values[residue_values['Crop'] == crop]
        temp_sum = 0
        net_product_array = np.zeros_like(product)

        for _, residue_row in residue_rows.iterrows():
            LHV = residue_row['LHV (MJ/kg)']
            SAF = residue_row['SAF']
            RPR = residue_row['RPR']

            # Multiply the sum_product with RPR, SAF, and LHV
            result = sum_product * RPR * SAF * LHV * (10 ** -3) # Unit conversion factor to PetaJoules
            temp_sum += result
            product_array = product * RPR * SAF * LHV * (10 ** -3)
            net_product_array += product_array
            
            

        net_sum += temp_sum
        

        # Create xarray DataArray to store individual biomass potential for the current crop
        crop_biomass_potential_array = xr.DataArray(data= net_product_array,
                                                    dims=('y', 'x'),
            coords={'y': range(clipped_shapefile_init.shape[0]), 'x': range(clipped_shapefile_init.shape[1]),
                                'latitude': (('x', 'y'), lats_init), 'longitude': (('x', 'y'), lons_init)},
                                                    attrs={'units': 'PetaJoules',
                                                           'sum_production': temp_sum})  # Add sum as an attribute

        # Sum the individual biomass potential with the net biomass potential
        net_biomass_potential_array += crop_biomass_potential_array

        # Store the individual biomass potential for the current crop in the dictionary
        individual_biomass_potentials[crop] = crop_biomass_potential_array

    # Create xarray Dataset to hold all the individual biomass potentials for each crop
    biomass_potentials_dataset = xr.Dataset(individual_biomass_potentials)

    # Add the net sum of all crops and their residues as an attribute to the Dataset
    biomass_potentials_dataset.attrs['net_sum in PJ'] = net_sum

    # Add the net_biomass_potential_array as a new variable named 'combined' to the biomass_potentials_dataset
    biomass_potentials_dataset['Combined'] = net_biomass_potential_array
    
    biomass_potentials_dataset['Combined'].attrs['sum_production'] = net_sum

    return biomass_potentials_dataset


# #### Additional functions:
# The following functions are available if you just need the final numbers for the biomass energy potential for the 
# region. It has two options either it can give you the net or it can give you the values for a specific crop as well.

# In[11]:


# Function doing as described above

def future_residues_all(time_period, climate_model, rcp, water_supply_future, input_level, shapefile_path, water_supply_2010):
    
    value = future_potential_cropland(time_period, climate_model, rcp, water_supply_future, input_level, shapefile_path, water_supply_2010)
    
    answer = value.attrs['net_sum']
    
    return answer


# In[12]:


# We also wanted to create a function that does this for a single crop as well.

def future_residues_crop(crop, time_period, climate_model, rcp, water_supply_future, input_level, shapefile_path, water_supply_2010):
    
    value = future_potential_cropland(time_period, climate_model, rcp, water_supply_future, input_level, shapefile_path, water_supply_2010)
    
    answer = value[crop].attrs['sum_production']
    
    return answer


# So this completes all cropland residue calculations for us. Next we will move to residue and biomass energy potential from the marginal land but before we get into this we will have to generate the marginal land. So we need to extract certain pixels from certain rasters which will be masked later to account for removal of deserts, water, glaciers etc. as described in the paper

# ## III. Raw Biomass Energy Potential from Agricultural Residues using Agro-Climatic Potential Yield for future yields data [GAEZv4 Theme: 3]

# Before moving on to describe the functions, we need to obtain the RPR, SAF and LHV values for the crops available in the potential yield theme in GAEZ. The following is the table followed by the assumptions made and references:

# <h2><center>Final Potential Yield Crop Table with RPR, SAF and LHV values</center></h2>
# 
# | Crop                  | Residue Type    | RPR   | SAF   | LHV (MJ/kg) |
# |:----------------------:|:-----------------:|:-------:|:-------:|:-------------:|
# | Alfalfa               | residue         | 0.25  | 0.0   | 0.0         |
# | Banana                | leaves          | 0.35  | 0.9   | 11.745      |
# | Banana                | peels           | 0.25  | 1     | 14.78       |
# | Banana                | stem            | 4.90  | 0.9   | 11.66       |
# | Barley                | stalk           | 1.60  | 0.60  | 18.5        |
# | Barley                | straw           | 0.75  | 0.15  | 17.5        |
# | Biomass highland sorghum |Husk            | 1.4   | 1     | 13          |
# | Biomass highland sorghum | Straw           | 1.25  | 0.8   | 12.38       |
# | Biomass lowland sorghum  |Husk            | 1.4   | 1     | 13          |
# |Biomass lowland sorghum  | Straw           | 1.25  | 0.8   | 12.38       |
# | Biomass sorghum       |Husk            | 1.4   | 1     | 13          |
# |Biomass sorghum        | Straw           | 1.25  | 0.8   | 12.38       |
# | Biomass temperate sorghum | Husk            | 1.4   | 1     | 13          |
# | Biomass temperate sorghum | Straw           | 1.25  | 0.8   | 12.38       |
# | Buckwheat             | straw         | 1.2   | 0.40  | 16.845      |
# | Cabbage               | residue       | 0.675 | 0.50  | 12.625      |
# | Carrot                | residue       | 0.675 | 0.50  | 12.625      |
# | Cassava               | Peelings        | 3     | 0.2   | 10.61       |
# | Cassava               | Stalk           | 0.062 | 0.407 | 16.99       |
# | Chickpea              | stalk         | 1.78  | 0.504 |15.53        |
# | Citrus                | pruning        | 0.29     | 0.8   | 17.85       |
# | Cocoa                 |  pods/husks    | 1     | 1     | 15.48       |
# | Cocoa cumoun          |  pods/husks    | 1     | 1     | 15.48       |
# | Cocoa hybrid          |  pods/husks    | 1     | 1     | 15.48       |
# | Coconut               | Husk           | 1.03  | 1     | 18.6        |
# | Coconut               | Coir dust      | 0.62  | 1     | 13.4        |
# | Cocoyam               |  Peelings      | 0.2   | 0.8   | 10.61       |
# | Coffee                | husk          | 1     | 1     | 12.8         |
# | Coffee arabica        |husk          | 1     | 1     | 12.8          |
# | Coffee robusta        |husk          | 1     | 1     | 12.8          |
# | Cotton                | stalk           | 2.1   | 1     | 15.9       |
# | Cowpea                | stalk         | 1.78  | 0.504 |15.53         |
# | Dry pea               |stalk         | 1.78  | 0.504 |15.53          |
# | Dryland rice          | Husk            | 0.23  | 0.83  | 12.9       |
# | Dryland rice          | Straw           | 1.757 | 0.684 | 8.83       |
# | Flax                  |  stalk           | 2.50  | 0.60  | 14.2      |
# | Foxtail millet        |  Stalk           | 1.75  | 0.8   | 15.51     |
# | Foxtail millet                | Straw           | 1.4   | 1     | 13 |
# | Gram                  |stalk         | 1.1   | 0.38  |16.02          |
# | Grass                 |  straw         | 0.4   | 0     | 0           |
# | Greater yam           |Peelings      | 0.2   | 0.8   | 10.61         |
# | Groundnut             | Shells/husks    | 0.477 | 1     | 15.56      |
# | Groundnut             | Straw           | 2.3   | 1     | 17.58      |
# | Highland maize        | Cob             | 0.273 | 1     | 16.63      |
# | Highland maize                 | Husk            | 0.2   | 1     | 15.56|
# | Highland maize                 | Stalk           | 2     | 0.8   | 16.3 |
# | Highland sorghum      | Husk            | 1.4   | 1     | 13         |
# |Highland sorghum       | Straw           | 1.25  | 0.8   | 12.38      |
# | Jatropha | Woody Biomass | 0.25 | 0.8 | 15.5 |
# | Jatropha | Leaves | 0.25 | 0.8 | 12 |
# | Jatropha | Pericarp | 0.20 | 0.8 | 10 |
# | Jatropha | Tegument | 0 | 10.8 | 16.9 |
# | Jatropha | Endosperm Cake | 0.2 | 0.8 | 13.6 |
# | Lowland maize         | Cob             | 0.273 | 1     | 16.63       |
# | Lowland maize                 | Husk            | 0.2   | 1     | 15.56       |
# | Lowland maize                 | Stalk           | 2     | 0.8   | 16.3        |
# | Lowland sorghum       |Husk            | 1.4   | 1     | 13          |
# |Lowland sorghum        | Straw           | 1.25  | 0.8   | 12.38       |
# | Maize                 | Cob             | 0.273 | 1     | 16.63       |
# | Maize                 | Husk            | 0.2   | 1     | 15.56       |
# | Maize                 | Stalk           | 2     | 0.8   | 16.3        |
# | Millet                | Stalk           | 1.75  | 0.8   | 15.51       |
# | Millet                | Straw           | 1.4   | 1     | 13          |
# | Miscanthus            | residue        | 0.42   | 1     | 17.44       |
# | Napier grass          |  straw         | 0.4   | 0     | 0            |
# | Oat                   | straw  |    1.15 |  0.40 | 18.45|
# | Oil palm              | Empty bunches   | 0.428 | 1     | 19.41       |
# | Oil palm              | Fiber           | 0.147 | 1     | 19.94       |
# | Oil palm              | Fronds          | 2.604 | 1     | 7.97        |
# | Oil palm              | Male bunches    | 0.233 | 1     | 14.86       |
# | Oil palm              | Shells          | 0.049 | 1     | 21.1        |
# | Olive                 | cake          | 0.40  | 0.90  | 19.7        |
# | Onion                 | residue       | 0.675 | 0.50  | 12.625      |
# | Para rubber           | residue               | 0     | 0     | 0           |
# | Pasture legumes       | stalk         | 1.78  | 0.504 |15.53        |
# | Pearl millet          |  Stalk           | 1.75  | 0.8   | 15.51       |
# | Pearl millet                | Straw           | 1.4   | 1     | 13          |
# | Phaseolus bean        |stalk         | 1.78  | 0.504 |15.53        |
# | Pigeonpea             |stalk         | 1.78  | 0.504 |15.53        |
# | Rapeseed              | straw           | 1.58  | 0.23  | 14.55       |
# | Reed canary grass     |  straw         | 0.4   | 0     | 0           |
# | Rye                   |   straw| 1.25|   0.40  | 15.24|
# | Silage maize          | Cob             | 0.273 | 1     | 16.63       |
# | Silage maize                 | Husk            | 0.2   | 1     | 15.56       |
# | Silage maize                 | Stalk           | 2     | 0.8   | 16.3        |
# | Sorghum               | Husk            | 1.4   | 1     | 13          |
# | Sorghum               | Straw           | 1.25  | 0.8   | 12.38       |
# | Soybean               | Pods            | 1     | 0.8   | 18          |
# | Soybean               | Straw           | 2.66  | 0.8   | 18          |
# | Spring barley         | stalk           | 1.60  | 0.60  | 18.5        |
# | Spring barley                | straw           | 0.75  | 0.15  | 17.5        |
# | Spring rye            |  straw| 1.25|   0.40  | 15.24|
# | Spring wheat          |  Husk            | 0.23  | 0.29  | 12.9        |
# | Spring wheat                 | Straw           | 1.2   | 0.29  | 15.6        |
# | Sugarbeet             | residue         | 0.66  | 0.09  | 0           |
# | Sugar Cane   | baggase       | 0.25  | 1     | 6.43        |
# | Sugar Cane   | tops/leaves   | 0.32  | 0.8   | 15.8        |
# | Sunflower             | stalk           | 2.50  | 0.60  | 14.2        |
# | Sweet potato          |  Peelings      | 0.6   | 0.8   | 10.61       |
# | Switchgrass           | straw         | 0.4   | 0     | 0           |
# | Tea                   | husks         | 1     | 1     | 14.14       |
# | Temperate maize       | Cob             | 0.273 | 1     | 16.63       |
# | Temperate maize                 | Husk            | 0.2   | 1     | 15.56       |
# | Temperate maize                 | Stalk           | 2     | 0.8   | 16.3        |
# | Temperate sorghum     |Husk            | 1.4   | 1     | 13          |
# | Temperate sorghum     | Straw           | 1.25  | 0.8   | 12.38       |
# | Tobacco               | stalk           | 1.20  | 0.60  | 16.1        |
# | Tomato                | stem          |0.3    | 0.50  | 13.7        | l               |
# | Tomato                | leaves        |0.3    | 0.50  | 13.7        | l               |
# | Wetland rice          | Husk            | 0.23  | 0.83  | 12.9        |
# | Wetland rice          | Straw           | 1.757 | 0.684 | 8.83        |
# | Wheat                 | Husk            | 0.23  | 0.29  | 12.9        |
# | Wheat                 | Straw           | 1.2   | 0.29  | 15.6        |
# | White potato          | Peelings      | 0.75  | 0.8   | 10.61       |
# | White yam             | Peelings      | 0.2   | 0.8   | 10.61       |
# | Winter barley         |  stalk           | 1.60  | 0.60  | 18.5        |
# | Winter barley                | straw           | 0.75  | 0.15  | 17.5        |
# | Winter rye            |   straw| 1.25|   0.40  | 15.24|
# | Winter wheat          |  Husk            | 0.23  | 0.29  | 12.9        |
# | Winter wheat                 | Straw           | 1.2   | 0.29  | 15.6        |
# | Yam                   |Peelings      | 0.2   | 0.8   | 10.61       |
# | Yellow yam            | Peelings      | 0.2   | 0.8   | 10.61       |
# 

# Since some extra crops have been added to this table in comparison to the previous table here are the references and few assumptions that have been made in order to make this table complete:
# 
# For a few of the crops I have assigned them value based on the following assumptions:
# 
# - Biomass highland sorghum, Biomass lowland sorghum, Biomass temperate sorghum, Highland sorghum, Lowland sorghum, Temperate sorghum will all be assigned just the sorghum value.
# - Buckwheat will take the value of other cereals
# - Onion, Cabbage, Carrot will take the value for vegetables
# - Cocoa, Cocoa cumoun, Cocoa hybrid will take the value of Cocoa.
# - Coffee, Coffee arabica, Coffee robusta will take the value of Coffee.
# - Dryland Rice will take the value of Rice/Wetland Rice.
# - Pearl millet, Foxtail millet, Millet will take the value of Millet.
# - Greater yam, White yam, Yam, Yellow yam will all be assigned the value of Yam.
# - Highland maize, Lowland maize, Silage maize, Temperate maize and Maize will be assigned the value of Maize.
# - Spring barley, Winter barley will take the value of Barley 
# - Spring rye, Winter rye will take the value of rye
# - Spring wheat, Winter wheat will take the value of wheat
# - White potato will take the value of Potato
# - Tea will take the value of stimulants.
# - ChickPea, Cowpea, Dry Pea, Pasture Legumes, Phaseolus bean, Pigeonpea will take the value of pulses.
# - Alfalfa, Grass, Napier grass, Para, Rubber, Reed canary grass will take the value of fodder crops.(Alfalfa takes green fodder values which will have different RPR(0.25) but SAF will be 0.)
# - Flax, being similar to sunflower, takes the values of sunflower since they belong to similar crop category.
# - Citrus here includes the average of Oranges and Lemons
# 
# For the crops included above and not in the previous table here are the references:
# 
# - Coconut : Reference: https://www.aimspress.com/article/doi/10.3934/energy.2023002?viewType=HTML
# - Citrus :  Reference:https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9941997/
# - Jatropha : Reference : doi: 10.1016/j.rser.2015.10.009.
# - Miscanthus RPR/SAF & LHV: https://www.sciencedirect.com/science/article/pii/S1161030101001022. & https://www.researchgate.net/publication/338950136_Calorific_values_of_Miscanthus_x_giganteus_biomass_cultivated_under_suboptimal_conditions_in_marginal_soils            
# - Para Rubber : None

# In[13]:


# The final crop data being added to a pandas dataframe:

data = [
    ['Alfalfa', 'residue', 0.25, 0.0, 0.0],
    ['Banana', 'leaves', 0.35, 0.9, 11.745],
    ['Banana', 'peels', 0.25, 1, 14.78],
    ['Banana', 'stem', 4.90, 0.9, 11.66],
    ['Barley', 'stalk', 1.60, 0.60, 18.5],
    ['Barley', 'straw', 0.75, 0.15, 17.5],
    ['Biomass highland sorghum', 'Husk', 1.4, 1, 13],
    ['Biomass highland sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Biomass lowland sorghum', 'Husk', 1.4, 1, 13],
    ['Biomass lowland sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Biomass sorghum', 'Husk', 1.4, 1, 13],
    ['Biomass sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Biomass temperate sorghum', 'Husk', 1.4, 1, 13],
    ['Biomass temperate sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Buckwheat', 'straw', 1.2, 0.40, 16.845],
    ['Cabbage', 'residue', 0.675, 0.50, 12.625],
    ['Carrot', 'residue', 0.675, 0.50, 12.625],
    ['Cassava', 'Peelings', 3, 0.2, 10.61],
    ['Cassava', 'Stalk', 0.062, 0.407, 16.99],
    ['Chickpea', 'stalk', 1.78, 0.504, 15.53],
    ['Citrus', 'prunings', 0.29 , 0.80 , 17.85],
    ['Cocoa', 'pods/husks', 1, 1, 15.48],
    ['Cocoa cumoun', 'pods/husks', 1, 1, 15.48],
    ['Cocoa hybrid', 'pods/husks', 1, 1, 15.48],
    ['Coconut', 'husk', 1.03, 1, 18.6],
    ['Coconut','coir dust', 0.62, 1, 13.4],
    ['Cocoyam', 'Peelings', 0.2, 0.8, 10.61],
    ['Coffee', 'husk', 1, 1, 12.8],
    ['Coffee arabica', 'husk', 1, 1, 12.8],
    ['Coffee robusta', 'husk', 1, 1, 12.8],
    ['Cotton', 'stalk', 2.1, 1, 15.9],
    ['Cowpea', 'stalk', 1.78, 0.504, 15.53],
    ['Dry pea', 'stalk', 1.78, 0.504, 15.53],
    ['Dryland rice', 'Husk', 0.23, 0.83, 12.9],
    ['Dryland rice', 'Straw', 1.757, 0.684, 8.83],
    ['Flax', 'stalk', 2.5, 0.6, 14.2],
    ['Foxtail millet', 'Stalk', 1.75, 0.8, 15.51],
    ['Foxtail millet', 'Straw', 1.4, 1, 13],
    ['Gram', 'stalk', 1.1, 0.38, 16.02],
    ['Grass', 'straw', 0.4, 0, 0],
    ['Greater yam', 'Peelings', 0.2, 0.8, 10.61],
    ['Groundnut', 'Shells/husks', 0.477, 1, 15.56],
    ['Groundnut', 'Straw', 2.3, 1, 17.58],
    ['Highland maize', 'Cob', 0.273, 1, 16.63],
    ['Highland maize', 'Husk', 0.2, 1, 15.56],
    ['Highland maize', 'Stalk', 2, 0.8, 16.3],
    ['Highland sorghum', 'Husk', 1.4, 1, 13],
    ['Highland sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Jatropha', 'Woody Biomass', 0.25, 0.8, 15.5],
    ['Jatropha', 'Leaves', 0.25, 0.8, 12],
    ['Jatropha', 'Pericarp', 0.20, 0.8, 10],
    ['Jatropha', 'Tegument', 0, 10.8, 16.9],
    ['Jatropha', 'Endosperm Cake', 0.2, 0.8, 13.6],
    ['Lowland maize', 'Cob', 0.273, 1, 16.63],
    ['Lowland maize', 'Husk', 0.2, 1, 15.56],
    ['Lowland maize', 'Stalk', 2, 0.8, 16.3],
    ['Lowland sorghum', 'Husk', 1.4, 1, 13],
    ['Lowland sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Maize', 'Cob', 0.273, 1, 16.63],
    ['Maize', 'Husk', 0.2, 1, 15.56],
    ['Maize', 'Stalk', 2, 0.8, 16.3],
    ['Millet', 'Stalk', 1.75, 0.8, 15.51],
    ['Millet', 'Straw', 1.4, 1, 13],
    ['Miscanthus', 'residue', 0.42, 1, 17.44],
    ['Napier grass', 'straw', 0.4, 0, 0],
    ['Oat', 'straw', 1.15, 0.4, 18.45],
    ['Oil palm', 'Empty bunches', 0.428, 1, 19.41],
    ['Oil palm', 'Fiber', 0.147, 1, 19.94],
    ['Oil palm', 'Fronds', 2.604, 1, 7.97],
    ['Oil palm', 'Male bunches', 0.233, 1, 14.86],
    ['Oil palm', 'Shells', 0.049, 1, 21.1],
    ['Olive', 'cake', 0.4, 0.9, 19.7],
    ['Onion', 'residue', 0.675, 0.5, 12.625],
    ['Para rubber', 'residue', 0, 0, 0],
    ['Pasture legumes', 'stalk', 0, 0, 0],
    ['Pearl millet', 'Stalk', 1.75, 0.8, 15.51],
    ['Pearl millet', 'Straw', 1.4, 1, 13],
    ['Phaseolus bean', 'stalk', 1.78, 0.504, 15.53],
    ['Pigeonpea', 'stalk', 1.78, 0.504, 15.53],
    ['Rapeseed', 'straw', 1.58, 0.23, 14.55],
    ['Reed canary grass', 'straw', 0.4, 0, 0],
    ['Rye', 'straw', 1.25, 0.4, 15.24],
    ['Silage maize', 'Cob', 0.273, 1, 16.63],
    ['Silage maize', 'Husk', 0.2, 1, 15.56],
    ['Silage maize', 'Stalk', 2, 0.8, 16.3],
    ['Sorghum', 'Husk', 1.4, 1, 13],
    ['Sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Soybean', 'Pods', 1, 0.8, 18],
    ['Soybean', 'Straw', 2.66, 0.8, 18],
    ['Spring barley', 'stalk', 1.6, 0.6, 18.5],
    ['Spring barley', 'straw', 0.75, 0.15, 17.5],
    ['Spring rye', 'straw', 1.25, 0.4, 15.24],
    ['Spring wheat', 'Husk', 0.23, 0.29, 12.9],
    ['Spring wheat', 'Straw', 1.2, 0.29, 15.6],
    ['Sugarbeet', 'residue', 0.66, 0.09, 0],
    ['Sugar Cane', 'baggase', 0.25, 1, 6.43],
    ['Sugar Cane', 'tops/leaves', 0.32, 0.8, 15.8],
    ['Sunflower', 'stalk', 2.5, 0.6, 14.2],
    ['Sweet potato', 'Peelings', 0.6, 0.8, 10.61],
    ['Switchgrass', 'straw', 0.4, 0, 0],
    ['Tea', 'husks', 1, 1, 14.14],
    ['Temperate maize', 'Cob', 0.273, 1, 16.63],
    ['Temperate maize', 'Husk', 0.2, 1, 15.56],
    ['Temperate maize', 'Stalk', 2, 0.8, 16.3],
    ['Temperate sorghum', 'Husk', 1.4, 1, 13],
    ['Temperate sorghum', 'Straw', 1.25, 0.8, 12.38],
    ['Tobacco', 'stalk', 1.2, 0.6, 16.1],
    ['Tomato', 'stem', 0.3, 0.5, 13.7],
    ['Tomato', 'leaves', 0.3, 0.5, 13.7],
    ['Wetland rice', 'Husk', 0.23, 0.83, 12.9],
    ['Wetland rice', 'Straw', 1.757, 0.684, 8.83],
    ['Wheat', 'Husk', 0.23, 0.29, 12.9],
    ['Wheat', 'Straw', 1.2, 0.29, 15.6],
    ['White potato', 'Peelings', 0.75, 0.8, 10.61],
    ['White yam', 'Peelings', 0.2, 0.8, 10.61],
    ['Winter barley', 'stalk', 1.6, 0.6, 18.5],
    ['Winter barley', 'straw', 0.75, 0.15, 17.5],
    ['Winter rye', 'straw', 1.25, 0.4, 15.24],
    ['Winter wheat', 'Husk', 0.23, 0.29, 12.9],
    ['Winter wheat', 'Straw', 1.2, 0.29, 15.6],
    ['Yam', 'Peelings', 0.2, 0.8, 10.61],
    ['Yellow yam', 'Peelings', 0.2, 0.8, 10.61]
]

# Defining the column names
columns = ['Crop', 'Residue Type', 'RPR', 'SAF', 'LHV (MJ/kg)']

# Create the DataFrame
all_residue_values = pd.DataFrame(data, columns=columns)


# Helper function for clipping any raster according to the selected region

# In[14]:


def maskingwithshapefile(shapefile, raster_path):
    
    with rasterio.open(raster_path) as src:
        crs= src.crs
        shapefile.crs=crs
        clipped, transform = mask(src, shapefile.geometry, crop=True )
        # This returns a numpy array on which we will conduct operations.
    return clipped


# Helper functions for converting numpy arrays to raster format again to give us a clipped raster ( We have used the MemoryFile datatype in rasterio which allows us to create rasters in the active memory without the need to download these to the computer)

# In[15]:


# For clipped arrays :

# The clipped one has extra parameters which ensure that the clipped raster has the correct latitudes and 
# longitudes acc. to the chosen CRS. This will be mostly useful when we will try to extract rasters with the
# correct longitude and latitude values.


# Create a function to convert a NumPy array to an in-memory raster
def array_to_inmemory_raster_for_clipped(array, transform, crs, shapefile):
    
    if len(array.shape) == 2:
        array = array.reshape((1, array.shape[0], array.shape[1]))  # Add a singleton dimension

    _, height, width = array.shape  # Extract the height and width from the shape

    # Reshape the array to 2 dimensions
    array = array[0]  # Extract the first dimension to remove the extra dimension
    
    # Correcting the transform for correct axes value representation
    
    shapefile.geometry.iloc[0]
    xmin = shapefile.bounds.iloc[0,3]
    ymax = shapefile.bounds.iloc[0,0]
    topleft_corner = (xmin,ymax)


    a = transform.a
    b = transform.b
    d = transform.d
    e = transform.e

    transform = Affine(a, b, ymax, d, e, xmin)
    
    # Update the transform with corrected values to make sure only the region of shapefile is represented
    transform = Affine(transform.a, transform.b, ymax, transform.d, transform.e, xmin)
    
    # Define the raster metadata
    meta = {
        'count': 1,
        'dtype': array.dtype,
        'width': width,
        'height': height,
        'crs': crs,
        'transform': transform
    }

    # Create an in-memory raster file
    memory_file = rasterio.MemoryFile()
    with memory_file.open(driver='GTiff', **meta) as dst:
        dst.write(array, 1)

    return memory_file


# In[16]:


# For Non-Clipped :

# This function might not be as used like the above one and will mostly be used only when converting the full 
# rasters from one resolution to the other along with resampling of data.

def array_to_inmemory_raster_for_non_clipped(array, transform, crs):
    if len(array.shape) == 2:
        array = array.reshape((1, array.shape[0], array.shape[1]))  # Add a singleton dimension

    _, height, width = array.shape  # Extract the height and width from the shape

    # Reshape the array to 2 dimensions
    array = array[0]  # Extract the first dimension to remove the extra dimension

    # Define the raster metadata
    meta = {
        'count': 1,
        'dtype': array.dtype,
        'width': width,
        'height': height,
        'crs': crs,
        'transform': transform
    }

    # Create an in-memory raster file
    memory_file = rasterio.MemoryFile()
    with memory_file.open(driver='GTiff', **meta) as dst:
        dst.write(array, 1)

    return memory_file


# Helper Functions for extracting select pixels from selected rasters and then putting them in a dataframe along with their coordinates so that they can be removed/masked later.

# In[17]:


# Once we have the rasters we are ready to extract specific pixels from it. The following functions
# will help us do exactly that. One of them will extract pixels with specific values and the other will 
# extract pixels having value above a certain threshold.

def coordinates_and_values(raster_path, pixel_values):
    
    with rasterio.open(raster_path) as src:
        df = pd.DataFrame()  
        raster_band = src.read(1) 
        transform_coordinate_conversion = src.transform

        for i in pixel_values:
            rows, cols = np.where(raster_band == i)  # extract row and column numbers for each pixel
            coords = transform_coordinate_conversion * (cols, rows)
            lon, lat = coords[0], coords[1]  

            values = raster_band[rows,cols]
            df_i = pd.DataFrame({'lon': lon, 'lat': lat, 'pixel': values, 'row': rows, 'col': cols}) 
            df = pd.concat([df, df_i], ignore_index=True)  # append to get DataFrame of lon, lat, row, col, and 
            # pixel

    return df

def coordinates_and_threshold(raster_path, threshold):
    
    with rasterio.open(raster_path) as src:
        df = pd.DataFrame()  
        raster_band = src.read(1)  
        transform_coordinate_conversion = src.transform

        rows, cols = np.where(raster_band > threshold)  # find row and column indices for pixel values above 
        # threshold
        coords = transform_coordinate_conversion * (cols, rows)
        lon, lat = coords[0], coords[1] 

        values = raster_band[rows, cols]  # extract pixel values above threshold
        df = pd.DataFrame({'lon': lon, 'lat': lat, 'row': rows, 'col': cols, 'pixel': values})  

    return df


# Helper functions for converting doing the clipping to shapefile and conversion back to raster in a single function & for converting dfs generated above to gdf so that the stored locations can be used to remove/mask these pixels later

# In[18]:


def clipper(shapefile, raster_path):
    
    with rasterio.open(raster_path) as src:
        transform_store = src.transform
        crs_store = src.crs
        
    masked = maskingwithshapefile(shapefile , raster_path)
    output_raster = array_to_inmemory_raster_for_clipped(masked, transform_store, crs_store, shapefile)
    
    return output_raster


# In[19]:


# Creating this function since both the value and threshold functions give us dataframes and we will need
# geodataframes containing the geometry column with the Point values for each pixel.

def convert_df_to_gdf(dataframe):
    
    # Convert the DataFrame of coordinates to a GeoDataFrame
    geometry = [Point(lon, lat) for lon, lat in zip(dataframe['lon'], dataframe['lat'])]
    coordinates_gdf = gpd.GeoDataFrame(dataframe, geometry=geometry)
    
    return coordinates_gdf


# Helper function for conversion of rasters from higher resolution to lower resolution

# In[20]:


# Also since the crop data is in a lower resolution than the AEZ classsification and other data so we will also 
# create a fn. for the conversion of Resolution from a higher to lower resolution along with resampling of the 
# pixel values. The current method of resampling used is 'Mode' method.

def resolution_converter_mode(raster_path , resampling_method):
    
    downscale_factor = 10 
    with rasterio.open(raster_path) as dataset:

        # Compute the downsampled shape and final resolution based on the downscale factor
        downsampled_height = int(dataset.height / downscale_factor)
        downsampled_width = int(dataset.width / downscale_factor)
        downsampled_shape = (dataset.count, downsampled_height, downsampled_width)
        initial_resolution = dataset.res[0]
        final_resolution = initial_resolution * downscale_factor
        crs_final = dataset.crs

        # Resample the data to the target shape
        data = dataset.read(
            out_shape=downsampled_shape,
            resampling=resampling_method
        )

     # Compute the scale factors for the image transform
    scale_x =1/(initial_resolution / final_resolution)
    scale_y = 1/(-initial_resolution / -final_resolution)
    
    initial_transform = Affine(initial_resolution, 0.0, -180.0, 0.0, -initial_resolution, 90.0 )

    # Scale the image transform
    transform = initial_transform * initial_transform.scale(scale_x, scale_y)

    # Reshape the data array to have two dimensions (height x width)
    reshaped_data = data[0, :, :]

    return array_to_inmemory_raster_for_non_clipped(reshaped_data, transform, crs_final)


# Helper function for removal of accumulated pixels in the GeoDataFrame

# In[21]:


# To explain it a bit more, what we do is get those pixels and assign the pixels to be removed a nodata value.


def remove_pixels(raster_path, shapefile, geodataframe):
    with rasterio.open(raster_path) as src:
        # Mask the raster using the shapefile boundary
        clipped, transform = mask(src, shapefile.geometry, crop=True)
        crs = src.crs

    raster_used = array_to_inmemory_raster_for_clipped(clipped, transform, crs, shapefile)

    dataset = rasterio.open(raster_used)
    
    # Load the GeoDataFrame
    gdf = geodataframe
    
    # Convert the row and column numbers to pixel coordinates
    pixel_coords = zip(gdf['row'], gdf['col'])
    
    # Create a mask with the same dimensions as the raster
    masked = np.zeros((dataset.height, dataset.width), dtype=np.uint8)
    
    # Set the pixels at the specified coordinates to a nodata value
    nodata_value = 255
    for row, col in pixel_coords:
        masked[row, col] = nodata_value
    
    # Read the raster data
    data = dataset.read(1)
    
    # Apply the mask
    data = np.where(masked == nodata_value, np.nan, data)
    
    return data


# So what this function does, is that it takes a sample raster path as input first clips it. Then it creates a
# mask layer using the sample raster while assigning nodata values to the points we want removed. 


# Helper function for going over the selected region and identifying which crop to grow to maximize energy extraction

# In[22]:


def find_max_for_each_pixel(time_period, climate_model, rcp, water_supply_future, input_level,
                            shapefile, geodataframe):
    # Initialize dictionaries to store the data for each crop and their residues
    crop_data = {}
    max_values = None
    max_crops = None
    crop_residue_sum_dict = {}  # Dictionary to store crop_residue_sum_array for each crop
    
    filtered_potential_yield = potential_yield[(potential_yield['Time Period'] == time_period) &
                                               (potential_yield['Climate Model'] == climate_model) &
                                               (potential_yield['RCP'] == rcp) &
                                               (potential_yield['Water Supply'] == water_supply_future) &
                                               (potential_yield['Input Level'] == input_level)]
    required_potential_yields = filtered_potential_yield[['Crop', 'Download URL']]
    
    # For defining size of the xarray
    with rasterio.open(potential_yield.iloc[2, 14].strip()) as src:
        clipped_shapefile_init, transform_init = mask(src, shapefile.geometry, crop=True)
        clipped_shapefile_init = remove_band_dimension(clipped_shapefile_init)
        lats_init, lons_init = get_lat_lon_from_transform(transform_init, clipped_shapefile_init.shape)
    
    # Iterate over the global rasters
    for crop in potential_yield['Crop'].unique():
        # Find the correct raster path for the rasters you want to access
        raster_path = required_potential_yields[required_potential_yields['Crop'] == crop]['Download URL'].values[0].strip()
        
        # Remove pixels from the raster
        data = remove_pixels(raster_path, shapefile, geodataframe)
        
        # Multiply the values with the corresponding RPR, SAF, and LHV
        residue_rows = all_residue_values.loc[all_residue_values['Crop'] == crop]
        crop_residue_sum_array = np.zeros_like(data)
        for _, residue_row in residue_rows.iterrows():
            LHV = residue_row['LHV (MJ/kg)']
            SAF = residue_row['SAF']
            RPR = residue_row['RPR']
            data_final = data * LHV * SAF * RPR
            
            # Handle NaN values by converting them to zero
            data_final = np.nan_to_num(data_final, nan=0)
            positive_data_mask = data_final >= 0
            data_final = data_final * positive_data_mask
            
            crop_residue_sum_array += data_final 
        
        # Store the data for the current crop and their residues in dictionaries
        crop_residue_sum_dict[crop] = crop_residue_sum_array
        
        # Check if max_values array is None (first iteration)
        if max_values is None:
            max_values = crop_residue_sum_array
            max_crops = np.empty_like(crop_residue_sum_array).astype(str)
            max_crops[crop_residue_sum_array == None] = None
            max_crops[crop_residue_sum_array != None] = crop
        else:
            # Find the maximum value between the current raster and previous maximum values
            max_mask = crop_residue_sum_array > max_values
            max_values[max_mask] = crop_residue_sum_array[max_mask]
            max_crops[max_mask] = crop
    
    # Replace instances of "Alfalfa" with None/NaN in max_crops
    max_crops[max_crops == "Alfalfa"] = None

    # Create xarray Dataset to hold all the individual biomass potentials for each crop
    biomass_potentials_dataset = xr.Dataset()

    # Add the crop_residue_sum_array as a variable for each crop
    for crop, crop_residue_sum_array in crop_residue_sum_dict.items():
        # Remove spaces and special characters from crop name to make it a valid variable name
        variable_name = crop.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace(",", "")
    
        # Create a DataArray for the crop_residue_sum_array
        data_array = xr.DataArray(
            crop_residue_sum_array,
            dims=('y', 'x'),
            coords={'latitude': (('x', 'y'), lats_init), 'longitude': (('x', 'y'), lons_init)},
            attrs={'units': 'PetaJoules'}
        )
    
        # Add the DataArray as a variable to the dataset
        biomass_potentials_dataset[variable_name] = data_array
    
        # Add the yield sum as an attribute for the variable
        biomass_potentials_dataset[variable_name].attrs['sum'] = np.nansum(crop_residue_sum_array)

    # Add the max_values as a variable to the dataset
    biomass_potentials_dataset['max_values'] = xr.DataArray(
        max_values,
        dims=('y', 'x'),
        coords={'latitude': (('x', 'y'), lats_init), 'longitude': (('x', 'y'), lons_init)},
        attrs={'units': 'PetaJoules'}
    )
    biomass_potentials_dataset['max_values'].attrs['sum'] = np.nansum(max_values)
    
    # Add the max_crops as a variable to the dataset
    biomass_potentials_dataset['max_crops'] = xr.DataArray(
    max_crops,
    dims=('y', 'x'),
    coords={'latitude': (('x', 'y'), lats_init), 'longitude': (('x', 'y'), lons_init)}
        ).astype(str)
    
    # Add attributes for the sum of max_values and units
    biomass_potentials_dataset.attrs['net_sum'] = np.nansum(max_values)
    biomass_potentials_dataset.attrs['units'] = 'PetaJoules'

    return biomass_potentials_dataset


# Helper function for obtaining harvested area and for obtaining net pixel area for each pixel

# In[23]:


# To be able to find the harvested area per pixel we need to sum up the harvested area for each crop in each pixel
# and store it in the form of an numpy array. 

def get_net_harvested_area(shapefile, geodataframe):
    
    net_harvested_area_obtained = None  # Initialize the net harvested area array
    
    filtered_harvested_area = harvested_area[(harvested_area['Time Period'] == 2010) &
                                                   (harvested_area['Water Supply'] == 'Total')]
    required_harvested_area = filtered_harvested_area['Download URL']
    
    for required_url in required_harvested_area: # This will loop pover all the available crops in cropland.
        required_url = required_url.strip()
        
        with rasterio.open(required_url) as src:
            # Assuming shapefile is used for clipping
            # Adjust accordingly if using a different method for clipping
            
            # Clip the raster using the shapefile
            data = remove_pixels(required_url, shapefile , geodataframe)
            
            # Get the harvested area values from the clipped data
            harvested_area_obtained = data  # Adjust this line if necessary
            
            # Update the net harvested area array
            if net_harvested_area_obtained is None:
                net_harvested_area_obtained = harvested_area_obtained
            else:
                net_harvested_area_obtained += harvested_area_obtained
    
    return net_harvested_area_obtained*1000 # To make the unit as hectares


# In[24]:


# Simply using a simple cosine of latitude approximation to account for the curvature of the Earth. The
# consequences of making this simple approximation have been explored in detail in the paper.

def extract_pixel_area(raster_path, shapefile):
    with rasterio.open(raster_path) as src:
    # Clip the raster using the shapefile boundaries
        clipped_data, clipped_transform = mask(src, shapefile.geometry, crop=True)

    # Get the pixel dimensions of the clipped raster
    pixel_width = clipped_transform[0]
    pixel_height = clipped_transform[4]

    # Calculate the area of each pixel based on latitude
    pixel_area = np.zeros_like(clipped_data, dtype=np.float32)

    for band in range(clipped_data.shape[0]):
        for row in range(clipped_data.shape[1]):
            for col in range(clipped_data.shape[2]):
                if clipped_data[band, row, col] != src.nodata:
                    lat = rasterio.transform.xy(clipped_transform, row, col, offset='center')[1]
                    lat_rad = np.radians(lat)
                    pixel_area[band, row, col] = (np.abs(pixel_width * pixel_height * (111319.9)**2)*(np.cos(lat_rad)))/(10000) # conversion to hectares
    return pixel_area


# #### Final output function for marginal land data. 
# - It outputs an xarray containg the energy yields of each crop for the selected geography (These are not multiplied by the area since the area is the same and this saves compute). 
# - It also outputs the net biomass energy potential from the marginal land using the the crop energy yields which give the max energy extractable from each pixel. 
# - Finally it outputs the sum of this final array described in the second point.

# In[25]:


def get_biomass_potential_for_marginal(shapefile,time_period, climate_model, rcp, water_supply_future,
                                       input_level):
    
    # Selecting and correcting the resolution of the selected files
    
    initial_aez_chosen = aez_classification[(aez_classification['Time Period']== time_period)&
                                         (aez_classification['RCP']== rcp)]
    initial_aez_raster = initial_aez_chosen['Download URL'].values[0].strip()
    
    final_aez_raster = resolution_converter_mode(initial_aez_raster , Resampling.mode)
    
    initial_exclusion = exclusion_areas.iloc[0,9].strip()
    
    final_exclusion_raster = resolution_converter_mode(initial_exclusion , Resampling.mode)
    
    initial_tree = tree_cover_share.iloc[0,9].strip()
    
    final_tree_cover_raster = resolution_converter_mode(initial_tree , Resampling.average)
    
    pasture_raster = "./dataset/pasture_cubic_reproject.tif" # the reproject here is just to make the pixel size 0.083333 instead of 0.08328
    
    clipped_aez = clipper(shapefile , final_aez_raster)
    clipped_exclusion = clipper(shapefile, final_exclusion_raster)# Now remove 2 to 7 value range.
    clipped_tree = clipper(shapefile, final_tree_cover_raster)# Threshold == 50
    clipped_pasture = clipper(shapefile, pasture_raster)
    
    coordinates_aez= coordinates_and_values(clipped_aez, [49,50,52,53,55,56,57])
    coordinates_exclusion = coordinates_and_values(clipped_exclusion, [2,3,4,5,6,7])
    coordinates_tree = coordinates_and_threshold(clipped_tree, 50) 
    coordinates_pasture = coordinates_and_threshold(clipped_pasture, 0.5)
    
    coordinates_all = pd.concat([coordinates_aez, coordinates_exclusion, coordinates_tree,coordinates_pasture],
                                ignore_index=True)  # append to get DataFrame of lon, lat, row, col, and pixel
    
    gdf_final = convert_df_to_gdf(coordinates_all)
    
    biomass_potential_xarray = find_max_for_each_pixel(time_period, climate_model, rcp,
                                                       water_supply_future, input_level,
                                                       shapefile, gdf_final)
    
    harvested_area_from_shapefile = get_net_harvested_area(shapefile, gdf_final)
    
    net_area = extract_pixel_area(potential_yield.iloc[2,14].strip(), shapefile) # Just a reference raster so doesn't matter
    
    # Using sample raster potential_yield.iloc[2,14] to extract the base transform and crs used for all
    with rasterio.open(potential_yield.iloc[2,14].strip()) as src:
        standard_transform = src.transform
        standard_crs = src.crs
    
    remaining_area = np.subtract(net_area,harvested_area_from_shapefile)
    final_potential = np.multiply(biomass_potential_xarray['max_values'].values, remaining_area)*(10**-5)# Unit conversion MJ to Joules and 10 Kg to Kg and 
    # then 10**-12 for peta joules
    total_biomass_marginal_potential = np.nansum(final_potential)

    
    return total_biomass_marginal_potential, final_potential, biomass_potential_xarray


# #### Total Raw Biomass Energy Potential : 
# - This is the final total raw biomass energy potential function which gives us the sum of energy potential from each pixel for cropland and marginal land, which is the final intended output of our tool. 
# - It also outputs a final xarray which contains everything under their respective headings.

# In[26]:


def get_total_biomass_potential(shapefile, time_period, climate_model, rcp, water_supply_future, input_level, water_supply_2010):
    # Calculate biomass potential for cropland
    cropland_dataset = future_potential_cropland(time_period, climate_model, rcp, water_supply_future, input_level, shapefile, water_supply_2010)

    # Calculate biomass potential for marginal land
    marginal_land_potential, marginal_land_array, marginal_land_dataset = get_biomass_potential_for_marginal(shapefile, time_period, climate_model, rcp, water_supply_future, input_level)

    # Create an empty dataset to hold the outputs
    total_biomass_dataset = xr.Dataset(coords=cropland_dataset.coords)

    # Add attributes for the total sum of attributes for each pixel
    total_sum_cropland = cropland_dataset.attrs['net_sum in PJ']
    total_sum_marginal_land = marginal_land_potential
    total_biomass_dataset.attrs['net_energy_potential'] = total_sum_cropland + total_sum_marginal_land
    total_biomass_dataset.attrs['final_energy_array'] = marginal_land_array + cropland_dataset['Combined'].values

    return total_biomass_dataset , cropland_dataset , marginal_land_dataset , marginal_land_array


# Visualisation functions to be able to visualize the raster with pixel values shown & to show what crop is selected where incase of marginal lands

# In[2]:


# Assuming the rest of your code remains the same
def bokeh_plot(shapefile, array ):
    
    with rasterio.open(potential_yield.iloc[2,14].strip()) as src:
            standard_transform = src.transform 
            standard_crs= src.crs
    # Convert the GeoDataFrame to GeoJSONDataSource
    
    test = array_to_inmemory_raster_for_clipped(array, standard_transform,standard_crs,shapefile)
    
    geojson = gpd.GeoSeries(shapefile.geometry).to_json()
    geojson_data = GeoJSONDataSource(geojson=geojson)

    # Read the raster data using rasterio.open
    raster_path = test
    src = rasterio.open(raster_path)

    # Read the raster data into a NumPy array
    data = src.read(1)

    # Flip the raster data along the y-axis to align with Bokeh's coordinate system
    data = np.flipud(data)

    # Calculate the minimum and maximum x and y coordinates
    min_x, min_y, max_x, max_y = src.bounds

    # Calculate the minimum and maximum values for the color mapper using the 'combined' array
    combined_min = array.min().item()
    combined_max = array.max().item()

    # Create a new color mapper for the raster data
    mapper = LinearColorMapper(palette=bp.viridis(256), low=combined_min, high=combined_max)


    # Create a Bokeh figure
    p = figure(width=600, height=600, x_axis_label='Longitude', y_axis_label='Latitude', title='Interactive Raster')

    # Add the raster image to the figure using the 'image' glyph
    p.image(image=[data], x=min_x, y=min_y, dw=(max_x - min_x), dh= (max_y - min_y), color_mapper=mapper)

    # Add color bar to the plot
    color_bar = ColorBar(color_mapper=mapper, location=(0, 0))
    p.add_layout(color_bar, 'right')

# Add the boundary of Spain to the plot as a polygon
    p.patches('xs', 'ys', source=geojson_data, line_color='black', fill_alpha=0)

    # Add hover tool to display the pixel value when hovering over the raster
    hover = HoverTool(tooltips=[('Value', '@image')], mode='mouse')
    p.add_tools(hover)

    # Show the plot
    bpl.show(p)


# In[28]:


def crop_show(crop_array,shapefile):
# Define a colormap for different crops
    cmap = plt.get_cmap('tab20b')

# Create a color index array based on the unique crop names
    crop_names = np.unique(crop_array)
    crop_indices = {crop: i for i, crop in enumerate(crop_names)}

# Convert crop names to corresponding color indices
    color_index = np.vectorize(crop_indices.get)(crop_array)

# Assuming you have loaded the shapefile using rasterio
# and obtained the 'standard_transform' object
    with rasterio.open(potential_yield.iloc[2,14].strip()) as src:
            standard_transform = src.transform 
            standard_crs= src.crs

# Get the pixel size from the standard_transform
    pixel_size_x = standard_transform.a
    pixel_size_y = standard_transform.e

    graph_bounds = shapefile.bounds

    # Get the boundary values from the shapefile
    xmin = graph_bounds['minx'].min()
    xmax = graph_bounds['maxx'].max()
    ymin = graph_bounds['miny'].min()
    ymax = graph_bounds['maxy'].max()
    # Calculate the number of rows and columns in the raster
    rows, cols = color_index.shape

    # Create the transformation matrix for the raster
    transform = Affine(pixel_size_x, 0, xmin,
                   0, pixel_size_y, ymax)

# Create a memory file to store the raster
    with MemoryFile() as memfile:
        # Create a new raster dataset
        with memfile.open(driver='GTiff', height=rows, width=cols, count=1,
                          dtype=color_index.dtype, crs=standard_crs,
                          transform=transform) as dataset:
            # Write the color_index array to the raster dataset
            dataset.write(color_index, 1)

            # Plot the raster with shapefile boundaries
            show((dataset, 1), ax=plt.gca(), cmap=cmap)
        
            # Plot the shapefile boundary
            shapefile.plot(ax=plt.gca(), facecolor='none', edgecolor='black')
            
            # Create a legend for color-to-crop mapping
            legend_patches = [mpatches.Patch(color=cmap(i), label=crop) for crop, i in crop_indices.items()]
            plt.legend(handles=legend_patches, bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)



    # Set the title and show the plot
        plt.title('Crop Raster with Shapefile Boundaries')
        plt.show()


# These are the final visualisation functions which output the net raw biomass energy potential from the marginal and the cropland respectively and show them with an interactive plotly graph.

# In[2]:


def graph_plotter_cropland(shapefile, climate_model, water_supply_future, input_level):
    time_periods = ['2000', '2010', '2011-2040', '2041-2070', '2071-2100']
    RCPs = ['RCP2.6', 'RCP4.5', 'RCP6.0', 'RCP8.5']
    
    xarrays = {}  # Dictionary to store the xarray for each RCP and time period
    
    # Colors from the Google logo: Blue, Red, Yellow, Blue-Green
    colors = ['#4285F4', '#DB4437', '#F4B400', '#0F9D58']

    fig = go.Figure()
    
    value_1 = biomass_potential_past(shapefile, 2000, 'Total')
    value_2 = biomass_potential_past(shapefile, 2010, 'Total')
    
    xarrays[('2000')] = value_1
    xarrays[('2010')] = value_2

    initial_potential_1 = value_1.attrs['Net Potential in PetaJ']
    initial_potential_2 = value_2.attrs['Net Potential in PetaJ']

    # Add traces for 2000 and 2010 with different colors
    fig.add_trace(go.Bar(x=['2000'], y=[initial_potential_1], name='2000', marker_color='#000000'))
    fig.add_trace(go.Bar(x=['2010'], y=[initial_potential_2], name='2010', marker_color='#808080'))

    x_values = ['2000', '2010']  # Initialize x-axis values

    for i, RCP in enumerate(RCPs):
        biomass_potentials = []  # Initialize biomass_potentials for each time period

        for j, time_period in enumerate(time_periods[2:]):
            
            value_calculator = future_potential_cropland(time_period, climate_model, RCP, water_supply_future, input_level, shapefile, 'Total')
            
            potential_value = value_calculator.attrs['net_sum in PJ']
            biomass_potentials.append(potential_value)
            
            # Store the xarray in the xarrays dictionary with a tuple key (RCP, time_period)
            xarrays[(RCP, time_period)] = value_calculator

        # Assign the corresponding color from the Google logo to each time period
        color = colors[i % len(colors)]

        fig.add_trace(go.Bar(x=time_periods[2:], y=biomass_potentials, name=RCP, marker_color=color))

    fig.update_layout(
        barmode='group',
        xaxis_title='Years',
        yaxis_title='Biomass Energy Potential from Cropland Land',
        title='Cropland Biomass Energy Potential from different RCPs'
    )
    
    fig.show()

    return fig, xarrays


# In[3]:


def graph_plotter_marginal(shapefile, climate_model, water_supply_future, input_level):
    time_periods = ['2011-2040', '2041-2070', '2071-2100']
    RCPs = ['RCP2.6', 'RCP4.5', 'RCP6.0', 'RCP8.5']

    fig = go.Figure()
    xarrays = {}  # Dictionary to store the xarray for each RCP and time period
    final_potentials = {}  # Dictionary to store the final potential array for each RCP

    for i, RCP in enumerate(RCPs):
        biomass_potentials = []  # Initialize biomass_potentials for each time period

        for time_period in time_periods:
            total_biomass_marginal_potential, final_potential, xarray = get_biomass_potential_for_marginal(
                shapefile, time_period, climate_model, RCP, water_supply_future, input_level
            )
            biomass_potentials.append(total_biomass_marginal_potential)
            xarrays[(RCP, time_period)] = xarray
            final_potentials[(RCP, time_period)] = final_potential

        fig.add_trace(go.Bar(x=time_periods, y=biomass_potentials, name=RCP))

    fig.update_layout(
        barmode='group',
        xaxis_title='Time Periods',
        yaxis_title='Biomass Energy Potential from Marginal Land',
        title='Marginal Land Biomass Energy Potential from different RCPs in Time Periods'
    )
    
    fig.show()

    return fig, xarrays, final_potentials


# In[1]:


def graph_plotter_all(shapefile, climate_model, water_supply_future, input_level, water_supply_2010):
    time_periods = ['2011-2040','2041-2070', '2071-2100']
    RCPs = ['RCP2.6', 'RCP4.5', 'RCP6.0', 'RCP8.5']
    colors = ['#4285F4', '#DB4437', '#F4B400', '#0F9D58']
    
    fig_crop = go.Figure()
    fig_marg = go.Figure()
    fig_total = go.Figure()
    
    
    # For cropland 
    
    xarrays_crop = {}  
    value_1 = biomass_potential_past(shapefile, 2000, 'Total')
    value_2 = biomass_potential_past(shapefile, 2010, 'Total')
    
    xarrays_crop[('2000')] = value_1
    xarrays_crop[('2010')] = value_2

    initial_potential_1 = value_1.attrs['Net Potential in PetaJ']
    initial_potential_2 = value_2.attrs['Net Potential in PetaJ']

    # Add traces for 2000 and 2010 with different colors
    fig_crop.add_trace(go.Bar(x=['2000'], y=[initial_potential_1], name='2000', marker_color='#000000'))
    fig_crop.add_trace(go.Bar(x=['2010'], y=[initial_potential_2], name='2010', marker_color='#808080'))

    x_values = ['2000', '2010']  # Initialize x-axis values
    
    # For marginal land
    
    xarrays_marg = {}  # Dictionary to store the xarray for each RCP and time period
    final_potentials_marg = {}  # Dictionary to store the final potential array for each RCP
    
    # For total land 
    
    arrays_total = {}

    for i, RCP in enumerate(RCPs):
        biomass_potentials_crop = []  # Initialize biomass_potentials for each time period
        biomass_potentials_marg = []
        biomass_potentials_total = []

        for j, time_period in enumerate(time_periods):
            
            total_energy_potential, cropland_dataset, marginal_dataset, marginal_array   = get_total_biomass_potential(
                shapefile, time_period, climate_model, RCP, water_supply_future, input_level, water_supply_2010
            )
            
            # Total Land
            biomass_potentials_total.append(total_energy_potential.attrs['net_energy_potential'])
            arrays_total[(RCP, time_period)] = total_energy_potential.attrs['final_energy_array']
            
            # Marginal Land
            biomass_potentials_marg.append(np.nansum(marginal_array))
            xarrays_marg[(RCP, time_period)] = marginal_dataset
            final_potentials_marg[(RCP, time_period)] = marginal_array
            
            # Cropland
            potential_value = cropland_dataset.attrs['net_sum in PJ']
            biomass_potentials_crop.append(potential_value)
            xarrays_crop[(RCP, time_period)] = cropland_dataset
            

        # Assign the corresponding color from the Google logo to each time period
        color = colors[i % len(colors)]
        fig_crop.add_trace(go.Bar(x=time_periods, y=biomass_potentials_crop, name=RCP, marker_color=color))
        fig_marg.add_trace(go.Bar(x=time_periods, y=biomass_potentials_marg, name=RCP))
        fig_total.add_trace(go.Bar(x=time_periods, y=biomass_potentials_total, name=RCP))

    fig_total.update_layout(
        barmode='group',
        xaxis_title='Time Periods',
        yaxis_title='Biomass Energy Potential from Total Land',
        title='Total Biomass Energy Potential from different RCPs in Time Periods'
    )

    fig_crop.update_layout(
        barmode='group',
        xaxis_title='Years',
        yaxis_title='Biomass Energy Potential from Cropland Land',
        title='Cropland Biomass Energy Potential from different RCPs'
    )
    
    fig_marg.update_layout(
        barmode='group',
        xaxis_title='Time Periods',
        yaxis_title='Biomass Energy Potential from Marginal Land',
        title='Marginal Land Biomass Energy Potential from different RCPs in Time Periods'
    )
    
    fig_crop.show()
    fig_marg.show()
    fig_total.show()

    
    return fig_crop, fig_marg , fig_total , xarrays_marg , xarrays_crop , final_potentials_marg , arrays_total


# In[ ]:




