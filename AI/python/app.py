from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
import os
from flask import send_file
from ml_model import load_and_train

app = Flask(__name__)
CORS(app)

# Paths
DATA_CSV = "customer_info.csv"
PRODUCTS_CSV = "products.csv"
ACCURACY_PNG = "accuracy_plot.png"


def ensure_products_file():
    if not os.path.exists(PRODUCTS_CSV):
        dfp = pd.DataFrame(columns=["product_id", "name", "price", "cost"])
        dfp.to_csv(PRODUCTS_CSV, index=False)


# initial ensure
ensure_products_file()

# Global training state for frontend progress
training_state = {
    "status": "idle",
    "epoch": 0,
    "total_epochs": 0,
    "percent": 0
}

# initial training
state = load_and_train()


@app.route("/mappings", methods=["GET"])
def get_mappings():
    enc = state["encoders"]
    mappings = {}
    for col in ["gender", "region", "loyalty_tier"]:
        le = enc[col]
        mappings[col] = {str(i): name for i, name in enumerate(le.classes_)}
    mappings["segment"] = {str(i): name for i, name in state["segment_mapping"].items()}
    return jsonify(mappings)


@app.route("/training-status", methods=["GET"])
def get_training_status():
    return jsonify(training_state)


@app.route("/retrain", methods=["POST"])
def retrain_model():
    global state, training_state
    data = request.get_json()
    epochs = int(data.get("epochs", 8))

    training_state["status"] = "training"
    training_state["total_epochs"] = epochs
    training_state["epoch"] = 0
    training_state["percent"] = 0

    state = load_and_train(epochs=epochs, progress_callback_dict=training_state)

    training_state["status"] = "completed"
    training_state["percent"] = 100
    return jsonify({
        "message": "Model retrained and data reloaded successfully",
        "validation_accuracy": round(state['history'].history['val_accuracy'][-1] * 100, 2)
    })


@app.route("/analyze", methods=["GET"])
def analyze_customers():
    df = state["df"]
    segment_counts = df["customer_segment"].value_counts().to_dict()
    # Simulate sales per customer based on loyalty_tier (for analytics)
    # Assign average purchase values per encoded loyalty tier
    # Map back loyalty tier names via encoder
    le_loyal = state["encoders"]["loyalty_tier"]
    loyalty_names = {i: name for i, name in enumerate(le_loyal.classes_)}

    # create a synthetic sale amount column if not present
    if "purchase_amount" not in df.columns:
        # assign mean amounts for tiers: gold:200, silver:120, bronze:60
        tier_map = {}
        for idx, name in loyalty_names.items():
            n = name.lower()
            if "gold" in n:
                tier_map[idx] = 200
            elif "silver" in n:
                tier_map[idx] = 150
            elif "bronze" in n:
                tier_map[idx] = 100
            elif "iron" in n:
                tier_map[idx] = 75
            else:
                tier_map[idx] = 50
        df["purchase_amount"] = df["loyalty_tier"].map(tier_map)

    # Sales by region
    sales_by_region = df.groupby("region")["purchase_amount"].sum().to_dict()
    # Loyalty tier sales by region and gender
    loyalty_region_gender = df.groupby(["region", "loyalty_tier", "gender"])['purchase_amount'].sum().reset_index().to_dict(orient='records')

    # Loyalty tier counts
    loyalty_counts = df["loyalty_tier"].value_counts().to_dict()

    # Gender and region counts
    gender_counts = df["gender"].value_counts().to_dict()
    region_counts = df["region"].value_counts().to_dict()

    # Get query params for pagination and filters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    loyalty_filter = request.args.get('loyalty_filter', '')
    gender_filter = request.args.get('gender_filter', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    search = request.args.get('search', '')

    # Filter df for customers
    filtered_df = df.copy()
    if loyalty_filter:
        le_loyal = state["encoders"]["loyalty_tier"]
        loyalty_encoded = le_loyal.transform([loyalty_filter])[0]
        filtered_df = filtered_df[filtered_df["loyalty_tier"] == loyalty_encoded]
    if gender_filter:
        le_gen = state["encoders"]["gender"]
        gender_encoded = le_gen.transform([gender_filter])[0]
        filtered_df = filtered_df[filtered_df["gender"] == gender_encoded]
    if from_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["signup_date"], format='%d-%m-%y', errors='coerce') >= pd.to_datetime(from_date)]
    if to_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["signup_date"], format='%d-%m-%y', errors='coerce') <= pd.to_datetime(to_date)]
    if search:
        filtered_df = filtered_df[filtered_df["customer_id"].str.contains(search, case=False, na=False) |
                                  filtered_df["email"].str.contains(search, case=False, na=False)]

    # Paginate
    total_customers = len(filtered_df)
    start = (page - 1) * limit
    end = start + limit
    paginated_df = filtered_df.iloc[start:end]

    sample_customers = paginated_df[[
        "customer_id", "email", "signup_date", "gender", "region", "loyalty_tier", "customer_segment"
    ]].to_dict(orient="records")
    # Handle signup_date and NaN
    for c in sample_customers:
        if pd.isna(c['signup_date']):
            c['signup_date'] = 'N/A'
        elif isinstance(c['signup_date'], pd.Timestamp):
            c['signup_date'] = c['signup_date'].strftime('%Y-%m-%d')
        c['customer_segment'] = state["segment_mapping"].get(c['customer_segment'], c['customer_segment'])

    # Convert dict keys to str to avoid sorting issues in jsonify
    segment_counts = {str(k): v for k, v in segment_counts.items()}
    sales_by_region = {str(k): v for k, v in sales_by_region.items()}
    loyalty_counts = {str(k): v for k, v in loyalty_counts.items()}
    gender_counts = {str(k): v for k, v in gender_counts.items()}
    region_counts = {str(k): v for k, v in region_counts.items()}

    return jsonify({
        "message": "Customer analysis completed successfully",
        "segment_distribution": segment_counts,
        "sales_by_region": sales_by_region,
        "loyalty_region_gender": loyalty_region_gender,
        "loyalty_counts": loyalty_counts,
        "gender_counts": gender_counts,
        "region_counts": region_counts,
        "sample_customers": sample_customers,
        "total_customers": total_customers,
        "page": page,
        "limit": limit
    })


