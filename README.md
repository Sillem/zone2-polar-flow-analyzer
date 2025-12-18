# ZONE-2 ANALYZER

Everyone just says: build the engine. How? Run long. How long? Do I need to run marathon in order to stress my cardiac system enough? Do I need to quit my 9-5 job in order to run every minute I have? With all the data we have at our hands, it seems silly that we have to eyeball the duration of our Z2 runs.

## Idea
Inspired by the idea of muscle failure in resistance training, I assumed that to maximize our training output from long running we have to put the circulatory system close to "failure". Of course we can't do it fully as we would run no more. I decided to measure the magnitude of the stress placed on the cardio system by analyzing average Cardiac Drift (difference between levels of heart rate) in second and last quarter of the training session.

The app is a CLI tool for analyzing magnitude of the cardiac drift in Zone 2 running sessions. It compares average drift inside different 0.5 km/h bins (like 9km/h, 9.5km/h etc.) between last and second quarter of the training session. In order to work it requires as an argument a .csv file with training session from Polar Flow.

## Usage
Install required packages
```
pip install requirements.txt
```
Analyze the training
```
python zone2-analyzer.py CSV_PATH
```

## Assumptions
The method assumes that pace is strictly chosen based on RPE: nose breathing and speaking. It is meant to be used in the sequential manner during training block, where the paces are similar on same RPE. It is unproductive to run above Zone 2 (so without ability to speak freely) and then listen to the directions to shorten the run*... just **slow down**.

*there are many more variables influencing HR drift, so by sticking to the one RPE we can establish duration to exertion at one fitness level