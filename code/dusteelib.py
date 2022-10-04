import requests
import sentinelsat
import gdal
import os
from shutil import copyfile
from xml.etree import ElementTree as et
import datetime as dt
from sentinelsat.sentinel import SentinelAPI

def clean_downloaded(products,a):
    for product_ID in iter(products):
        product_path = a[0][product_ID]['path']
        if os.path.exists(product_path):
            os.remove(product_path)
        tif = product_path.replace('.zip','.tif')
        if os.path.exists('tmpfile.tif'):
            os.remove('tmpfile.tif')
        if os.path.exists(tif):
            os.remove(tif)
            try:
                os.remove(tif+'.aux.xml')
            except:
                print(tif+'.aux.xml does not exist')

def s5p2geotiff(product_path, product_type):
    if os.path.exists('lon.vrt'):
        os.remove('lon.vrt')
        os.remove('lat.vrt')
    if os.path.exists(product_type+'.vrt'):
        os.remove(product_type+'.vrt')
    if product_type == 'no2':
        strtype='nitrogendioxide_tropospheric_column'
    if product_type == 'aerosols':
        strtype='aerosol_index_340_380'
    os.system('gdal_translate -of VRT HDF5:"'+product_path+'"://PRODUCT/longitude lon.vrt')
    os.system('gdal_translate -of VRT HDF5:"'+product_path+'"://PRODUCT/latitude lat.vrt')
    os.system('gdal_translate -of VRT HDF5:"'+product_path+'"://PRODUCT/'+strtype+' '+product_type+'.vrt')
    tree = et.parse(product_type+'.vrt')
    root = tree.getroot()
    xml_geo = et.SubElement(root, 'Metadata')
    xml_geo.attrib["domain"] = 'GEOLOCATION'
    latinfo = et.SubElement(xml_geo, 'mdi')
    latinfo.attrib["key"] = 'X_DATASET'
    latinfo.text = 'lon.vrt'
    latinfo2 = et.SubElement(xml_geo, 'mdi')
    latinfo2.attrib["key"] = 'X_BAND'
    latinfo2.text = '1'
    loninfo = et.SubElement(xml_geo, 'mdi')
    loninfo.attrib["key"] = 'Y_DATASET'
    loninfo.text = 'lat.vrt'
    loninfo2 = et.SubElement(xml_geo, 'mdi')
    loninfo2.attrib["key"] = 'Y_BAND'
    loninfo2.text = '1'
    pixof = et.SubElement(xml_geo, 'mdi')
    pixof.attrib["key"] = 'PIXEL_OFFSET'
    pixof.text = '0'
    linof = et.SubElement(xml_geo, 'mdi')
    linof.attrib["key"] = 'LINE_OFFSET'
    linof.text = '0'
    pixst = et.SubElement(xml_geo, 'mdi')
    pixst.attrib["key"] = 'PIXEL_STEP'
    pixst.text = '1'
    linst = et.SubElement(xml_geo, 'mdi')
    linst.attrib["key"] = 'LINE_STEP'
    linst.text = '1'
    tree.write(product_type+'.vrt')
    outname = product_path.replace('.zip','.tif')
    ds = gdal.Warp(outname, product_type+'.vrt',format = 'GTiff',
               warpOptions = [ 'dstSRS=EPSG:4326', 'geoloc=True', 'srcNodata=9.96921e+36', 'dstNodata=9999'])
    return outname

