#!/bin/bash
#source /opt/home/espi/.bashrc
source /home/lazecky/.bashrc_all
source activate
conda activate

cd /home/lazecky/dustee/espigis/code
if [ `date | awk {'print $6'}` == AM ]; then
 extra="-d yesterday"
else
 extra=""
fi
#./update_map.py `date -d 'yesterday' +%Y-%m-%d` no2
./update_map.py `date $extra +%Y-%m-%d` no2
./update_map.py `date $extra +%Y-%m-%d` aerosols
./update_map.py `date $extra +%Y-%m-%d` pm10
#./update_map.py `date +%Y-%m-%d` pm10-24
#./update_map.py 2019-08-20 no2