@app.route("/future-prediction", methods=["POST"])
def future_prediction():
    """
    Predict customer segment for new customer
    Input JSON:
    {
        "gender": "male",
        "region": "north",
        "loyalty_tier": "gold"
    }
    """
    data = request.get_json()
    # Expecting gender, region, loyalty_tier
    input_df = pd.DataFrame([data])
    # apply encoders
    enc = state["encoders"]
    for col in ["gender", "region", "loyalty_tier"]:
        le = enc[col]
        # handle unknown labels by adding to classes (fallback)
        val = str(input_df.loc[0, col]).lower().strip()
        if val not in le.classes_:
            # extend classes
            le.classes_ = np.append(le.classes_, val)
        input_df[col] = le.transform([val])

    # predict using model
    model = state["model"]
    pred = model.predict(input_df[["gender", "region", "loyalty_tier"]].values)
    predicted_segment = int(np.argmax(pred))

    # compute simple estimated sale based on loyalty tier mapping
    loyalty_le = state["encoders"]["loyalty_tier"]
    tier_name = loyalty_le.inverse_transform([int(input_df.loc[0, 'loyalty_tier'])])[0]
    tier_name = str(tier_name).lower()
    if "gold" in tier_name:
        est_sale = 200
    elif "silver" in tier_name:
        est_sale = 150
    elif "bronze" in tier_name:
        est_sale = 100
    elif "iron" in tier_name:
        est_sale = 75
    else:
        est_sale = 50

    return jsonify({
        "message": "Prediction completed",
        "predicted_segment": predicted_segment,
        "estimated_sale": est_sale
    })


@app.route("/accuracy-plot", methods=["GET"])
def get_accuracy_plot():
    if os.path.exists(ACCURACY_PNG):
        return send_file(ACCURACY_PNG, mimetype='image/png')
    return jsonify({"error": "Plot not available"}), 404


