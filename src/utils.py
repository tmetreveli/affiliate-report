import pandas as pd

def convert_to_eur(row, rates_df):
    date = row['Order Date']
    currency = row['Currency']
    amount = row['Order Amount']

    if currency == 'EUR':
        return amount
    rate = rates_df.loc[rates_df['date'] == date, currency].values[0]
    return amount / rate

## Define a function to find the correct affiliate rate
def find_affiliate_rate(row, affiliates_df):
    affiliate_id = row['Affiliate ID']
    order_date = row['Order Date']
    filtered_df = affiliates_df[(affiliates_df['Affiliate ID'] == affiliate_id) &
                                (affiliates_df['Start Date'] <= order_date)]
    if filtered_df.empty:
        # Handle the case where no matching affiliate rate is found, e.g., return None or a default rate
        return None  # Or you might want to return a DataFrame with default values
    else:
        # Return the most recent rate
        return filtered_df.iloc[-1]

def calculate_fees(row, affiliates_df):
    affiliate_rate = find_affiliate_rate(row, affiliates_df)

    # Handle the case where no affiliate rate is found
    if affiliate_rate is None:
        # Set default fees or skip calculation
        processing_fee = 0
        refund_fee = 0
        chargeback_fee = 0
    else:
        order_amount_eur = row['Order Amount EUR']
        processing_fee = order_amount_eur * affiliate_rate['Processing Rate']
        refund_fee = affiliate_rate['Refund Fee'] if row['Order Status'] == 'Refunded' else 0
        chargeback_fee = affiliate_rate['Chargeback Fee'] if row['Order Status'] == 'Chargeback' else 0
    return pd.Series([processing_fee, refund_fee, chargeback_fee])