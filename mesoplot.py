#!/usr/bin/env python3
# TAMU Mesonet timeseries creation for next-gen HDWX
# Created 16 September 2021 by Sam Gardner <stgardner4@tamu.edu>

import pandas as pd
from os import path, listdir
from matplotlib import pyplot as plt
from matplotlib import image as mpimage


if __name__ == "__main__":
    inputDir = "input/"
    for file in listdir(inputDir):
        campTable = pd.read_csv(path.join(inputDir, file), skiprows=1)
        campTable["pd_datetimes"] = pd.to_datetime(campTable["TIMESTAMP"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        campTable = campTable.dropna().reset_index()
        campTable["datetimes"] = [campTable["pd_datetimes"][i].to_pydatetime() for i in range(0, len(campTable))]
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