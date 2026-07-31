from flask import Flask, render_template, jsonify, request
import joblib
import pandas as pd

app = Flask(__name__)

# Model aur feature columns load karo (ek hi baar, server start hote hi)
model = joblib.load('model/rul_model.pkl')
feature_columns = joblib.load('model/feature_columns.pkl')

# Test data load karo
test_data = pd.read_csv('data/test_last.csv')


@app.route('/')
def home():
    engine_ids = sorted(test_data['unit_nr'].unique().tolist())
    return render_template('index.html', engine_ids=engine_ids)


@app.route('/predict/<int:engine_id>')
def predict(engine_id):
    engine_data = test_data[test_data['unit_nr'] == engine_id].sort_values('time_cycles')

    if engine_data.empty:
        return jsonify({'error': 'Engine not found'}), 404

    last_row = engine_data.iloc[[-1]]
    X = last_row[feature_columns]

    predicted_rul = float(model.predict(X)[0])

    if predicted_rul < 30:
        status = "critical"
        message = "Maintenance jald zaroori hai"
    elif predicted_rul < 80:
        status = "warning"
        message = "Monitor karo"
    else:
        status = "healthy"
        message = "Engine healthy hai"

    sensor_trend = {
        'cycles': engine_data['time_cycles'].tolist(),
        'T24': engine_data['T24'].tolist(),
        'T50': engine_data['T50'].tolist(),
        'Ps30': engine_data['Ps30'].tolist(),
        'Nc': engine_data['Nc'].tolist()
    }

    return jsonify({
        'engine_id': engine_id,
        'predicted_rul': round(predicted_rul, 1),
        'status': status,
        'message': message,
        'current_cycle': int(last_row['time_cycles'].values[0]),
        'sensor_trend': sensor_trend
    })


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
