# Project PULSE
### Public Transit Analytics and Disruption Intelligence

## Overview

Project PULSE is a transportation analytics platform
designed to monitor and analyze the Massachusetts Bay
Transportation Authority (MBTA) network using real-time
public transit data.

The project combines data engineering, statistical
analysis, geospatial analytics, unsupervised machine
learning, and network science to identify potential
service disruptions and transportation reliability patterns.

## Key Features

- Real-time vehicle tracking across transportation modes
- Automated network-wide prediction collection
- Historical SQLite database
- Route-level and trip-level schedule deviation analysis
- Geographic disruption hotspot detection
- DBSCAN spatial clustering
- Custom Disruption Priority Index (DPI)
- Graph-based analysis of shared-trip connections
- Official MBTA service alert integration
- Interactive geographic visualizations
- Scheduled background data collection

## Transportation Modes

- Bus
- Subway
- Light Rail
- Commuter Rail
- Ferry
- Replacement Shuttle tracking

## Initial Results

November 24, 2026:

- 179 routes in the network inventory
- 72,426 historical prediction observations
- 234 potential geographic disruption hotspots
- 17 geographic disruption clusters
- 153 active official service alerts
- 326 route-alert associations

These figures represent initial collection and analysis
results rather than permanent network statistics.

## Technology Stack

- Python
- Pandas
- NumPy
- SQLite
- SQL
- Requests
- Folium
- Scikit-learn
- NetworkX
- Matplotlib
- Seaborn
- JupyterLab
- macOS launchd
- MBTA V3 API

## Methodology

PULSE compares predicted arrival and departure times
against scheduled service times to estimate forecast
schedule deviations.

Trip-level aggregation reduces the influence of repeated
stop-level predictions.

DBSCAN identifies geographic concentrations of potential
disruptions, while graph analysis identifies shared-trip
connections between disruption clusters.

The custom Disruption Priority Index combines deviation
severity, route exposure, and the proportion of delayed
trips.

## Limitations

- Predicted schedule deviations are not observed delays.
- The priority index is experimental and is not an
  official MBTA performance metric.
- Geographic proximity does not establish causation.
- Shared-trip connections do not prove disruption propagation.
- Network collections occur over multiple API requests.
- Service alerts and prediction observations may have
  different collection timestamps.
- Some alert route identifiers may not match the inventory.
- Historical predictive modeling requires additional data.
- Scheduled local collection requires an awake Mac,
  an active user session, and internet connectivity.

## Future Development

- Historical reliability forecasting
- Predictive disruption modeling
- Interactive web application
- Automated dashboard refresh
- Cloud-based data collection

## Data Source

MBTA V3 API
https://api-v3.mbta.com/

## Project Status

Version 1.0: Analytical prototype.

The background scheduler is configured.
Successful unattended database ingestion is pending
runtime verification.

## Author

Samyush Rana

Data Science and Business Analytics
Applied Analytics


## Installation and Usage

1. Clone the repository.

2. Install the required dependencies:
    pip install -r requirements.txt

3. Initialize the local database:
    python setup_database.py

4. Collect a network-wide prediction snapshot:
    python pulse_collector.py

5. Open the analytical notebook:
    jupyter lab ProjectPULSE_V1.ipynb

Historical data accumulates through repeated collection.
The original historical database is not distributed with
this repository. Sample analytical results are provided
in the outputs directory.

## License

Original project code is licensed under the MIT License.
Third-party data remains subject to its applicable terms.
