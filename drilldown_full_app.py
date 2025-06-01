from flask import Flask, render_template, request
from influxdb import InfluxDBClient
from influx_query_generator import generate_influx_query, get_sensor_type
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
from pathlib import Path

app = Flask(__name__)

def load_config():
    with open(Path(__file__).parent / "config.json", "r") as f:
        return json.load(f)

def is_within_week_range(timestamp_str, start_dt, end_dt):
    try:
        ts = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        return start_dt <= ts < end_dt
    except ValueError:
        return False

def is_within_month(timestamp_str, year, month):
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.year == year and dt.month == month
    except ValueError:
        return False
    
def is_within_year(timestamp_str, year):
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.year == year
    except ValueError:
        return False

def get_all_sensors(influx_client):
    query = 'SHOW TAG VALUES FROM energy WITH KEY = "entity_id"'
    return sorted([r['value'] for r in influx_client.query(query).get_points()])

def get_month_range(year, month):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start.isoformat() + "Z", end.isoformat() + "Z"

def get_year_range(year):
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    return start.isoformat() + "Z", end.isoformat() + "Z"

def get_day_range(year, month, day):
    start = datetime(year, month, day)
    end = start + timedelta(days=1)
    return start.isoformat() + "Z", end.isoformat() + "Z"

@app.route('/')
def index():
    from collections import defaultdict
    month_labels = {
        "01": "Jan", "02": "Feb", "03": "Mär", "04": "Apr", "05": "Mai",
        "06": "Jun", "07": "Jul", "08": "Aug", "09": "Sep", "10": "Okt",
        "11": "Nov", "12": "Dez"
    }

    year = int(request.args.get('year', datetime.now().year))
    local_zone = ZoneInfo("Europe/Berlin")
    local_year_start = datetime(year, 1, 1, 0, 0, tzinfo=local_zone)
    local_year_end = datetime(year + 1, 1, 1, 0, 0, tzinfo=local_zone)
    start_dt = local_year_start.astimezone(timezone.utc)
    end_dt = local_year_end.astimezone(timezone.utc)
    start = start_dt.isoformat().replace('+00:00', 'Z')
    end = end_dt.isoformat().replace('+00:00', 'Z')
    config = load_config()
    influx_client = InfluxDBClient(
        host=config["influxdb"]["host"],
        port=config["influxdb"]["port"]
    )
    influx_client.switch_database(config["influxdb"]["database"])
    sensors = get_all_sensors(influx_client)

    monthly_totals = defaultdict(lambda: defaultdict(float))
    max_day_per_month = defaultdict(lambda: datetime.min.date())
    raw_data = defaultdict(list)

    for sensor in sensors:
        sensor_type = get_sensor_type(influx_client, sensor)
        query = generate_influx_query(sensor, sensor_type, period="1d", start=start, end=end)
        result = list(influx_client.query(query).get_points())
        field = "value" if sensor_type == "delta" else "sum"
        for r in result:
            try:
                dt = datetime.strptime(r['time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt.year == year:
                    month_key = f"{dt.month:02d}"
                    val = round(r.get(field, 0), 4)
                    if val > 0:
                        raw_data[(month_key, dt.date(), sensor)].append(val)
                        if dt.date() > max_day_per_month[month_key]:
                            max_day_per_month[month_key] = dt.date()
            except:
                continue

    for (month, day, sensor), values in raw_data.items():
        if day <= max_day_per_month[month]:
            monthly_totals[month][sensor] += sum(values)

    all_months = sorted(monthly_totals.keys())
    month_categories = [month_labels[m] for m in all_months]

    series_dict = {sensor: [] for sensor in sensors}
    total_kwh = sum(
        sum(sensor_data.values())
        for sensor_data in monthly_totals.values()
    )
    for sensor in sensors:
        for m in all_months:
            value = monthly_totals[m].get(sensor, 0)
            series_dict[sensor].append({'x': month_labels[m], 'y': round(value, 4)})

    series = sorted(series_dict.items(), key=lambda s: sum(p['y'] for p in s[1]))
    series.reverse()
    series_data = json.dumps([{'name': name, 'data': data} for name, data in series])

    return render_template("drilldown_year.html", year=year, series_data=series_data, month_categories=month_categories, total_kwh=round(total_kwh, 2))

@app.route('/<int:year>/<int:month>')
def view_month(year, month):
    from collections import defaultdict
    import calendar
    local_zone = ZoneInfo("Europe/Berlin")
    local_month_start = datetime(year, month, 1, 0, 0, tzinfo=local_zone)
    if month == 12:
        local_month_end = datetime(year + 1, 1, 1, 0, 0, tzinfo=local_zone)
    else:
        local_month_end = datetime(year, month + 1, 1, 0, 0, tzinfo=local_zone)
    
    start_dt = local_month_start.astimezone(timezone.utc)
    end_dt = local_month_end.astimezone(timezone.utc)
    start = start_dt.isoformat().replace('+00:00', 'Z')
    end = end_dt.isoformat().replace('+00:00', 'Z')
    start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
    end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
    config = load_config()
    influx_client = InfluxDBClient(
        host=config["influxdb"]["host"],
        port=config["influxdb"]["port"]
    )
    influx_client.switch_database(config["influxdb"]["database"])
    sensors = get_all_sensors(influx_client)

    daily_totals = defaultdict(lambda: defaultdict(float))

    for sensor in sensors:
        sensor_type = get_sensor_type(influx_client, sensor)
        query = generate_influx_query(sensor, sensor_type, period="1d", start=start, end=end)
        result = list(influx_client.query(query).get_points())
        field = "value" if sensor_type == "delta" else "sum"

        for r in result:
            try:
                dt = datetime.strptime(r['time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt.year == year and dt.month == month:
                    key = dt.strftime("%d")
                    val = round(r.get(field, 0), 4)
                    if val > 0:
                        daily_totals[key][sensor] += val
            except:
                continue

    all_days = [f"{i:02d}" for i in range(1, 32)]
    series_dict = {sensor: [] for sensor in sensors}
    total_kwh = sum(
        sum(sensor_data.values())
        for sensor_data in daily_totals.values()
    )

    for sensor in sensors:
        for d in all_days:
            value = daily_totals[d].get(sensor, 0)
            series_dict[sensor].append({'x': d[-2:], 'y': round(value, 4)})

    series = sorted(series_dict.items(), key=lambda s: sum(p['y'] for p in s[1]))
    series.reverse()
    series_data = json.dumps([{'name': name, 'data': data} for name, data in series])

    return render_template("drilldown_month.html", year=year, month=month, series_data=series_data, total_kwh=round(total_kwh, 2))


@app.route('/<int:year>/<int:month>/<int:day>')
def view_day(year, month, day):
    from collections import defaultdict
    local_zone = ZoneInfo("Europe/Berlin")
    local_day_start = datetime(year, month, day, 0, 0, tzinfo=local_zone)
    start_dt = local_day_start.astimezone(timezone.utc)
    end_dt = (local_day_start + timedelta(hours=24)).astimezone(timezone.utc)
    start = start_dt.isoformat().replace("+00:00", "Z")
    end = end_dt.isoformat().replace("+00:00", "Z")

    config = load_config()
    influx_client = InfluxDBClient(
        host=config["influxdb"]["host"],
        port=config["influxdb"]["port"]
    )
    influx_client.switch_database(config["influxdb"]["database"])

    sensors = get_all_sensors(influx_client)

    daily_data = defaultdict(lambda: defaultdict(float))
    for sensor in sensors:
        sensor_type = get_sensor_type(influx_client, sensor)
        query = generate_influx_query(sensor, sensor_type, period="1h", start=start, end=end)
        result = list(influx_client.query(query).get_points())
        field = "value" if sensor_type == "delta" else "sum"
        for r in result:
            try:
                dt = datetime.strptime(r['time'], "%Y-%m-%dT%H:%M:%SZ")
                dt = dt.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Berlin"))
                hour = dt.strftime("%H")

                val = round(r.get(field, 0), 4)
                if val > 0:
                    daily_data[hour][sensor] += val
            except:
                continue

    all_hours = [f"{i:02d}" for i in range(24)]

    total_kwh = sum(
        sum(sensor_data.values())
        for sensor_data in daily_data.values()
    )

    series_dict = {sensor: [] for sensor in sensors}
    for sensor in sensors:
        for h in all_hours:
            value = daily_data[h].get(sensor, 0)
            series_dict[sensor].append({'x': h, 'y': round(value, 4)})

    series = sorted(series_dict.items(), key=lambda s: sum(p['y'] for p in s[1]))
    series.reverse()
    # KORREKTUR: Tupel-Entpackung statt Zugriff auf Dict
    series_data = json.dumps([{'name': name, 'data': data} for name, data in series])

    prev_dt = datetime(year, month, day) - timedelta(days=1)
    next_dt = datetime(year, month, day) + timedelta(days=1)

    return render_template("drilldown_day.html",
        year=year, month=month, day=day,
        prev_year=prev_dt.year, prev_month=prev_dt.month, prev_day=prev_dt.day,
        next_year=next_dt.year, next_month=next_dt.month, next_day=next_dt.day,
        series_data=series_data,
        total_kwh=round(total_kwh, 2)
    )


@app.route('/total/<string:view_type>/<int:year>', defaults={'month': None, 'day': None})
@app.route('/total/<string:view_type>/<int:year>/<int:month>', defaults={'day': None})
@app.route('/total/<string:view_type>/<int:year>/<int:month>/<int:day>')
def total_per_sensor(view_type, year, month, day):
    from collections import defaultdict
    config = load_config()
    influx_client = InfluxDBClient(
        host=config["influxdb"]["host"],
        port=config["influxdb"]["port"]
    )
    influx_client.switch_database(config["influxdb"]["database"])
    sensors = get_all_sensors(influx_client)

    if view_type == "year":
        start, end = get_year_range(year)
        heading = f"Jahresverbrauch {year}"
        back_url = f"/?year={year}"
    elif view_type == "month" and month:
        start, end = get_month_range(year, month)
        heading = f"Monatsverbrauch {year}-{month:02d}"
        back_url = f"/{year}/{month:02d}"
    elif view_type == "day" and month and day:
        start, end = get_day_range(year, month, day)
        heading = f"Tagesverbrauch {year}-{month:02d}-{day:02d}"
        back_url = f"/{year}/{month:02d}/{day:02d}"
    else:
        return "Ungültige Parameter", 400

    totals = {}
    total_kwh = 0.0
    for sensor in sensors:
        sensor_type = get_sensor_type(influx_client, sensor)
        query = generate_influx_query(sensor, sensor_type, period="1h", start=start, end=end)
        result = list(influx_client.query(query).get_points())
        field = "value" if sensor_type == "delta" else "sum"
        total = sum(round(r.get(field, 0), 4) for r in result if r.get(field, 0) > 0)
        if total > 0:
            totals[sensor] = total
            total_kwh += total

    sorted_data = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    series_data = json.dumps([{"name": "Gesamtverbrauch", "data": [{"x": sensor, "y": round(val, 2)} for sensor, val in sorted_data]}])

    return render_template("total_per_sensor.html", heading=heading, series_data=series_data, total_kwh=round(total_kwh, 2), back_url=back_url)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
