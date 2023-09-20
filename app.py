from flask import Flask, render_template, request, make_response
from Functions import shapefile_generator, graph_plotter_cropland, graph_plotter_marginal_new, bokeh_plot
import pandas as pd
from flask import send_file
import io
import json
import xarray as xr


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    # Read the country and province data from the CSV file
    df = pd.read_csv("Countries&Provinces.csv")
    countries = df["NAME_0"].unique().tolist()

    # Convert the provinces dictionary values from ndarray to list
    provinces = df.groupby("NAME_0")["NAME_1"].unique().to_dict()
    provinces = {country: provinces[country].tolist() for country in provinces}

    if request.method == 'POST':
        country = request.form['country']
        province = request.form['province']
        water_supply_future = request.form['water_supply_future']
        climate_model = request.form['climate_model']
        input_level = request.form['input_level']

        gdf = shapefile_generator(country, province)
        if gdf is None:
            return "Invalid country or province"

        plot_type = request.form.get('plot_type')  # Retrieve the selected plot type

        if plot_type == 'cropland':
            graph_html, xarrays = graph_plotter_cropland(gdf, climate_model, water_supply_future, input_level)
            bokeh_plots = {key: bokeh_plot(gdf, xarrays[key]['combined'].values) for key in xarrays}

        elif plot_type == 'marginal':
            graph_html, xarrays, final_potentials = graph_plotter_marginal_new(gdf, climate_model, water_supply_future, input_level)
            bokeh_plots = {key: bokeh_plot(gdf, final_potentials[key]) for key in xarrays}

        else:
            return "Invalid plot type"
        
        xarrays_dict = {str(key): value.to_dict() for key, value in xarrays.items()}  # Convert xarrays to a dictionary of dictionaries


        return render_template('calculator.html', graph_html=graph_html, xarrays_json=json.dumps(xarrays_dict), countries=countries, provinces=provinces, bokeh_plots=bokeh_plots)

    return render_template('calculator.html', countries=countries, provinces=provinces, graph_html=None)

@app.route('/download_xarray', methods=['POST'])
def download_xarray():
    try:
        # Retrieve the xarray data from the form (you may need to pass this data from the previous route)
        xarray_data_json = request.form['xarray_data']
        
        # Convert the JSON string back to a dictionary
        xarrays_dict = json.loads(xarray_data_json)
        
        for key, data_dict in xarrays_dict.items():
            print(f"Key: {key}")
            
        
        reconstructed_xarrays = {}
        for key, data_dict in xarrays_dict.items():
            key_tuple = eval(key)
            coords = {}
            for coord_name, coord_info in data_dict['coords'].items():
                coords[coord_name] = xr.DataArray(coord_info['data'], dims=coord_info['dims'], attrs=coord_info['attrs'])
    
            data_vars = {}
            for data_var_name, data_var_info in data_dict['data_vars'].items():
                data_vars[data_var_name] = xr.DataArray(data_var_info['data'], dims=data_var_info['dims'], attrs=data_var_info['attrs'])
    
            reconstructed_xarrays[key_tuple] = xr.Dataset(data_vars=data_vars, coords=coords, attrs=data_dict['attrs'])

        
            print("Reconstructed xarrays:", reconstructed_xarrays)  # Print the reconstructed Xarray data
    
        netcdf_file = io.BytesIO()

        # List to store the filenames of the saved NetCDF files
        filenames = []

        # Loop through the reconstructed xarrays and save them to NetCDF files
        for key, xarray_obj in reconstructed_xarrays.items():
            # Create a unique filename for each NetCDF file
            filename = f'biomass_potentials_{key}.nc'
            filenames.append(filename)
            
            # Convert the xarray object to NetCDF format and save it to a file
            xarray_obj.to_netcdf(filename, format='NETCDF4')

        # Provide links to download each NetCDF file
        download_links = []
        for filename in filenames:
            download_link = f'<a href="{filename}" download>{filename}</a><br>'
            download_links.append(download_link)

        return "Click the links below to download the NetCDF files:<br>" + "\n".join(download_links)
    except Exception as e:
        print("Error:", e)
        return "An error occurred while processing the download request."
    
@app.route('/submit', methods=['POST'])
def submit():
    return home()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')