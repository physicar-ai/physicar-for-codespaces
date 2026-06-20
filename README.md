# PhysiCar DeepRacer

A workspace where you can train autonomous driving models with reinforcement learning.

## [0] Getting Started

Click **[`app.physicar`](app.physicar)** in the left explorer to open the UI-based DeepRacer app.

## [1] Models

Select **Models** from the app's left menu to train, evaluate, and monitor models.

### Start Training a Model

Click the **Create Model** button at the top right of the model list page to create a new model.

#### Training Settings

- **MODEL NAME** : Model name
- **SIMULATION**
    - Sub Simulation Count : Number of sub-simulations to run concurrently (default `only main`)
    - Simulation settings
        - Choose a track : Track to train on
        - Alternate Training Direction : Train the track in both directions alternately
        - Race Type : 
            - `Time Trial`: Drive on a track without obstacles (boxes)
            - `Object Avoidance`: Drive on a track with obstacles (boxes) (when selected → set box count, placement, box type)
- **Vehicles**
    - Vehicle Type : `PhysiCar` / `DeepRacer`
    - Sensor : 
        - Camera: 1 (default)
        - Lidar: whether to use it
    - Action Space
        - Choose the number of discrete actions
        - Set speed (Speed) and steering angle (Angle) for each action index
- **Training**
    - Algorithm : PPO (fixed)
    - Hyperparameters
        - Batch size : Number of data samples used per weight update (default `32`)
        - Discount factor : Ratio for converting future rewards to present value (default `0.99`)
        - Learning Rate : Strength of weight adjustment in a single update (default `0.0003`)
        - Entropy : Strength of exploration toward new actions (default `0.01`)
        - Loss type : How prediction error is measured (`Huber` / `Mean Squared Error`)
    - Best Model Metric : Metric for selecting the best model (`Progress` / `Reward`)
    - Max Training Time : Maximum training time (minutes)
- **Reward Function** : Write the reward function code (see [below](#3-reward-function))

Once training starts, you are taken to the model detail page.


### Monitoring Training

- On the **Models** page, select a training model to open its detail page.

- To monitor a training model, select the **Training** tab at the top.
    - Check training trends with the Reward / Progress graphs.
    - Watch the vehicle drive in real time with Chase View / Front View.
    - Stop training midway with the **Stop Training** button.

- Model training status
    - `training` : Training in progress
    - `evaluating` : Evaluation in progress
    - `ready` : Training complete (checkpoint exists)
    - `failed` : Training failed (no checkpoint)  
        > Training can often fail. If it becomes `failed`, create a new model and train again.

### Evaluating a Model

- You can run a trained model on a track to directly check how well it drives. 

- You typically evaluate a model when you want an accurate lap-time record, or to run it on a different track to check for overfitting.

- Click **Actions → Start Evaluation** on the model detail page to start evaluation.

#### Evaluation Settings

- **Simulation**
    - Choose a track : Track to evaluate on
    - Race Type : `Time Trial` / `Object Avoidance` (when selected → set box count, placement, box type)
- **Evaluation Settings**
    - Number of Trials : Number of evaluation runs (1–20, default `5`)
    - Checkpoint : Model used for evaluation (`Last` / `Best`)
    - Off-track Penalty : Time (seconds) added when going off-track (default `5`)
    - Collision Penalty : Time (seconds) added on obstacle collision (default `5`)


## [2] Tracks

- Select **Tracks** from the left menu to manage tracks.
- Tracks come in two types: **Custom Tracks** that you create yourself, and **Official Tracks** provided by default.
- To create your own track, use the World Builder: <https://physicar.ai/resources/world-builder>
- On each track card, you can check the length (Length) and width (Width) and download the **Waypoints** file.

### Waypoints

A track coordinate file that can be downloaded with the **Waypoints** button on every track.

- A `(N, 6)` NumPy array (`.npy`), where each row is a point placed along the track.
- The 6 columns are in the order `[center x, center y, inner border x, inner border y, outer border x, outer border y]`.
- The reward function's `waypoints` parameter uses only columns 0 and 1 (the center-line coordinates).
- Download it to analyze the track shape or design a reward function.


## [3] Reward Function

A function called at every step that scores the vehicle's behavior.
The vehicle learns in the direction that increases this score.

### Basic Structure

```python
def reward_function(params):

    # Write logic to calculate reward based on params

    return float(reward)
```

- The function name must be `reward_function`, with a single argument `params`.
- The return value must be wrapped with `float`.

### Params

`params` is a Python dictionary holding the driving state at each step; you read values by key (e.g. `params['speed']`) to compute the reward. The main keys are:

| Key | Value Type | Description |
|----------|------|------|
| `all_wheels_on_track` | bool | Whether all wheels are on the track |
| `x` | float | Vehicle position x-coordinate (m) |
| `y` | float | Vehicle position y-coordinate (m) |
| `heading` | float | Vehicle heading (degrees, -180~180) |
| `progress` | float | Track progress (0~100) |
| `steps` | int | Cumulative step count (starts at 2) |
| `speed` | float | Speed (m/s, 0~5.0) |
| `steering_angle` | float | Steering angle (degrees, -20~20) |
| `track_width` | float | Track width (m) |
| `track_length` | float | Total track length (m) |
| `distance_from_center` | float | Distance from the center line |
| `is_left_of_center` | bool | Whether it is left of the center line |
| `is_offtrack` | bool | Whether it left the track |
| `is_crashed` | bool | Whether it crashed |
| `waypoints` | list[(x, y)] | Track center-line waypoints (first point `waypoints[0]` equals last point `waypoints[-1]` — the track forms a loop) |
| `closest_waypoints` | [int, int] | [previous, next] waypoint indices |
| `objects_location` | list[[x, y]] | Obstacle positions (OBJECT_AVOIDANCE) |
| `objects_left_of_center` | list[bool] | Whether each obstacle is left of the center line (OBJECT_AVOIDANCE) |
| `closest_objects` | [int, int] | [behind, ahead] nearest obstacle indices (OBJECT_AVOIDANCE) |

### Example: Default Reward Function

```python
def reward_function(params):
    # Read input parameters
    distance_from_center = params['distance_from_center']
    track_width = params['track_width']

    # Calculate 3 marks that are farther and father away from the center line
    marker_1 = 0.1 * track_width
    marker_2 = 0.25 * track_width
    marker_3 = 0.5 * track_width

    # Give higher reward if the car is closer to center line and vice versa
    if distance_from_center <= marker_1:
        reward = 1
    elif distance_from_center <= marker_2:
        reward = 0.5
    elif distance_from_center <= marker_3:
        reward = 0.1
    else:
        reward = 1e-3  # likely crashed/ close to off track

    return float(reward)
```
