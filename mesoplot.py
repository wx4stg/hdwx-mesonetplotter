#!/usr/bin/env python3
# TAMU Mesonet timeseries creation for next-gen HDWX
# Created 16 September 2021 by Sam Gardner <stgardner4@tamu.edu>

from math import e
import pandas as pd
from os import path, listdir, remove, chmod
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
from shutil import copyfile

basePath = path.dirname(path.realpath(__file__))

def writeJson(productID, validTime):
    if productID == 100:
        siteName = "Farm"
        typeOfImg = "WxCenter"
    elif productID == 101:
        siteName = "Farm"
        typeOfImg = "Timeseries"
    elif productID == 102:
        siteName = "Gardens"
        typeOfImg = "WxCenter"
    elif productID == 103:
        siteName = "Gardens"
        typeOfImg = "Timeseries"
    productDesc = "Mesonet "+siteName+" "+typeOfImg
    # For prettyness' sake, make all the publishTimes the same
    publishTime = dt.utcnow()
    # Create dictionary for the product. 
    productDict = {
        "productID" : productID,
        "productDescription" : productDesc,
        "productPath" : "products/mesonet/"+siteName+"/"+typeOfImg.lower(),
        "productReloadTime" : 60,
        "lastReloadTime" : int(publishTime.strftime("%Y%m%d%H%M")),
        "isForecast" : False,
        "isGIS" : False,
        "fileExtension" : "png"
    }
    # Target path for the product json is just output/metadata/<productID>.json
    productDictJsonPath = path.join(basePath, "output", "metadata", str(productID)+".json")
    # Create output/metadata/ if it doesn't already exist
    Path(path.dirname(productDictJsonPath)).mkdir(parents=True, exist_ok=True)
    with open(productDictJsonPath, "w") as jsonWrite:
        # Write the json. indent=4 gives pretty/human-readable format
        json.dump(productDict, jsonWrite, indent=4)
    chmod(productDictJsonPath, 0o644)
    # Now we need to write a json for the product run in output/metadata/products/<productID>/<runTime>.json
    productRunDictPath = path.join(basePath, "output", "metadata", "products", str(productID), validTime.strftime("%Y%m%d%H00")+".json")
    # Create parent directory if it doesn't already exist.
    Path(path.dirname(productRunDictPath)).mkdir(parents=True, exist_ok=True)
    # Create a frame array to add to the runDict
    framesArray = [{"fhour" : i, "filename" : str(i)+".png", "gisInfo" : ["0,0", "0,0"], "valid" : int(validTime.strftime("%Y%m%d%H%M"))} for i in range(0, 60)]
    # Create a dictionary for the run
    productRunDict = {
        "publishTime" : publishTime.strftime("%Y%m%d%H%M"),
        "pathExtension" : "last24hrs",
        "runName" : validTime.strftime("%d %b %Y %HZ"),
        "availableFrameCount" : 1,
        "totalFrameCount" : 1,
        "productFrames" : framesArray
    }
    # Write productRun dictionary to json
    with open(productRunDictPath, "w") as jsonWrite:
        json.dump(productRunDict, jsonWrite, indent=4)
    chmod(productRunDictPath, 0o644)
    # Now we need to create a dictionary for the product type (TAMU)
    productTypeID = 1
    # Output for this json is output/metadata/productTypes/1.json
    productTypeDictPath = path.join(basePath, "output/metadata/productTypes/"+str(productTypeID)+".json")
    # Create output directory if it doesn't already exist
    Path(path.dirname(productTypeDictPath)).mkdir(parents=True, exist_ok=True)
    # Create empty list that will soon hold a dict for each of the products generated by this script
    productsInType = list()
    # If the productType json file already exists, read it in to discover which products it contains
    if path.exists(productTypeDictPath):
        with open(productTypeDictPath, "r") as jsonRead:
            oldProductTypeDict = json.load(jsonRead)
        # Add all of the products from the json file into the productsInType list...
        for productInOldDict in oldProductTypeDict["products"]:
            # ...except for the one that's currently being generated (prevents duplicating it)
            if productInOldDict["productID"] != productID:
                productsInType.append(productInOldDict)
    # Add the productDict for the product we just generated
    productsInType.append(productDict)
    # Create productType Dict
    productTypeDict = {
        "productTypeID" : productTypeID,
        "productTypeDescription" : "TAMU",
        "products" : sorted(productsInType, key=lambda dict: dict["productID"]) # productsInType, sorted by productID
    }
    # Write productType dict to json
    with open(productTypeDictPath, "w") as jsonWrite:
        json.dump(productTypeDict, jsonWrite, indent=4)
    chmod(productTypeDictPath, 0o644)
    # Black magic for HDWX backwards compatibility
    if path.exists(path.join(path.dirname(basePath), "config.txt")):
        if "backwardsCompatibility=true" in open(path.join(path.dirname(basePath), "config.txt")).read():
            srcImage = path.join(basePath, "output", "products", "mesonet", siteName, typeOfImg.lower(), "last24hrs", "0.png")
            for i in range(1, 60):
                copyfile(srcImage, srcImage.replace("0.png", str(i)+".png"))

