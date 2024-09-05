#!/usr/bin/env python
#-*- coding=utf-8 -*-
#filename: monitor_dir.py
import os
import time
monitor_dir = "./"
now_file = dict([(f,None)for  f in os.listdir(monitor_dir)])
while True:
    new_file = dict([(f,None)for  f in os.listdir(monitor_dir)])
    added = [f for f in new_file if not f in now_file]
    removed = [f for f in now_file if not f in new_file]
    if added:
        print ("Added:",",".join(added))
        file_name = added[0]
        print(file_name)
        try:
            file_type = file_name.split(".")[-1]
            file = file_name.split(".")[0]
            new_r_file = "./new/" + file + "." + file_type
            tmp_file = "./new/" +file+".txt"
            os.rename(file_name,tmp_file)
            os.rename(tmp_file ,new_r_file)
        except:
            print("error")
    if removed:
        print ("Removed:",",".join(removed))
    now_file = new_file