import matplotlib
# --- CRITICAL FIX ---
# Set the backend *before* importing pyplot
# This prevents a crash/infinite loop when PySide6 is also imported.
matplotlib.use('Agg') 
# --- END FIX ---

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import warnings # <-- Import Added
from PySide6.QtWidgets import QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- Setup Seaborn Styling ---
sns.set_theme(
    style="whitegrid", 
    palette="deep",
    rc={
        "axes.edgecolor": ".8",
        "axes.labelcolor": ".3",
        "text.color": ".3",
        "xtick.color": ".5",
        "ytick.color": ".5",
        "figure.figsize": (8, 5)
    }
)
MONTH_NAMES = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

# --- Matplotlib Canvas Widget ---

class MatplotlibCanvas(FigureCanvas):
    """A custom PySide6 widget to embed a Matplotlib plot."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

# --- Helper Function (UPDATED) ---

def _apply_category_filter(df, category_filter, product_col_name='product_name'):
    """Helper to filter a DataFrame based on the category."""
    if df.empty:
        return df
        
    if category_filter == "P.E.":
        return df[df[product_col_name].str.startswith("P.E.")]
    elif category_filter == "Slip-on":
        return df[df[product_col_name].str.startswith("Slip-on")]
    elif category_filter == "All":
        return df
    # --- FINAL FIX ---
    # This else handles specific product names (like "P.E. - Black")
    # passed from the forecast plot
    else: 
        return df[df[product_col_name] == category_filter]
    # --- END FIX ---

def _get_monthly_data(df, category_filter, year_filter, value_column):
    """Helper to aggregate sales/target data by month for a specific category and year."""
    if df.empty:
        return pd.Series(index=range(1, 13), data=0, name=value_column)
        
    # Apply category filter
    df_filtered = _apply_category_filter(df, category_filter)
        
    # Apply year filter
    df_filtered = df_filtered[df_filtered['year'] == year_filter]
    
    # Group by month and sum the value column
    monthly_data = df_filtered.groupby('month')[value_column].sum()
    
    # Reindex to ensure all 12 months are present, filling missing with 0
    monthly_data = monthly_data.reindex(range(1, 13), fill_value=0)
    
    return monthly_data

# --- Plot 1: Sales vs Target (UPDATED) ---

def plot_sales_vs_target_yoy(axes, past_sales_df, current_sales_df, targets_df, category_filter, year_filter):
    """
    Plots a dynamic YOY sales vs. target comparison for the selected year and category.
    """
    axes.clear()
    
    try:
        # --- Get Data ---
        # 1. Past Year Sales (fixed to 2024 from CSV)
        past_sales = _get_monthly_data(past_sales_df, category_filter, 2024, 'quantity')
        
        # 2. Current Year Sales (dynamic based on year_filter)
        current_sales = _get_monthly_data(current_sales_df, category_filter, year_filter, 'quantity')
        
        # 3. Target Quantity (pairs) (dynamic based on year_filter)
        target_quantity = _get_monthly_data(targets_df, category_filter, year_filter, 'target_quantity')
        
        # 4. Target Increase (%) (dynamic based on year_filter)
        # Note: We saved Increase (%) in the 'quota' column
        # We take the mean for the category, as summing % makes no sense
        targets_filtered = _apply_category_filter(targets_df, category_filter)
        targets_filtered = targets_filtered[targets_filtered['year'] == year_filter]
        if targets_filtered.empty:
            target_increase = pd.Series(index=range(1, 13), data=0)
        else:
            target_increase = targets_filtered.groupby('month')['quota'].mean()
            target_increase = target_increase.reindex(range(1, 13), method='ffill').fillna(0)
        
        # --- Create Plot ---
        plot_df = pd.DataFrame({
            f'Past Sales ({past_sales.sum():,.0f})': past_sales,
            f'Current Sales ({current_sales.sum():,.0f})': current_sales,
            f'Target Qty ({target_quantity.sum():,.0f})': target_quantity,
        })
        
        # Plot the bars (Sales and Quota)
        plot_df.plot(kind='bar', ax=axes, width=0.8, 
                     color={"Past Sales": "#cce5ff", "Current Sales": "#66b0ff", "Target Qty": "#ffc107"})
        
        axes.set_title(f'YOY Sales vs. Targets for {category_filter} ({year_filter})', fontsize=12, weight='bold')
        axes.set_ylabel("Sales / Target (Units)", fontsize=10)
        axes.set_xlabel(None)
        
        # --- Add Second Y-Axis for Target Increase (%) ---
        ax2 = axes.twinx()
        ax2.plot(
            axes.get_xticks(), # Align with bar chart x-ticks
            target_increase, 
            color='#d9534f', # Red
            marker='o', 
            linestyle='--',
            label=f'Target Increase (%) (Avg: {target_increase.mean():.1f}%)'
        )
        ax2.set_ylabel("Target Increase (%)", fontsize=10, color='#d9534f')
        ax2.tick_params(axis='y', colors='#d9534f')
        ax2.grid(False) # Don't show grid for the second axis
        
        # Combine legends from both axes
        lines, labels = axes.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        axes.legend(lines + lines2, labels + labels2, loc='upper left', fontsize=8)
        
        # Format X-axis
        axes.set_xticks(range(12))
        axes.set_xticklabels(MONTH_NAMES, rotation=0)
        axes.ticklabel_format(style='plain', axis='y')
        ax2.ticklabel_format(style='plain', axis='y')
        
    except Exception as e:
        axes.text(0.5, 0.5, f"Error: {e}", ha='center', va='center', color='red')
        
    axes.figure.tight_layout()

# --- Plot 2: Historical Sales Summary (UPDATED) ---

def plot_historical_sales_summary(axes, past_sales_df, category_filter):
    """
    Plots a horizontal bar chart of total "Past Year" sales by product,
    filtered by the selected category.
    """
    axes.clear()
    
    if past_sales_df.empty:
        axes.text(0.5, 0.5, "No historical sales data imported.", ha='center', va='center')
        axes.set_title("Historical Sales Summary (from CSV)")
        return
        
    try:
        # Apply category filter
        df_filtered = _apply_category_filter(past_sales_df, category_filter)
        
        if df_filtered.empty:
            axes.text(0.5, 0.5, f"No historical data for {category_filter}.", ha='center', va='center')
            axes.set_title(f"Historical Sales Summary for {category_filter}")
            return

        # Group by product and sum quantity
        product_sales = df_filtered.groupby('product_name')['quantity'].sum().sort_values()
        
        # Plot
        product_sales.plot(kind='barh', ax=axes, color="#6c757d")
        
        axes.set_title(f"Historical Sales Summary for {category_filter}", fontsize=12, weight='bold')
        axes.set_xlabel("Total Units Sold")
        axes.set_ylabel("Product")
        
        # Add value labels
        for i, v in enumerate(product_sales):
            axes.text(v + 10, i, f"{v:,.0f}", va='center', fontsize=8, color='black')
            
    except Exception as e:
        axes.text(0.5, 0.5, f"Error: {e}", ha='center', va='center', color='red')

    axes.figure.tight_layout()
    
# --- Plot 3: Forecast vs Actual (UPDATED) ---

def plot_forecast_vs_actual_admin(axes, predictions_df, current_sales_df, category_filter, year_filter):
    """
    Plots the generated forecast vs. actual "Current Sales" for the selected year and category.
    """
    axes.clear()

    try:
        # --- Get Data ---
        # 1. Forecast Data (dynamic)
        forecast = _get_monthly_data(predictions_df, category_filter, year_filter, 'predicted_quantity')
        
        # 2. Actual "Current Sales" (dynamic)
        actual = _get_monthly_data(current_sales_df, category_filter, year_filter, 'quantity')

        # Check if data exists
        if forecast.sum() == 0 and actual.sum() == 0:
            axes.text(0.5, 0.5, f"No forecast or sales data for {category_filter}\nin {year_filter}.", 
                      ha='center', va='center', linespacing=1.5)
            axes.set_title(f"Forecast vs. Actual Sales ({year_filter})")
            return
            
        # --- Create Plot ---
        plot_df = pd.DataFrame({
            f'Predicted Sales ({forecast.sum():,.0f})': forecast,
            f'Actual Sales ({actual.sum():,.0f})': actual
        })
        
        plot_df.plot(kind='line', ax=axes, marker='o')
        
        axes.set_title(f'Forecast vs. Actual for {category_filter} ({year_filter})', fontsize=12, weight='bold')
        axes.set_ylabel("Units Sold")
        axes.set_xlabel(None)
        
        # Format X-axis
        axes.set_xticks(range(1, 13))
        axes.set_xticklabels(MONTH_NAMES)
        axes.ticklabel_format(style='plain', axis='y')
        axes.legend(loc='upper left', fontsize=8)
        
    except Exception as e:
        axes.text(0.5, 0.5, f"Error: {e}", ha='center', va='center', color='red')

    axes.figure.tight_layout()

# --- Plot 4: Top Selling (Current Year) (REMOVED) ---

# The plot_top_selling_products function has been removed.

# --- Plot 5: Forecast vs Actual (Employee/Admin Forecast Tab) ---

def plot_forecast_vs_actual(axes, historical_df, forecast_df, product_name):
    """
    Plots a specific product's forecast vs. its historical data.
    Used on the 'Generate Forecast' panel.
    """
    axes.clear()
    
    try:
        # Get historical data for the specific product (fixed to 2024)
        hist_data = _get_monthly_data(historical_df, product_name, 2024, 'quantity')
        
        # Get forecast data
        # The forecast_df is already filtered for the product and target year
        forecast_data = forecast_df.set_index('month')['predicted_quantity']
        forecast_data = forecast_data.reindex(range(1, 13), fill_value=0)
        
        target_year = forecast_df['year'].iloc[0]
        
        # Create Plot
        plot_df = pd.DataFrame({
            f'Historical (2024): {hist_data.sum():,.0f}': hist_data,
            f'Forecast ({target_year}): {forecast_data.sum():,.0f}': forecast_data
        })
        
        plot_df.plot(kind='line', ax=axes, marker='o', 
                     color={'Historical (2024)': '#6c757d', f'Forecast ({target_year})': '#0275d8'})
        
        axes.set_title(f'Forecast for {product_name}', fontsize=12, weight='bold')
        axes.set_ylabel("Units Sold")
        axes.set_xlabel(None)
        
        # Format X-axis
        axes.set_xticks(range(1, 13))
        axes.set_xticklabels(MONTH_NAMES)
        axes.ticklabel_format(style='plain', axis='y')
        axes.legend(loc='upper left', fontsize=8)
        
    except Exception as e:
        axes.text(0.5, 0.5, f"Error: {e}", ha='center', va='center', color='red')

    axes.figure.tight_layout()