def fetchData(site):
    if site == "Farm":
        url = "http://afs102.tamu.edu:8080/?command=DataQuery&uri=Server:Farm%20Mesonet.Table10&format=toa5&mode=most-recent&p1=145&p2="
    elif site == "Gardens":
        url = "http://afs102.tamu.edu:8080/?command=DataQuery&uri=Server:Gardens%20Meso.Table10&format=toa5&mode=most-recent&p1=145&p2="
    tenTable = requests.get(url)
    inputDir = path.join(basePath, "input")
    Path(inputDir).mkdir(parents=True, exist_ok=True)
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
    campTable = pd.read_csv(path.join(inputDir, fileName))
    campTable["datetimes"] = pd.to_datetime(campTable["datetimes"])
    campTable = campTable.set_index(["datetimes"])
    campTable = campTable.sort_index().loc["2021-01-01":]
    campTable = campTable.loc[(dt.now() - timedelta(days=1)):]
    campTable = campTable[~campTable.index.duplicated(keep="first")]
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
    ax1.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%M"))
    ax1.set_ylabel("°F")
    ax2 = fig.add_subplot(gs[1, :])
    ax2.barbs(windTimes, 0, u, v, pivot="middle", label="Winds")
    ax2.legend(loc="upper left")
    ax2.set_title("Winds")
    ax2.tick_params(left=False, labelleft=False)
    ax2.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%M"))
    ax4 = fig.add_subplot(gs[2, :])
    ax4.plot(campTable["AvgMSLP"], "blue", label="Mean Sea-Level Pressure")
    ax4.scatter(campTable.index, campTable["AvgMSLP"], 1, "blue")
    ax4.set_title("MSLP")
    ax4.set_ylabel("hPa")
    ax4.legend(loc="upper left")
    ax4.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%M"))
    ax5 = fig.add_subplot(gs[3, :])
    srplot = ax5.plot(campTable["AvgSR"], "yellow", label="Solar Radiation")
    ax5.scatter(campTable.index, campTable["AvgSR"], 1, "yellow")
    ax5.set_ylabel("W m^-2")
    ax6 = ax5.twinx()
    battplot = ax6.plot(campTable["Batt"], "green", label="Battery Voltage")
    ax6.scatter(campTable.index, campTable["Batt"], 1, "green")
    ax6.xaxis.set_major_formatter(pltdates.DateFormatter("%m/%d %H:%M"))
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
    tax.text(0.5, 0.6, "TAMU Mesonet "+siteName+" Site\n 10-Minute Averages Timeseries: Last 24 Hours\nValid "+campTable.index[0].strftime("%b %d %H:%M")+" through "+campTable.index[-1].strftime("%b %d %H:%M"), horizontalalignment="center", verticalalignment="center", fontsize=16)
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
    fig.savefig(path.join(prodDir, "0.png"))
    writeJson((productID+1), campTable.index[-1])

if __name__ == "__main__":
    fetchData("Farm")
    fetchData("Gardens")
    inputDir = path.join(basePath, "input")
    for file in listdir(inputDir):
        plotData(file)
        
