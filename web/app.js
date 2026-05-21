const config = window.ROOM_MONITOR_FIREBASE_CONFIG;
const statusEl = document.getElementById("connectionStatus");

function formatNumber(value, digits = 2) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function formatCompact(value, digits = 1) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: digits
  }).format(value);
}

function readingValues(reading) {
  return {
    temperature: reading.temperature_c ?? reading.temperature_c_x100 / 100,
    humidity: reading.humidity_rh ?? reading.humidity_rh_x100 / 100,
    pressure: reading.pressure_hpa ?? reading.pressure_pa / 100,
    gas: reading.gas_ohm
  };
}

function formatTime(value) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function setStatus(text, stale = false) {
  statusEl.textContent = text;
  document.querySelector(".statusWrap").classList.toggle("stale", stale);
}

function updateLatest(reading) {
  if (!reading) {
    setStatus("No data", true);
    return;
  }

  const values = readingValues(reading);
  document.getElementById("temperature").textContent = formatNumber(values.temperature, 1);
  document.getElementById("humidity").textContent = formatNumber(values.humidity, 1);
  document.getElementById("pressure").textContent = formatNumber(values.pressure, 1);
  document.getElementById("gas").textContent = formatCompact(values.gas, 1);
  document.getElementById("lastUpdate").textContent = formatTime(reading.measured_at);
  document.getElementById("gasStatus").textContent =
    `valid=${reading.gas_valid ?? "--"}, heat_stable=${reading.heat_stable ?? "--"}`;
  setStatus("Live");
}

function updateHistory(snapshot) {
  const body = document.getElementById("historyBody");
  const rows = [];
  snapshot.forEach((child) => {
    rows.push(child.val());
  });
  rows.reverse();

  document.getElementById("historyCount").textContent = `${rows.length} rows`;
  renderTrend(rows);
  if (rows.length === 0) {
    body.replaceChildren(emptyRow("Waiting for readings."));
    return;
  }

  body.replaceChildren(...rows.map(historyRow));
}

function emptyRow(message) {
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 5;
  cell.textContent = message;
  row.append(cell);
  return row;
}

function historyRow(reading) {
  const values = readingValues(reading);
  const row = document.createElement("tr");
  const cells = [
    ["Time", formatTime(reading.measured_at)],
    ["Temp", `${formatNumber(values.temperature)} C`],
    ["Humidity", `${formatNumber(values.humidity)}%`],
    ["Pressure", `${formatNumber(values.pressure, 1)} hPa`],
    ["Gas", values.gas?.toLocaleString() ?? "--"]
  ];
  cells.forEach(([label, value]) => {
    const cell = document.createElement("td");
    cell.dataset.label = label;
    cell.textContent = value;
    row.append(cell);
  });
  return row;
}

function renderTrend(rows) {
  const tempPath = document.getElementById("temperaturePath");
  const humidityPath = document.getElementById("humidityPath");
  const empty = document.getElementById("trendEmpty");
  const points = rows
    .map((reading) => readingValues(reading))
    .filter((reading) => Number.isFinite(reading.temperature) && Number.isFinite(reading.humidity));

  if (points.length < 2) {
    tempPath.setAttribute("d", "");
    humidityPath.setAttribute("d", "");
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";
  tempPath.setAttribute("d", pathFor(points.map((point) => point.temperature), 720, 180, 20));
  humidityPath.setAttribute("d", pathFor(points.map((point) => point.humidity), 720, 180, 20));
}

function pathFor(values, width, height, padding) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - padding - ((value - min) / span) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

function setDemoRowsForMissingConfig() {
  renderTrend([
    { temperature_c: 25.8, humidity_rh: 58 },
    { temperature_c: 26.1, humidity_rh: 57 },
    { temperature_c: 26.3, humidity_rh: 59 },
    { temperature_c: 26.0, humidity_rh: 61 },
    { temperature_c: 25.9, humidity_rh: 60 }
  ]);
}

function boot() {
  if (!config || config.apiKey.startsWith("YOUR_")) {
    setStatus("Config needed", true);
    document.getElementById("lastUpdate").textContent = "Firebase config missing";
    setDemoRowsForMissingConfig();
    return;
  }

  firebase.initializeApp(config);
  const database = firebase.database();

  database.ref("latest").on(
    "value",
    (snapshot) => updateLatest(snapshot.val()),
    (error) => {
      console.error(error);
      setStatus("Read failed", true);
    }
  );

  database.ref("readings").orderByChild("measured_at").limitToLast(24).on(
    "value",
    updateHistory,
    (error) => {
      console.error(error);
      setStatus("History failed", true);
    }
  );
}

window.addEventListener("DOMContentLoaded", boot);
