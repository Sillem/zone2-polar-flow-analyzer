import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
import os
import json
import sys
import pprint

def calculate_cardiac_drift_in_bins(workout_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate the difference in heart rate on the same speeds in last quarter of the workout and the second quarter (fully warmed up).

    If the cardiac drift om some pace is:
        - <3bpm => Elite
        - 3-4bpm => Excellent
        - 4-6bpm => Good
        - 6-8bpm => Fair
        - Poor => >8

    If reached cardiac drift of some level, can extend the duration AND OR pace.

    Args:
        workout_data (pd.DataFrame): DataFrame with workout data from Polar Flow CSV
    """

    n = workout_data.shape[0]
    workout_data = workout_data[["HR (bpm)", "Speed (km/h)"]]
    # binning the speed into 0.5 km/h buckets
    workout_data[["Speed (km/h)"]] = (workout_data[["Speed (km/h)"]] // 0.5) * 0.5

    Q2 = workout_data.iloc[n//4:n//2, :]
    Q4 = workout_data.iloc[3 * n//4: , :]

    results = []
    # quarter analysis
    for quarter in [Q2, Q4]:
        avg_hr_quarter = quarter.groupby("Speed (km/h)").mean("HR (bpm)").rename(columns={'HR (bpm)' : 'HR (bpm) AVG'})
        std_dev_hr_quarter = quarter.groupby("Speed (km/h)")["HR (bpm)"].std().rename('HR (bpm) stddev')
        count_speed_bins_quarter = quarter.groupby("Speed (km/h)").count().rename(columns={'HR (bpm)' : 'bin_count'})
        quarter_results = avg_hr_quarter.join(count_speed_bins_quarter, on="Speed (km/h)").join(std_dev_hr_quarter)

        # based on the CTL we can assume that mean estimations converge to normal distribution so we construct Confidence Intervals
        # these will in turn allow us to estimate with 95% certainty where may real value lie, if the width is more than 1BPM then
        # how can we trust it to make good decision?
        quarter_results['conf_interval_95_width'] = 2 * stats.t.ppf(0.975, quarter_results['bin_count'] - 1) * (quarter_results['HR (bpm) stddev'] / quarter_results['bin_count']**0.5)
        
        # remove bins with unreliable sample size and variability too high
        quarter_results = quarter_results[(quarter_results['conf_interval_95_width'] < 1) & (quarter_results['bin_count'] > 25)]
        results.append(quarter_results)
    
    merged = results[0].join(results[1], lsuffix="_q2", rsuffix="_q4").dropna()
    merged['HR drift (BPM)'] = merged['HR (bpm) AVG_q4'] -  merged['HR (bpm) AVG_q2']
    merged['HR drift (%)'] = (merged['HR (bpm) AVG_q4'] -  merged['HR (bpm) AVG_q2'])/merged['HR (bpm) AVG_q2']
    merged['HR drift CI(95%) width'] = (merged['conf_interval_95_width_q2']**2 + merged['conf_interval_95_width_q4']**2)**0.5
    merged['bin_count'] = merged['bin_count_q2'] + merged['bin_count_q4']

    merged = merged[['HR drift (BPM)', 'HR drift (%)', 'HR drift CI(95%) width', 'bin_count']] 
    return merged

def generate_workout_decisions(drift_results: pd.DataFrame, duration_min: int, date: str) -> dict:
    """
    Simple, practical decision framework for duration progression.
    
    Logic:
    - drift < 5 bpm: Add 5 minutes
    - drift 5-8 bpm: Maintain current duration
    - drift > 8 bpm: Reduce by 5 minutes
    """
    
    # Calculate average drift
    avg_drift = (drift_results['HR drift (BPM)'] * (drift_results['bin_count'] / drift_results['bin_count'].sum())).sum()
    
    # Categorize
    if avg_drift < 3:
        category = 'Elite'
    elif avg_drift < 4:
        category = 'Excellent'
    elif avg_drift < 6:
        category = 'Good'
    elif avg_drift < 8:
        category = 'Fair'
    else:
        category = 'Poor'
    
    # Make decision
    if avg_drift < 3.0:
        decision = 'extend much'
        next_duration = duration_min + 10
        notes = f"Drift {avg_drift:.1f} bpm is super good. Ready to add 10 minutes."
    elif avg_drift <= 5.0:
        decision = 'extend'
        next_duration = duration_min + 5
        notes = f"Drift {avg_drift:.1f} bpm is good. Ready to add 5 minutes."
    elif avg_drift <= 8.0:
        decision = 'maintain'
        next_duration = duration_min
        notes = f"Drift {avg_drift:.1f} bpm. Keep building base at {duration_min} min."
    else:
        decision = 'reduce'
        next_duration = duration_min - 5
        notes = f"Drift {avg_drift:.1f} bpm is high. Drop to {next_duration} min and rebuild."
    
    return {
        'date': date,
        'duration_min': duration_min,
        'avg_drift_bpm': round(avg_drift, 1),
        'drift_details': drift_results[['HR drift (BPM)', 'bin_count']].to_dict('index'),
        'fitness_category': category,
        'decision': decision,
        'next_duration_min': next_duration,
        'paces_analyzed': drift_results.index.tolist(),
        'notes': notes
    }

def get_minutes_from_duration_string(duration_string: str) -> int:
    """Converts HH:MM:SS string into number of minutes elapsed

    Args:
        duration_string (str): HH:MM:SS string like 01:52:34

    Returns:
        int: number of minutes of time elapsed like, 01:52:34 -> 112 minutes
    """
    duration = duration_string.split(':')
    return int(duration[0])*60 + int(duration[1])

def save_decision_to_json(decision: dict, file_path: str='workout_history.json'):
    history = []
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            history = json.load(f)
    
    history.append(decision)
    
    with open(file_path, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"Changes were saved to {file_path}")

if __name__ == "__main__":
    csv_file_path = sys.argv[1]
    try:
        data = pd.read_csv(csv_file_path, skiprows=2)
    except Exception as e:
        print("Data does not exist or is not Polar Flow CSV format")
        exit(1)

    attributes = pd.read_csv(csv_file_path).iloc[0, :][['Duration', 'Date']]
    date = attributes['Date']
    minutes = get_minutes_from_duration_string(attributes['Duration'])
    drift_matrix = calculate_cardiac_drift_in_bins(data)

    decision = generate_workout_decisions(drift_matrix, minutes, date)
    save_decision_to_json(decision)
    print('Details:')
    pprint.pprint(decision)
    print('====================================================')
    print(decision['notes'])