def s5down(datum = str(dt.date.today()), product_type = 'no2'):
    # this function will download s5p data of given product_type for given date
    # e.g. s5down('2019-08-15','no2')
    if product_type == 'no2':
        strtype='L2__NO2___'
    if product_type == 'aerosols':
        strtype='L2__AER_AI'
    datum = dt.datetime.strptime(datum,'%Y-%m-%d').date()
    time_in = dt.datetime.combine(datum, dt.time(0,0))
    time_out = dt.datetime.combine(datum, dt.time(23,59))
    api = SentinelAPI('s5pguest', 's5pguest', 'https://s5phub.copernicus.eu/dhus')
    #coordinates for CZ:
    footprint = 'POLYGON((12.278971773041526 48.69059060056844,18.98957262575027 48.69059060056844,18.98957262575027 51.081759060281655,12.278971773041526 51.081759060281655,12.278971773041526 48.69059060056844))'
    products = api.query(footprint,
                     date = (time_in, time_out),
                     platformname = 'Sentinel-5',
                     producttype=strtype)
    print('there are '+str(len(products))+' products found')
    a = api.download_all(products)
    geotiffs = []
    for product_ID in iter(products):
        product_path = a[0][product_ID]['path']
        print('converting '+product_path+' to geotiff')
        geotiffs.append(s5p2geotiff(product_path,product_type))
    if not geotiffs:
        print('some error happened, no geotiffs generated')
        clean_downloaded(products,a)
        return None
    tifstring = ''
    for tif in geotiffs:
        tifstring = tifstring + ' '+ tif
    print('merging geotiffs to '+str(datum)+'.tif and cropping for CZ extents')
    outfile = str(datum)+'.'+product_type+'.tif'
    tmpfile = 'tmp.tif'
    os.system('gdal_merge.py -o merged.tif -of GTiff -ul_lr 11.3867 51.4847 19.943 47.7933 -a_nodata 9999 '+tifstring)
    if product_type == 'no2':
        #need to compute 1000x
        gdal_calc = 'gdal_calc.py -A merged.tif --outfile='+tmpfile+' --calc="(A*1000 > 0)*(A * 1000 < 0.7)*(A * 1000)" --overwrite'
        print(gdal_calc)
        os.system(gdal_calc)
    else:
        tmpfile='merged.tif'
    #now oversample using cubic..
    gdalwarp = 'gdalwarp -tr 0.015 0.015 -r cubicspline -dstnodata 9999 -srcnodata 9999 '+tmpfile+' '+outfile
    #gdalwarp = 'gdalwarp -s_srs EPSG:4326 -t_srs EPSG:4326 -tr 0.015 0.015 -r cubicspline -dstnodata 9999 -srcnodata 9999 temp1000.tif '+outfile
    print(gdalwarp)
    os.system(gdalwarp)
    print('(the file will be also saved as {}.tif)'.format(product_type))
    copyfile(outfile, '../data/'+product_type+'.tif')
    #cleaning
    clean_downloaded(products,a)
    return geotiffs

def colorize_tif(tiffile, producttype):
    if producttype=='no2':
        palette = """
0.57 103   0  31
0.5 178  24  43
0.438 214  96  77
0.375 244 165 130
0.313 253 219 199
0.25 209 229 240
0.188 146 197 222
0.125 67 147 195
0.062 33 102 172
0  5  48  97
nv 255 255 255   0
"""
    if producttype == 'aerosols':
        palette = """
1 103   0  31
0.778 178  24  43
0.556 214  96  77
0.333 244 165 130
0.111 253 219 199
-0.111 209 229 240
-0.333 146 197 222
-0.556 67 147 195
-0.778 33 102 172
-1  5  48  97
nv 255 255 255 0
"""
    if producttype == 'pm10-24':
        palette = """
50 103   0  31
45 178  24  43
40 214  96  77
35 244 165 130
25 253 219 199
20 209 229 240
15 146 197 222
10 67 147 195
5 33 102 172
0  5  48  97
nv 255 255 255 0
"""
    if producttype == 'pm10':
        palette = """
200 103   0  31
150 178  24  43
125 214  96  77
100 244 165 130
75 253 219 199
60 209 229 240
45 146 197 222
30 67 147 195
20 33 102 172
10  5  48  97
nv 255 255 255 0
"""
    if not os.path.exists('pal_'+producttype+'.txt'):
        with  open('pal_'+producttype+'.txt','w') as myfile:
            myfile.write(palette)
    gdaldem = 'gdaldem color-relief -alpha '+tiffile+' pal_'+producttype+'.txt -of GTiff temp.tif'
    print(gdaldem)
    os.system(gdaldem)
    os.remove(tiffile)
    os.rename('temp.tif',tiffile)

