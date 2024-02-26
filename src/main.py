import pandas as pd
from utils import convert_to_eur, calculate_fees
from pathlib import Path

# Path to the data directory from the src directory
data_dir_path = '../data/'

# Define the base directory
base_dir = Path(__file__).parent.parent

# Define the output directory path
output_dir = base_dir / 'output'

# Ensure the output directory exists, create if it doesn't
output_dir.mkdir(exist_ok=True)

# Load data from Excel files
orders_df = pd.read_excel(data_dir_path + 'test-orders.xlsx')
affiliates_df = pd.read_excel(data_dir_path + 'test-affiliate-rates.xlsx')
currency_rates_df = pd.read_excel(data_dir_path + 'test-currency-rates.xlsx')

# Clean the data
## Remove duplicates
orders_df.drop_duplicates(inplace=True)
affiliates_df.drop_duplicates(inplace=True)
currency_rates_df.drop_duplicates(inplace=True)

# Convert 'Affiliate ID' column to string type to handle mixed types
orders_df['Affiliate ID'] = orders_df['Affiliate ID'].astype(str)

# Replace 'none', 'None', 'NONE', etc., with pd.NA
orders_df['Affiliate ID'].replace(to_replace='[Nn]one', value=pd.NA, regex=True, inplace=True)

# Additionally, replace 'nan' strings with pd.NA
# This is necessary because the conversion to string type can turn actual NaN values into 'nan' strings
orders_df['Affiliate ID'].replace('nan', pd.NA, inplace=True)

# Drop rows where 'Affiliate ID' is now pd.NA (covers None, NaN, "none" variations, and 'nan' strings)
filtered_orders = orders_df.dropna(subset=['Affiliate ID']).copy()

# Convert 'Affiliate ID' in both DataFrames to string
filtered_orders['Affiliate ID'] = filtered_orders['Affiliate ID'].astype(str).str.replace('.0', '', regex=False)
affiliates_df['Affiliate ID'] = affiliates_df['Affiliate ID'].astype(str).str.replace('.0', '', regex=False)

# Define a mapping of typos or variations to standard currency codes
currency_mapping = {
    'EURO': 'EUR',  # Map 'EURO' to 'EUR'
}

# Use the replace() function to correct these typos in the 'Currency' column
filtered_orders.loc[:, 'Currency'] = filtered_orders['Currency'].replace(currency_mapping)

# Convert 'Affiliate ID' in both DataFrames to string
filtered_orders['Affiliate ID'] = filtered_orders['Affiliate ID'].astype(str)
affiliates_df['Affiliate ID'] = affiliates_df['Affiliate ID'].astype(str)

# Ensure 'Start Date' is in datetime format in affiliates_df
affiliates_df['Start Date'] = pd.to_datetime(affiliates_df['Start Date'])


# Convert "Order Amount" to EUR
## First, make sure the 'date' columns are in datetime format
filtered_orders.loc[:, 'Order Date'] = pd.to_datetime(filtered_orders['Order Date'])
currency_rates_df['date'] = pd.to_datetime(currency_rates_df['date'])

## Perform currency conversion
filtered_orders.loc[:, 'Order Amount EUR'] = filtered_orders.apply(convert_to_eur, axis=1, rates_df=currency_rates_df)

# Calculate fees for each order
affiliates_df['Start Date'] = pd.to_datetime(affiliates_df['Start Date'])
affiliates_df = affiliates_df.sort_values(by=['Affiliate ID', 'Start Date'])


# Apply the calculate_fees function to calculate fees
fee_columns = filtered_orders.apply(lambda row: calculate_fees(row, affiliates_df), axis=1)
fee_columns.columns = ['Processing Fee', 'Refund Fee', 'Chargeback Fee']

# Concatenate the original filtered_orders DataFrame with the new fee columns
filtered_orders_with_fees = pd.concat([filtered_orders, fee_columns], axis=1)

# Calculate the start of the week for each order
filtered_orders_with_fees['Week Start'] = filtered_orders_with_fees['Order Date'] - pd.to_timedelta(filtered_orders_with_fees['Order Date'].dt.dayofweek, unit='D')

# Aggregate data by 'Affiliate ID' and 'Week Start'
weekly_aggregated = filtered_orders_with_fees.groupby(['Affiliate ID', 'Week Start']).agg(
    Number_of_Orders=('Order Number', 'count'),
    Total_Order_Amount_EUR=('Order Amount EUR', 'sum'),
    Total_Processing_Fee=('Processing Fee', 'sum'),
    Total_Refund_Fee=('Refund Fee', 'sum'),
    Total_Chargeback_Fee=('Chargeback Fee', 'sum')
).reset_index()

# Format the 'Week Start' to the desired string format, e.g., "01-10-2023 - 07-10-2023"
weekly_aggregated['Week'] = weekly_aggregated['Week Start'].dt.strftime('%d-%m-%Y') + ' - ' + (weekly_aggregated['Week Start'] + pd.Timedelta(days=6)).dt.strftime('%d-%m-%Y')

# Ensure 'Affiliate ID' in affiliates_df is the same type as in filtered_orders_with_fees
affiliates_df['Affiliate ID'] = affiliates_df['Affiliate ID'].astype(str)

for affiliate_id, data in weekly_aggregated.groupby('Affiliate ID'):
    # Find affiliate name using affiliate_id
    affiliate_name = affiliates_df.loc[affiliates_df['Affiliate ID'] == affiliate_id, 'Affiliate Name'].iloc[0]

    # Define the Excel filename using the affiliate name, saved in the output directory
    filename = output_dir / f"{affiliate_name}.xlsx"

    # Select the columns to include in the Excel report
    report_columns = ['Week', 'Number_of_Orders', 'Total_Order_Amount_EUR', 'Total_Processing_Fee', 'Total_Refund_Fee',
                      'Total_Chargeback_Fee']

    # Save the affiliate's weekly data to an Excel file
    data[report_columns].to_excel(filename, index=False)

