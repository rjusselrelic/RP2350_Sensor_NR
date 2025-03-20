# RP2350_Sensor_NR

## Software installation
1. Install Micropython image on RP2350 *for this step only you will need a compuer that doesn't block usb storage devices*
2. Download the [image](https://micropython.org/download/RPI_PICO2_W/) for the Pico 2 W 
3Plug the device in, and drag the .uf2 file in
4. Install [Thonny](https://thonny.org/)
5. Switch the intrepreter in the bottom right to the micropython on the microcontroller
6. In Thonny's file interface, upload .py files in the root of the porject along with the entire lib directory

## Software configuration
*Before beginning make sure you have a New Relic account set up*
*you can get [one](https://newrelic.com/pricing/free-tier) for free*

1. Generate and copy a NR License aka ingest [key](https://one.newrelic.com/launcher/api-keys-ui.api-keys-launcher?_gl=1*1ubudw0*_gcl_au*ODM1MTQzNjA0LjE3NDE0NTMwNTM.*_ga*ODU3NjgwMDEyLjE3NDE0NTMwNTM.*_ga_R5EF3MCG7B*MTc0MjQzMTkyOS43LjEuMTc0MjQzMTk2OC4yMS4xLjExMDY0NDY0NDU.)
2. Open the credentials.py file on the device in Thonny.  Add your wifi credentials and the license key you copied
3. Open environment.py and change the hostname, appname, and if necessary your region for WIFI frequency compliance.
4. Reset the board, or click stop, then run main.py in Thonny

##Configure Newrelic
1. Upload .json file from dashboards using these [directions](https://docs.newrelic.com/docs/query-your-data/explore-query-data/dashboards/dashboards-charts-import-export-data/)
2. Create your own alert [conditions](https://docs.newrelic.com/docs/tutorial-create-alerts/create-an-alert/)