def geocode(address):
    geocode_url = "https://www.google.com/maps/search/{}".format(address)
    results = requests.get(geocode_url)
    page = results.text
    loc = page.find('staticmap?center=')
    stripe = page[loc:loc+100]
    coords = stripe.split('=')[1].split('&')[0]
    lat = coords.split('%2C')[0]
    lon = coords.split('%2C')[1]
    latlon = [float(lat), float(lon)]
    return latlon

def meteo_stations_generate(pollut = "pm10-24"):
    #measurement options are:
    # pm10
    # pm10-24
    # no2
    # so2
    # co

    #vrt and csv are temporary for geotiff, fn_points is to be loaded to leaflet directly
    fn_vrt = "meteo_"+pollut+".vrt"
    fn_csv = "meteo_"+pollut+".csv"
    fn_points = "meteo."+pollut

    file_points = open(fn_points,"w+")
    file_csv = open(fn_csv,"w+")

    file_points.write('var meteopoints_'+pollut.replace('-','')+' = [\n')
    file_csv.write('X, Y, Z\n')
    
    # get current list of stations
    print('getting list of stations')
    url = 'https://jkav8s04il.execute-api.eu-west-1.amazonaws.com/Prod/stations'
    results = requests.get(url)
    page = results.text
    stations = page.split('{"code":')
    
    # extract information for given pollution type from the stations
    print('getting pollution measurements for '+pollut)
    pom=0
    for station in stations:
        if len(station)>5:
            code = station.split('"')[1]
            lat = station.split('"latitude":')[1].split('"')[1]
            lon = station.split('"longitude":')[1].split('"')[1]
            url_station = "https://jkav8s04il.execute-api.eu-west-1.amazonaws.com/Prod/stations/{}/state?history=1".format(code)
            results = requests.get(url_station)
            page = results.text
            try:
                pollut_value = page.split('"'+pollut+'":')[1].split('"')[1]
            except:
                pollut_value = None
            if pollut_value:
                file_csv.write('{0}, {1}, {2}\n'.format(lon, lat, pollut_value))
                if pom == 0:
                    file_points.write('   [ {0}, {1}, {2} ]'.format(lat, lon, pollut_value))
                    pom = 1
                else:
                    file_points.write(',\n   [ {0}, {1}, {2} ]'.format(lat, lon, pollut_value))
    file_points.write('];')
    file_points.close()
    file_csv.close()
    
    # prepare vrt file
    with open(fn_vrt, 'w') as file_vrt:
        file_vrt.write('<OGRVRTDataSource>\n')
        file_vrt.write('\t<OGRVRTLayer name="meteo_{}">\n'.format(pollut))
        file_vrt.write('\t\t<SrcDataSource>{}</SrcDataSource>\n'.format(fn_csv))
        file_vrt.write('\t\t<GeometryType>wkbPoint</GeometryType>\n')
        file_vrt.write('\t\t<GeometryField encoding="PointFromColumns" x="X" y="Y" z="Z"/>\n')
        file_vrt.write('\t</OGRVRTLayer>\n')
        file_vrt.write('</OGRVRTDataSource>\n')
    # interpolating to geotiff - double  dimensions as S5P images
    gdalcmd = 'gdal_grid -ot Float32 -of GTiff -zfield Z -a_srs EPSG:4326 -clipsrc 11.3867 47.7933 19.9667 51.4847 \
          -l meteo_{0} -a invdist:power=2.0:smoothing=0.001 -outsize 1200 1200 meteo_{0}.vrt meteo_{0}.tif'.format(pollut)   
    print(gdalcmd)
    os.system(gdalcmd)
    
    #colorize it
    colorize_tif('meteo_'+pollut+'.tif', pollut)
    os.remove(fn_csv)
    os.remove(fn_vrt)
