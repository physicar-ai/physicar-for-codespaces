#!/bin/bash -i
# Autonomous driving (saves the map from a running SLAM automatically).
# In RViz: [2D Pose Estimate] click-drag where the robot really is,
#          [2D Goal Pose] click the destination — off it goes.

DIR=$HOME/physicar_ws/sample_projects/navigation
grep -q "SIM=true" /opt/physicar/userdata/.env 2>/dev/null && SIM=true || SIM=false

# SLAM is running — save its map now (open map/my_map.png to check it)
if pgrep -f "[a]sync_slam_toolbox" > /dev/null; then
    mkdir -p $DIR/map
    ros2 run nav2_map_server map_saver_cli -f $DIR/map/my_map --fmt png
fi

# SLAM also publishes map->odom — swap it (and any previous run) out
pkill -f "[s]lam_toolbox|[n]av2|[c]omponent_container|[r]viz2" && sleep 3
[ -f $DIR/map/my_map.yaml ] || { echo "no map — run 1_slam.sh first"; exit 1; }

# AMCL starts localized at the map origin = the start line (nav2_params
# set_initial_pose). SIM: respawn there. Real robot: place it there.
if [ $SIM = true ]; then
    curl -s -X POST http://localhost/sim/api/respawn > /dev/null
    until curl -s http://localhost/sim/api/pose | grep -q '"x"'; do sleep 1; done
fi

setsid ros2 launch nav2_bringup localization_launch.py \
    map:=$DIR/map/my_map.yaml params_file:=$DIR/config/nav2_params.yaml \
    use_sim_time:=$SIM autostart:=false > /dev/null 2>&1 < /dev/null &
setsid ros2 launch nav2_bringup navigation_launch.py \
    params_file:=$DIR/config/nav2_params.yaml \
    use_sim_time:=$SIM autostart:=false > /dev/null 2>&1 < /dev/null &

echo "starting nav2 (about 30s) ..."
# bring each stack up once its manager appears (the call returns when done)
for mgr in lifecycle_manager_localization lifecycle_manager_navigation; do
    until ros2 service type /$mgr/manage_nodes > /dev/null 2>&1; do sleep 1; done
    ros2 service call /$mgr/manage_nodes \
        nav2_msgs/srv/ManageLifecycleNodes "{command: 0}" > /dev/null
done

setsid rviz2 -d $DIR/config/nav.rviz --ros-args -p use_sim_time:=$SIM > /dev/null 2>&1 < /dev/null &

# rviz sometimes misses the latched map — republish it once rviz is up
sleep 5
ros2 service call /map_server/load_map nav2_msgs/srv/LoadMap \
    "{map_url: $DIR/map/my_map.yaml}" > /dev/null

echo "ready — click a goal in RViz (VNC tab)"
