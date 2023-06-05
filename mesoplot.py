#!/usr/bin/env python3
# TAMU Mesonet timeseries creation for python-based HDWX
# Created 16 September 2021 by Sam Gardner <stgardner4@tamu.edu>

import pandas as pd
from os import path, remove
from pathlib import Path
from matplotlib import pyplot as plt
from matplotlib import image as mplimage
from matplotlib.gridspec import GridSpec
from matplotlib import dates as pltdates
import requests
from datetime import datetime as dt
from datetime import timedelta
from metpy import calc as mpcalc
from metpy.units import units
import numpy as np
import json

basePath = path.dirname(path.realpath(__file__))
hasHelpers = False
if path.exists(path.join(basePath, "HDWX_helpers.py")):
    import HDWX_helpers
    hasHelpers = True

def fetchData(site):
    if site == "Farm":
        url = "http://afs102.tamu.edu:8080/?command=DataQuery&uri=Server:Farm%20Mesonet.Table10&format=toa5&mode=most-recent&p1=145&p2="
    elif site == "Gardens":
        url = "http://afs102.tamu.edu:8080/?command=DataQuery&uri=Server:Gardens%20Meso.Table10&format=toa5&mode=most-recent&p1=145&p2="
    tenTable = requests.get(url)
    Path(path.join(basePath, "input")).mkdir(parents=True, exist_ok=True)
    with open("input/"+site+"newData.csv", "w") as f:
        f.write(tenTable.text)
    if path.exists("input/"+site+".csv"):
        table = pd.read_csv("input/"+site+".csv")
        table["datetimes"] = pd.to_datetime(table["datetimes"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        table = table.set_index(["datetimes"])
        newTable = pd.read_csv("input/"+site+"newData.csv", skiprows=1).dropna().iloc[1:].reset_index(drop=True)
        newTable["datetimes"] = pd.to_datetime(newTable["TIMESTAMP"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        newTable = newTable.set_index(["datetimes"])
        table = pd.concat([table, newTable]).drop_duplicates().sort_index()
        remove("input/"+site+"newData.csv")
        remove("input/"+site+".csv")
        table.to_csv("input/"+site+".csv")
    else:
        newTable = pd.read_csv("input/"+site+"newData.csv", skiprows=1).dropna().iloc[1:].reset_index(drop=True)
        newTable["datetimes"] = pd.to_datetime(newTable["TIMESTAMP"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        newTable.set_index(["datetimes"])
        newTable.to_csv("input/"+site+".csv")
        remove("input/"+site+"newData.csv")

def plotData(fileName):
    siteName = fileName.replace(".csv", "")
    if siteName == "Farm":
        productID = 100
    elif siteName == "Gardens":
        productID = 102
    campTable = pd.read_csv(path.join(basePath, "input", fileName))
    campTable["datetimes"] = pd.to_datetime(campTable["datetimes"])
    campTable = campTable.set_index(["datetimes"])
    campTable = campTable.sort_index().loc["2021-01-01":]
    campTable = campTable.loc[(dt.now() - timedelta(days=1)):]
    campTable = campTable[~campTable.index.duplicated(keep="first")]
    campTable = campTable.tz_localize("US/Central").tz_convert("UTC")
    campTable["AvgAT"] = campTable["AvgAT"].astype(float)
    campTable["AvgAT"] = campTable["AvgAT"] * 1.8 + 32
    campTable["rollingAT"] = campTable["AvgAT"].rolling("1D").mean()
    campTable["AvgRH"] = campTable["AvgRH"]/100
    if "AvgWS" in campTable.columns:
        windSpeedVar = "AvgWS"
        windDirVar = "AvgWD"
    elif "AWS" in campTable.columns:
        windSpeedVar = "AWS"
        windDirVar = "AWD"
    campTable["heatIndex"] = np.ma.MaskedArray([mpcalc.heat_index(campTable["AvgAT"][i] * units.degF, campTable["AvgRH"][i]).to("degF").magnitude for i in range(0, len(campTable["AvgRH"]))]).filled(np.nan)
    campTable.loc[(campTable["heatIndex"] <= campTable["AvgAT"], "heatIndex")] = np.nan
    campTable["windChill"] = np.ma.MaskedArray([mpcalc.windchill(campTable["AvgAT"][i] * units.degF, campTable[windSpeedVar][i] * units.meter / units.second).to("degF").magnitude for i in range(0, len(campTable["AvgRH"]))]).filled(np.nan)
    campTable.loc[(campTable["windChill"] >= campTable["AvgAT"], "windChill")] = np.nan
    campTable["AvgDP"] = [mpcalc.dewpoint_from_relative_humidity(campTable["AvgAT"][i] * units.degF, campTable["AvgRH"][i]).to("degF").magnitude for i in range(0, len(campTable["AvgRH"]))]
    windTimes = list()
    u = list()
    v = list()
    for i in range(0, len(campTable[windSpeedVar]), 2):
        time = campTable.index[i]
        windTimes.append(time)
        spd = units.Quantity(campTable[windSpeedVar][i], "m/s")
        dir = units.Quantity(campTable[windDirVar][i], "degrees")
        uwind, vwind = mpcalc.wind_components(spd, dir)
        u.append(uwind.to(units("knots")).magnitude)
        v.append(vwind.to(units("knots")).magnitude)
    if siteName == "Farm":
        elevation = 67.7772216796875 * units.meter
    elif siteName == "Gardens":
        elevation = 95.36789703369141 * units.meter
    campTable["AvgMSLP"] = [mpcalc.altimeter_to_sea_level_pressure((float(campTable["AvgBP"][i]) * units.hectopascal), elevation, (campTable["AvgAT"][i] * units.degF)) for i in range(0, len(campTable["AvgBP"]))]
    fig = plt.figure()
    px = 1/plt.rcParams["figure.dpi"]
    fig.set_size_inches(1920*px, 1080*px)
    gs = GridSpec(4, 3, figure=fig)
    gs.update(hspace = 50*px)
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(campTable["AvgAT"], "red", label="Temperature")
    ax1.scatter(campTable.index, campTable["AvgAT"], 1, "red")
    ax1.plot(campTable["AvgDP"], "green", label="Dew Point")
    ax1.scatter(campTable.index, campTable["AvgDP"], 1, "green")
    ax1.plot(campTable["heatIndex"], "olive", label="Heat Index")
    ax1.scatter(campTable.index, campTable["heatIndex"], 1, "olive")
    ax1.plot(campTable["windChill"], "aqua", label="Wind Chill")
    ax1.scatter(campTable.index, campTable["windChill"], 1, "aqua")
    ax1.legend(loc="upper left")
    ax1.set_title("Temperature/Dew Point")
    ax1.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%MZ"))
    ax1.set_ylabel("°F")
    ax2 = fig.add_subplot(gs[1, :])
    ax2.barbs(windTimes, 0, u, v, pivot="middle", label="Winds")
    ax2.legend(loc="upper left")
    ax2.set_title("Winds")
    ax2.tick_params(left=False, labelleft=False)
    ax2.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%MZ"))
    ax4 = fig.add_subplot(gs[2, :])
    ax4.plot(campTable["AvgMSLP"], "blue", label="Mean Sea-Level Pressure")
    ax4.scatter(campTable.index, campTable["AvgMSLP"], 1, "blue")
    ax4.set_title("MSLP")
    ax4.set_ylabel("hPa")
    ax4.legend(loc="upper left")
    ax4.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%MZ"))
    ax5 = fig.add_subplot(gs[3, :])
    srplot = ax5.plot(campTable["AvgSR"], "yellow", label="Solar Radiation")
    ax5.scatter(campTable.index, campTable["AvgSR"], 1, "yellow")
    ax5.set_ylabel("W m^-2")
    ax6 = ax5.twinx()
    battplot = ax6.plot(campTable["Batt"], "green", label="Battery Voltage")
    ax6.scatter(campTable.index, campTable["Batt"], 1, "green")
    ax6.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%MZ"))
    ax6.set_ylabel("Volts")
    fourthPlotLines = srplot+battplot
    ax6.legend(fourthPlotLines, [line.get_label() for line in fourthPlotLines], loc="upper left")
    ax6.set_title("Solar and Battery")
    fig.subplots_adjust(bottom = 0.21)
    fig.subplots_adjust(top = 0.95)
    fig.subplots_adjust(right = 0.95)
    fig.subplots_adjust(left = 0.05)
    fig.set_size_inches(1920*px, 1080*px)
    tax = fig.add_axes([ax6.get_position().x0+(ax6.get_position().width/2)-(ax6.get_position().width/6),0.1,(ax6.get_position().width/3),.05])
    tax.text(0.5, 0.6, "TAMU Mesonet "+siteName+" Site\n 10-Minute Averages Timeseries: Last 24 Hours\nValid "+campTable.index[0].strftime("%b %d %H:%M")+" through "+campTable.index[-1].strftime("%b %d %H:%MZ"), horizontalalignment="center", verticalalignment="center", fontsize=16)
    plt.setp(tax.spines.values(), visible=False)
    tax.tick_params(left=False, labelleft=False)
    tax.tick_params(bottom=False, labelbottom=False)
    lax = fig.add_axes([.75,0.01,0.2,0.2])
    tax.set_xlabel("Python HDWX -- Send bugs to stgardner4@tamu.edu")
    atmoLogo = mplimage.imread("assets/atmoLogo.png")
    lax.imshow(atmoLogo)
    lax.axis("off")
    prodDir = path.join(basePath, "output", "products", "mesonet", siteName, "timeseries", "last24hrs")
    Path(prodDir).mkdir(parents=True, exist_ok=True)
    if hasHelpers:
        HDWX_helpers.saveImage(fig, path.join(prodDir, "0.png"))
        HDWX_helpers.writeJson(basePath, (productID+1), campTable.index[-1], "0.png", campTable.index[-1], ["0,0", "0,0"], 60)
    else:
        fig.savefig(path.join(prodDir, "0.png"))

if __name__ == "__main__":
    shouldFarm = True
    shouldGarden = True
    now = dt.utcnow()
    farmLastRunPath = path.join("output", "metadata", "products", "101", now.strftime("%Y%m%d%H00.json"))
    if path.exists(farmLastRunPath):
        with open(farmLastRunPath, "r") as jsonRead:
            lastRunDict = json.load(jsonRead)
        if now - timedelta(minutes=10) < dt.strptime(lastRunDict["productFrames"][0]["valid"], "%Y%m%d%H%M"):
            shouldFarm = False
    gardensLastRunPath = path.join("output", "metadata", "products", "103", now.strftime("%Y%m%d%H00.json"))
    if path.exists(gardensLastRunPath):
        with open(gardensLastRunPath, "r") as jsonRead:
            lastRunDict = json.load(jsonRead)
        if now - timedelta(minutes=10) < dt.strptime(lastRunDict["productFrames"][0]["valid"], "%Y%m%d%H%M"):
            shouldGarden = False
    if shouldFarm:
        fetchData("Farm")
        plotData("Farm.csv")
    if shouldGarden:
        fetchData("Gardens")
        plotData("Gardens.csv")
