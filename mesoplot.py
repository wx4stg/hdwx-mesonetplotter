#!/usr/bin/env python3
# TAMU Mesonet timeseries creation for next-gen HDWX
# Created 16 September 2021 by Sam Gardner <stgardner4@tamu.edu>

import pandas as pd
from os import path, listdir, rename, remove
from matplotlib import pyplot as plt
from matplotlib import image as mpimage
import requests
from datetime import datetime as dt

def fetchData(site):
    if site == "farm":
        url = "http://afs102.tamu.edu:8080/?command=DataQuery&uri=Server:Farm%20Mesonet.Table10&format=toa5&mode=most-recent&p1=145&p2="
    elif site == "gardens":
        url = "http://afs102.tamu.edu:8080/?command=DataQuery&uri=Server:Gardens%20Meso.Table10&format=toa5&mode=most-recent&p1=145&p2="
    tenTable = requests.get(url)
    with open("input/"+site+"newData.csv", "w") as f:
        f.write(tenTable.text)
    if path.exists("input/"+site+".csv"):
        table = pd.read_csv("input/"+site+".csv")
        table = table.set_index(["datetimes"])
        newTable = pd.read_csv("input/"+site+"newData.csv", skiprows=1).dropna().iloc[1:].reset_index(drop=True)
        newTable["datetimes"] = pd.to_datetime(newTable["TIMESTAMP"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        newTable = newTable.set_index(["datetimes"])
        table = pd.concat([table, newTable]).drop_duplicates()
        remove("input/"+site+"newData.csv")
        remove("input/"+site+".csv")
        table.to_csv("input/"+site+".csv")
    else:
        newTable = pd.read_csv("input/"+site+"newData.csv", skiprows=1).dropna().iloc[1:].reset_index(drop=True)
        newTable["datetimes"] = pd.to_datetime(newTable["TIMESTAMP"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        newTable.set_index(["datetimes"])
        newTable.to_csv("input/"+site+".csv")
        remove("input/"+site+"newData.csv")

if __name__ == "__main__":
    fetchData("farm")
    fetchData("gardens")
    inputDir = "input/"
    for file in listdir(inputDir):
        campTable = pd.read_csv(path.join(inputDir, file))
        campTable["datetimes"] = pd.to_datetime(campTable["datetimes"])
        campTable = campTable.set_index(["datetimes"])
        campTable = campTable.sort_index().loc["2021-01-01":]
        campTable["AvgAT"] = campTable["AvgAT"].astype(float)
        campTable["rollingAT"] = campTable["AvgAT"].rolling("1D").mean()
        dtlist = campTable.index.values
        atlist = campTable["AvgAT"].to_list()
        rollingAtList = campTable["rollingAT"]
        fig = plt.figure()
        px = 1/plt.rcParams["figure.dpi"]
        ax = fig.gca()
        ax.plot(dtlist, atlist, "red", label="Air temperature")
        ax.plot(dtlist, rollingAtList, "blue", label="24-hour rolling average temperature")
        ax.legend(bbox_to_anchor=(0.2, -0.05))
        fig.subplots_adjust(bottom = 0.21)
        fig.subplots_adjust(top = 0.95)
        fig.subplots_adjust(right = 0.95)
        fig.subplots_adjust(left = 0.05)
        fig.set_size_inches(1920*px, 1080*px)
        ax.set_title("TAMU Mesonet -- Gardens Site\nAverage Air Temperature")
        lax = fig.add_axes([.75,0.01,0.2,0.2])
        lax.set_xlabel("Python HDWX -- Send bugs to stgardner4@tamu.edu")
        lax.set_aspect(2821/11071)
        plt.setp(lax.spines.values(), visible=False)
        lax.tick_params(left=False, labelleft=False)
        lax.tick_params(bottom=False, labelbottom=False)
        plt.setp(lax.spines.values(), visible=False)
        atmoLogo = mpimage.imread("assets/atmoLogo.png")
        lax.imshow(atmoLogo)
        fig.savefig("test.png")