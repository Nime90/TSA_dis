import streamlit as st
import pandas as pd
from scipy.stats import linregress
import statistics
import matplotlib.pyplot as plt
from io import BytesIO

# Set up the Streamlit page
st.title("Time Series Analysis: Manual Method")
st.write("Remember: in order for this script to work, you need to have always a column called 'Year' and one column called either 'Month' or 'Quarter'. ")
st.write("Please check that the column where to get the real data, needs to be the last column in your file. ")

# Upload file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])
if uploaded_file:
    # Read Excel file structure to get sheet names
    excel_file = pd.ExcelFile(uploaded_file)
    sheet_names = excel_file.sheet_names
    
    # Let user select a sheet if there are multiple tabs
    if len(sheet_names) > 1:
        selected_sheet = st.selectbox("Select sheet/tab:", sheet_names)
    else:
        selected_sheet = sheet_names[0]
        st.info(f"Automatically selected the only available sheet: **{selected_sheet}**")
        
    data = pd.read_excel(excel_file, sheet_name=selected_sheet)
    Col_to_pred = data.columns[-1]
    
    # Select the prediction period
    period = st.selectbox("Select period:", ["Quarter" , "Month"])

    t = [i+1 for i in data.index]
    data['t'] = t
    data = data[['t', 'Year', period, Col_to_pred]]

    years_to_predict = st.number_input("Years to predict", min_value=1, max_value=10, value=None)
    if years_to_predict != None:
        period_to_predict = years_to_predict * 12 if period == 'Month' else years_to_predict * 4

        # Step 1: Finding Moving Averages
        Mv_avg = []
        for i in range(len(data[Col_to_pred])):
            if i < 2:
                Mv_avg.append(None)
            else:
                try:
                    sales_to_avg = [data[Col_to_pred][i-2], data[Col_to_pred][i-1], data[Col_to_pred][i], data[Col_to_pred][i+1]]
                    Mv_avg.append(float(statistics.mean(sales_to_avg)))
                except:
                    Mv_avg.append(None)

        CMv_avg = []
        for i in range(len(Mv_avg)):
            if i < 2:
                CMv_avg.append(None)
            else:
                try:
                    sales_to_avg = [Mv_avg[i], Mv_avg[i+1]]
                    CMv_avg.append(float(statistics.mean(sales_to_avg)))
                except:
                    CMv_avg.append(None)

        gap = []
        for i in range(len(data[Col_to_pred])):
            if i < 2:
                gap.append(None)
            else:
                try:
                    gap.append(float(data[Col_to_pred][i] / CMv_avg[i]))
                except:
                    gap.append(None)

        data['Moving_avg'] = Mv_avg
        data['Centered_Moving_avg'] = CMv_avg
        data['gap_sales_cma'] = gap

        # Creating empty rows for future predictions safely
        empty_rows = pd.DataFrame(index=range(period_to_predict), columns=data.columns)
        empty_rows['t'] = range(int(data['t'].max()) + 1, int(data['t'].max()) + 1 + period_to_predict)

        if period == 'Quarter':
            for i in range(len(empty_rows)):
                if i < 4:
                    empty_rows.loc[i, 'Year'] = int(data['Year'].max()) + 1
                    empty_rows.loc[i, 'Quarter'] = data['Quarter'].iloc[i]
                else:
                    empty_rows.loc[i, 'Year'] = int(empty_rows.loc[i-4, 'Year']) + 1
                    empty_rows.loc[i, 'Quarter'] = empty_rows.loc[i-4, 'Quarter']
        elif period == 'Month':
            for i in range(len(empty_rows)):
                if i < 12:
                    empty_rows.loc[i, 'Year'] = int(data['Year'].max()) + 1
                    empty_rows.loc[i, 'Month'] = data['Month'].iloc[i]
                else:
                    empty_rows.loc[i, 'Year'] = int(empty_rows.loc[i-12, 'Year']) + 1
                    empty_rows.loc[i, 'Month'] = empty_rows.loc[i-12, 'Month']

        data = pd.concat([data, empty_rows]).reset_index(drop=True)

        # Calculating Seasonal Factors
        Seas_factor = data[[period, 'gap_sales_cma']].groupby(period).mean().reset_index()
        Seas_factor.columns = [period, 'Seas_factor']
        data = pd.merge(data, Seas_factor, on=period, how='left').reset_index(drop=True)

        # Calculating Deseasonalized Sales
        Sales_des = []
        for i in range(len(data[Col_to_pred])):
            try:
                Sales_des.append(float(data[Col_to_pred][i] / data['Seas_factor'][i]))
            except:
                Sales_des.append(None)
        data[Col_to_pred+'_des'] = Sales_des

        # Computing Linear Trend
        x = [s for s in range(len(data[Col_to_pred+'_des'].dropna()))]
        y = [s for s in data[Col_to_pred+'_des'].dropna()]
        slope, intercept, r_value, p_value, std_err = linregress(x, y)

        # Applying Linear Trend
        Linear_trend = [intercept + slope * t for t in data.t]
        data['Linear_trend'] = Linear_trend

        # Making Predictions
        data['Predictions'] = data['Linear_trend'] * data['Seas_factor']

        # Plotting the Results
        plt.figure(figsize=(10, 5))
        plt.plot(data[Col_to_pred], label='Actual '+Col_to_pred, color='blue')
        plt.plot(data['Predictions'], label='Predicted values', color='red')
        plt.xlabel("Time")
        plt.ylabel(Col_to_pred)
        plt.title(Col_to_pred+" Predictions")
        plt.legend()

        # Display plot in Streamlit
        st.pyplot(plt)

        # Add download button for the modified dataset
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Predictions')
            return output.getvalue()

        excel_data = to_excel(data)
        st.download_button(label="Download predictions as Excel file",
                        data=excel_data,
                        file_name=Col_to_pred+"_predictions.xlsx",
                        mime="application/vnd.ms-excel")

        # Optionally, add a download button for the plot image
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        st.download_button(label="Download plot as PNG",
                        data=buffer,
                        file_name=Col_to_pred+"_predictions_plot.png",
                        mime="image/png")
else:
    st.write("Please upload a file to continue.")
