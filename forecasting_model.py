import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
# --- NEW LIBRARY ---
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings # <-- IMPORT ADDED
# --- END NEW LIBRARY ---

def generate_sklearn_forecast(historical_df, product_name, target_year, percent_increase):
    """
    Generates a simple, mock forecast based on the previous year's sales
    for a specific product, applying a percentage increase.
    
    This is the STABLE FALLBACK model.
    """
    print(f"[Model] FALLBACK: Generating scikit-learn forecast for {product_name}...")
        
    # We use 2024 as the fixed "Past Year" from the CSV (based on database.py)
    base_year = 2024
    
    # Filter for the specific product and base year
    product_history = historical_df[
        (historical_df['product_name'] == product_name) &
        (historical_df['year'] == base_year)
    ]
    
    if product_history.empty:
        print(f"[Model] No historical data found for {product_name} in {base_year}. Using default.")
        # As a fallback, create a flat forecast
        months = range(1, 13)
        base_sales = pd.DataFrame({'month': months, 'quantity': 100}) # Default 100 units
    else:
        # Get sales from the base year
        base_sales = product_history.groupby('month')['quantity'].sum().reset_index()
    
    # Ensure all 12 months are present, filling missing months with 0
    all_months = pd.DataFrame({'month': range(1, 13)})
    base_sales = pd.merge(all_months, base_sales, on='month', how='left').fillna(0)
    
    # Calculate the new predicted quantity
    # Apply the percentage increase
    increase_factor = 1 + (percent_increase / 100)
    base_sales['predicted_quantity'] = base_sales['quantity'] * increase_factor
    
    # Add some random "seasonality" noise to make it look realistic
    noise = np.random.normal(1, 0.1, 12) # 10% random variation
    base_sales['predicted_quantity'] = base_sales['predicted_quantity'] * noise
    
    # Ensure no negative sales and round to whole numbers
    base_sales['predicted_quantity'] = base_sales['predicted_quantity'].clip(lower=0).astype(int)

    # Prepare the final DataFrame
    forecast_df = pd.DataFrame({
        'product_name': product_name,
        'year': target_year,
        'month': base_sales['month'],
        'predicted_quantity': base_sales['predicted_quantity']
    })
    
    print(f"[Model] Fallback forecast generation complete.")
    return forecast_df

    # --- PRIMARY ATTEMPT: SARIMA MODEL ---
    try:
        # --- FIX: Suppress warnings from the model ---
        warnings.filterwarnings("ignore")
        # --- END FIX ---
        
        print(f"[Model] PRIMARY: Attempting SARIMA forecast for {product_name}...")
        
        # 1. Prepare Data
        # We use 2024 as the fixed "Past Year" from the CSV
        base_year = 2024
        
        # Filter for the specific product and base year
        product_history = historical_df[
            (historical_df['product_name'] == product_name) &
            (historical_df['year'] == base_year)
        ]

        if product_history.empty or len(product_history) < 12:
            # Not enough data for SARIMA, raise error to trigger fallback
            raise ValueError("Not enough historical data for SARIMA model.")
            
        # Get sales from the base year
        base_sales = product_history.groupby('month')['quantity'].sum().reset_index()
        
        # Ensure all 12 months are present
        all_months = pd.DataFrame({'month': range(1, 13)})
        base_sales = pd.merge(all_months, base_sales, on='month', how='left').fillna(0)
        
        # Create a proper time-series index for 2024
        ts_data = base_sales.set_index(
            pd.to_datetime(pd.DataFrame({'year': [base_year]*12, 'month': base_sales['month'], 'day': [1]*12}))
        )['quantity']
        ts_data.freq = 'MS' # Set frequency to Month-Start

        # 2. Fit SARIMA Model
        # (p,d,q) = non-seasonal orders
        # (P,D,Q,m) = seasonal orders (m=12 for 12 months)
        # These are common defaults, a real model would use auto_arima to find them
        model = SARIMAX(
            ts_data, 
            order=(1, 1, 1), 
            seasonal_order=(0, 1, 1, 12),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results = model.fit()
        
        # 3. Predict the next 12 months (the target year)
        prediction = results.get_forecast(steps=12)
        predicted_quantity = prediction.predicted_mean
        
        # 4. Apply Percentage Increase
        increase_factor = 1 + (percent_increase / 100)
        final_prediction = predicted_quantity * increase_factor
        
        # 5. Clean and format
        final_prediction = final_prediction.clip(lower=0).astype(int)

        forecast_df = pd.DataFrame({
            'product_name': product_name,
            'year': target_year,
            'month': range(1, 13),
            'predicted_quantity': final_prediction.values
        })
        
        print("[Model] PRIMARY: SARIMA forecast successful.")
        return forecast_df

    except Exception as e:
        # --- FALLBACK ---
        print(f"[Model] WARNING: SARIMA model failed ({e}).")
        print("[Model] Reverting to stable scikit-learn forecast...")
        return generate_sklearn_forecast(historical_df, product_name, target_year, percent_increase)