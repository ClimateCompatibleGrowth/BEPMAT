from flask import Flask, render_template, request, make_response
from Functions import shapefile_generator, graph_plotter_cropland, graph_plotter_marginal_new
import pandas as pd
import csv


app = Flask(__name__)

def xarray_to_csv(xarray):
    # Convert the xarray to a CSV string
    csv_string = xarray.to_csv(encoding='utf-8')
    return csv_string

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
        elif plot_type == 'marginal':
            graph_html, xarrays, final_potentials = graph_plotter_marginal_new(gdf, climate_model, water_supply_future, input_level)
        else:
            return "Invalid plot type"

        return render_template('calculator.html', graph_html=graph_html, xarrays=xarrays, countries=countries, provinces=provinces)

    return render_template('calculator.html', countries=countries, provinces=provinces, graph_html=None)

@app.route('/download_csv', methods=['POST'])
def download_csv():
    # Retrieve the xarrays from the form data
    xarray_str = request.form.get('xarrays')
    # Split the xarrays string into individual xarray CSV strings
    xarray_csv_list = xarray_str.split(';')

    # Create a response object with the CSV data
    response = make_response('\n'.join(xarray_csv_list))
    # Set the appropriate content type for CSV
    response.headers['Content-Type'] = 'text/csv'
    # Set the content disposition as attachment so that it downloads as a file
    response.headers['Content-Disposition'] = 'attachment; filename=xarrays.csv'

    return response

@app.route('/submit', methods=['POST'])
def submit():
    return home()


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
