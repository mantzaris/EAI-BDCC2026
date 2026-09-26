from traffic_risk_twins.data_access import download, save_json

if __name__ == '__main__':
    sources = [
        ('https://drive.usercontent.google.com/download?id=1wD-mHlqAb2mtHOe_68fZvDh1LpDegMMq&export=download&confirm=t', 'data/raw/pems-bay.h5'),
        ('https://raw.githubusercontent.com/liyaguang/DCRNN/master/data/sensor_graph/adj_mx_bay.pkl', 'data/raw/adj_mx_bay.pkl'),
        ('https://raw.githubusercontent.com/liyaguang/DCRNN/master/data/sensor_graph/graph_sensor_locations_bay.csv', 'data/raw/graph_sensor_locations_bay.csv'),
    ]
    rows = []
    for url, path in sources:
        row = download(url, path)
        rows.append(row)
        save_json('manifests/pems_download.json', rows)
        print(row, flush=True)
