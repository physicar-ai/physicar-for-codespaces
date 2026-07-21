#!/bin/bash -i
# Start mapping: drive the robot around and watch the map grow in the VNC
# tab. When you are done, just run 2_nav.sh — it saves the map automatically.

pkill -f "[s]lam_toolbox|[n]av2|[c]omponent_container|[r]viz2" && sleep 3

DIR=$HOME/physicar_ws/sample_projects/navigation
grep -q "SIM=true" /opt/physicar/userdata/.env 2>/dev/null && SIM=true || SIM=false

# The map origin is wherever mapping starts. SIM: respawn to the start line
# so the origin is always the start line. Real robot: place it there.
if [ $SIM = true ]; then
    curl -s -X POST http://localhost/sim/api/respawn > /dev/null
    until curl -s http://localhost/sim/api/pose | grep -q '"x"'; do sleep 1; done
fi

setsid rviz2 -d $DIR/config/slam.rviz --ros-args -p use_sim_time:=$SIM > /dev/null 2>&1 < /dev/null &
setsid ros2 run slam_toolbox async_slam_toolbox_node --ros-args \
    --params-file $DIR/config/slam_params.yaml -p use_sim_time:=$SIM \
    > /dev/null 2>&1 < /dev/null &

# slam_toolbox is a lifecycle node — idle until configured + activated
until ros2 lifecycle set /slam_toolbox configure 2>/dev/null; do sleep 1; done
ros2 lifecycle set /slam_toolbox activate > /dev/null

echo "mapping — drive the robot, then run 2_nav.sh"
