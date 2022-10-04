#!/usr/bin/env python

import sys, os
from dusteelib import *


def main():
    datum = sys.argv[1]
    #datum = '2019-08-20'
    product_type = sys.argv[2]
    #product_type = 'no2' or 'aerosols'

    temppath = '/home/lazecky/dustee/espigis/temp/'
    outpath = '/home/lazecky/dustee/espigis/data/'

    os.chdir(temppath)

    tiffile = str(datum)+'.'+product_type+'.tif'
    tilesdir = product_type+'.'+datum

    if os.path.exists(tiffile):
        os.remove(tiffile)
    
    if product_type in ['no2','aerosols']:
        #if yes, download from S5P data:
        #download and prepare NO2 data for given date
        bb = s5down(datum, product_type)
        if bb:
            print('first step done')
        else:
            print('some error')
            exit()
        colorize_tif(tiffile, product_type)
        #this will convert tif to mbtiles
        gdal2tiles='gdal2tiles.py -s EPSG:4326 -r bilinear -z 6-9 -w none '+tiffile+' '+tilesdir
    else:
        #if not, we will get the data from meteo points:
        meteo_stations_generate(product_type)
        #need higher zoom levels here
        gdal2tiles='gdal2tiles.py -s EPSG:4326 -r bilinear -z 6-11 -w none '+'meteo_'+product_type+'.tif '+tilesdir
    #gdal2tiles='gdal2tiles.py -r bilinear -z 6-9 -w none '+tiffile+' '+tilesdir
    print(gdal2tiles)
    os.system(gdal2tiles)
    #update meta xml file:
    #os.remove(tilesdir+'/tilemapresource.xml')
    #copyfile('tilemapresource.xml', tilesdir+'/tilemapresource.xml')

    #now to move it to the proper place
    os.rename(tilesdir,outpath+tilesdir)
    for tocopy in [ 'meteo.pm10-24', 'meteo.pm10' ]:
        if os.path.exists(tocopy):
            os.rename(tocopy,os.path.join(outpath,tocopy))

    #do the git update
    os.chdir(outpath)
    os.system('rm -r '+product_type)
    os.rename(tilesdir,product_type)
    with open('meta.'+product_type,'w') as f:
        f.write("let text"+product_type+" = '{0}';".format(str(datum)))
    os.chdir(outpath+'..')
    #this routine will renew the git repository, so the history will not expand
    os.system('git checkout --orphan temp_branch')
    os.system('git add -A')
    os.system('git commit -am "s5data {0}"'.format(str(datum)))
    os.system('git branch -D master')
    os.system('git branch -m master')
    os.system('git push -f origin master')
    os.chdir(temppath)
    print('all done, check webmap')

if __name__ == '__main__':
    main()
