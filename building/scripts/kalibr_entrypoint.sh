#!/bin/bash

set -eox pipefail

export KALIBR_MANUAL_FOCAL_LENGTH_INIT=1
source "${WORKSPACE}/devel/setup.bash"
cd "${WORKSPACE}"

"$@"
command_status=$?

# NOTE(Jack): Normally an entrypoint script would end with "$@, but we need to do some post processing inside of the
# running docker container to get the data sorted and moved into the right place. After the command to run kalibr is
# finished executing here the script below will execute.to move and organize the output diagnostics.

# NOTE(Jack): We need to clean the camera name from having slashes (ex. like in a ROS topic) because otherwise the
# mkdir command below could interpret that as a multilevel path.
camera_name="${CAMERA_TOPIC#/}"
camera_name="${camera_name//\//_}"

# TODO(Jack): We should protect against the case where there are no output files to move, if that is an error condition
# that we realistically need to worry about.
# TODO(Jack): Define a variable for the data path?
# TODO(Jack): It might be a smart idea to be more specific about which files we move, for example all files that do not
# end in .bag or all files that match the kalibr output format pattern, etc.
# NOTE(Jack): Kalibr does not let us specify an output path or filename for the output diagnostics. Therefore
# we need to manually move all the outputs into a batch specific (i.e. camera name and model) directory.
mkdir --parents "/data/kalibr/${camera_name}"
mv -- /data/*.pdf /data/*.txt /data/*.yaml "/data/kalibr/${camera_name}"

exit "${command_status}"