@app.route("/add-customer", methods=["POST"])
def add_customer():
    """
    Accepts JSON: email, signup_date, gender, region, loyalty_tier
    Appends to in-memory df, predicts segment, updates analytics without saving to CSV
    """
    payload = request.get_json()
    required = ["email", "signup_date", "gender", "region", "loyalty_tier"]
    for r in required:
        if r not in payload:
            return jsonify({"error": f"Missing field {r}"}), 400

    # generate new customer id
    df = state["df"]
    # find max numeric part
    def max_id(df):
        try:
            nums = df['customer_id'].dropna().str.replace(r'[^0-9]', '', regex=True).astype(int)
            return nums.max()
        except Exception:
            return 0

    mx = max_id(df) or 0
    new_num = mx + 1
    new_cid = f"C{str(new_num).zfill(5)}"

    # normalize the input
    new_row = {
        'customer_id': new_cid,
        'email': payload.get('email',''),
        'signup_date': pd.to_datetime(payload.get('signup_date',''), errors='coerce'),
        'gender': str(payload.get('gender','')).strip().title(),
        'region': str(payload.get('region','')).strip().title(),
        'loyalty_tier': str(payload.get('loyalty_tier','')).strip().title()
    }

    # append to in-memory df
    new_df = pd.DataFrame([new_row])

    # encode for prediction
    enc = state['encoders']
    for col in ["gender", "region", "loyalty_tier"]:
        le = enc[col]
        val = new_row[col]
        if val not in le.classes_:
            # handle new category
            le.classes_ = np.append(le.classes_, val)
        new_df[col] = le.transform([val])

    state["df"] = pd.concat([df, new_df], ignore_index=True)

    # predict segment
    model = state['model']
    pred = model.predict(new_df[["gender", "region", "loyalty_tier"]].values)
    predicted_segment = int(np.argmax(pred))
    
    # Save the predicted segment to the main dataframe so charts update
    state["df"].loc[state["df"].index[-1], "customer_segment"] = predicted_segment

    predicted_segment_name = state["segment_mapping"].get(predicted_segment, f"Segment {predicted_segment}")

     # Recalculate loyalty tier sales prediction
    df = state["df"]
    # create a synthetic sale amount column if not present
    le_loyal = state["encoders"]["loyalty_tier"]
    loyalty_names = {i: name for i, name in enumerate(le_loyal.classes_)}
    tier_map = {}
    for idx, name in loyalty_names.items():
        n = name.lower()
        if "gold" in n:
            tier_map[idx] = 200
        elif "silver" in n:
            tier_map[idx] = 150
        elif "bronze" in n:
            tier_map[idx] = 100
        elif "iron" in n:
            tier_map[idx] = 75
        else:
            tier_map[idx] = 50
    df["purchase_amount"] = df["loyalty_tier"].map(tier_map)

    return jsonify({
        'message': 'Customer added to memory',
        'customer_id': new_cid,
        'prediction': {'predicted_segment': predicted_segment_name},
        'validation_accuracy': round(state['history'].history['val_accuracy'][-1] * 100, 2)
    })


def future_prediction_internal(data):
    # helper to predict a dict input
    input_df = pd.DataFrame([data])
    enc = state['encoders']
    for col in ["gender", "region", "loyalty_tier"]:
        le = enc[col]
        val = str(input_df.loc[0, col]).lower().strip()
        if val not in le.classes_:
            le.classes_ = np.append(le.classes_, val)
        input_df[col] = le.transform([val])
    model = state['model']
    pred = model.predict(input_df[["gender", "region", "loyalty_tier"]].values)
    predicted_segment = int(np.argmax(pred))
    return {'predicted_segment': predicted_segment}


@app.route('/products', methods=['GET', 'POST'])
def products():
    ensure_products_file()
    if request.method == 'GET':
        dfp = pd.read_csv(PRODUCTS_CSV)
        # compute profit/loss
        if not dfp.empty:
            dfp['profit'] = dfp['price'].astype(float) - dfp['cost'].astype(float)
        return jsonify(dfp.to_dict(orient='records'))
    else:
        payload = request.get_json()
        required = ['name','price','cost']
        for r in required:
            if r not in payload:
                return jsonify({'error': f'Missing {r}'}), 400
        dfp = pd.read_csv(PRODUCTS_CSV)
        # product id
        pid = f"P{str(len(dfp)+1).zfill(4)}"
        new = {'product_id': pid, 'name': payload['name'], 'price': payload['price'], 'cost': payload['cost']}
        dfp = pd.concat([dfp, pd.DataFrame([new])], ignore_index=True)
        dfp.to_csv(PRODUCTS_CSV, index=False)
        return jsonify({'message':'product added', 'product': new})


@app.route('/product-prediction', methods=['GET'])
def product_prediction():
    df = state["df"]
    le_loyal = state["encoders"]["loyalty_tier"]
    loyalty_names = {i: name for i, name in enumerate(le_loyal.classes_)}

    # Define tier values for sales estimation
    tier_map = {}
    for idx, name in loyalty_names.items():
        n = str(name).lower()
        if "gold" in n:
            tier_map[idx] = 200
        elif "silver" in n:
            tier_map[idx] = 150
        elif "bronze" in n:
            tier_map[idx] = 100
        elif "iron" in n:
            tier_map[idx] = 75
        else:
            tier_map[idx] = 50

    # Calculate sales share per tier based on current data
    sales_series = df["loyalty_tier"].map(tier_map)
    sales_by_tier = sales_series.groupby(df["loyalty_tier"]).sum()
    total_sales = sales_by_tier.sum()

    predictions = []
    for idx, name in loyalty_names.items():
        tier_total = sales_by_tier.get(idx, 0)
        if total_sales > 0:
            percent = (tier_total / total_sales) * 100
        else:
            percent = 0

        predictions.append({
            'name': name,
            'prediction': round(percent, 2),
        })
    return jsonify(predictions)


if __name__ == "__main__":
    app.run(debug=True)
