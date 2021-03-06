#!/usr/bin/env python

# Dependencies

from lxml import html, etree
#url management library
import requests
#Data management library
import pandas as pd
#Time management library
import datetime as dt
# Database Library
import numpy as np
# open floorplan
import io
import pytesseract
from PIL import Image

class rightmove_data(object):
    """The rightmove_data web scraper works by implementing an instance of the class 
    on the URL returned by a search on the rightmove website. Go to rightmove.co.uk
    and search for whatever you want, then create an instance of the class on the URL 
    returned by the search. The class returns an object which includes various 
    methods for extracting data from the search results, the most useful being the 
    .get_results() method which returns all results as a pandas DataFrame object.
    """
    
    def __init__(self, url):
        # FG the self variable represents the instance of the object itself.
        # FG declared explicitly
        # FG __init__ method represents a constructor in Python.
        # FG call rightmove_data() Python creates an object and passes it as the first parameter to the __init__ method.
        # FG Any additional parameters (url) will also get passed as argument
        self.url = url
        
        # determine if the url is a property search result. works for rent and sale
        try:
            if "searchType=SALE" in self.url or "property-for-sale" in self.url:
                self.rent_or_sale = "SALE"
            elif "searchType=RENT" in self.url or "property-to-rent" in self.url:
                self.rent_or_sale = "RENT"
        except ValueError:
            print("Not a valid rightmove search URL.")
        
        # the number of search results
        self.results_count = self.__results_count()
        # the number of pages to get all the results
        self.result_pages_count = self.__result_pages_count()


    def __results_count(self):
        """Returns an integer of the total number of results returned by the search URL."""
        
        # FG pind the url for information
        page = requests.get(self.url)
        # FG Get the content of the hhtp/url and parse it using the html module
        tree = html.fromstring(page.content)
        # FG 
        xp_result_count = """//span[@class="searchHeader-resultCount"]/text()"""
        # FG query in tree for the result count on the page
        return int(tree.xpath(xp_result_count)[0].replace(",", ""))

    
    def __result_pages_count(self):
        """Returns the number of result pages returned by the search URL.
        There are 24 results on each results page, but note that the
        rightmove website limits results pages to a maximum of 42 pages."""

        page_count = self.results_count // 24
        
        if self.results_count % 24 > 0:
            page_count += 1

        # Rightmove will return a maximum of 42 results pages, hence:
        if page_count > 42: page_count = 42

        return page_count

    def __get_individual_info(self,property_url):
        """This is a hidden method to scrape the data from the individual property page
           It is used iteratively by the .get_results() and _get_page_results
           """
        # Set the xpaths for the description
        xp_keyfeatures = """//div[@class="sect key-features"]\
                           //ul[@class="list-two-col list-style-square"]//li/text()"""
        xp_desc = """//div[@class="sect "]\
                     //p[@itemprop="description"]/text()"""
        xp_firstlisted =  """//div[@id="firstListedDateValue"]/text()"""
        
        # Set the xpaths for the geo location of the property
        xp_latlong = """//div[@class="pos-rel"]\
                        //a[@class="block js-tab-trigger js-ga-minimap"]\
                       //img/@src"""
         
        # set the path for the floorplan
        xp_floorplan = """//div[@class="zoomableimagewrapper"]\
                          //img/@src"""
        
        
        
        # Use the requests library to get the whole web page.
        page = requests.get(property_url)

        # Process the html.
        tree = html.fromstring(page.content)
        
        # Create data lists from Xpaths.
        fd = tree.xpath(xp_firstlisted)
        if len(fd)!=0 : firstd =fd[0]
        else: firstd = fd  
        firstlisted = pd.to_datetime(firstd, dayfirst=True,format= '%d %B %Y',errors='ignore')        
        # any text describing the property
        list_key_features = tree.xpath(xp_keyfeatures)
        keyfeatures = ' '.join(list_key_features) 
        keyfeatures = keyfeatures.replace('/',' ')
        desc = tree.xpath(xp_desc)
        description = ' '.join(desc) 
        #the full text available to mininge
        description = description+' '+ keyfeatures
        #the unique words in the description
        descWords =list(set(description.replace('/',' ').replace('.','').replace('\'','').replace(',','').lower().split()))

        #try to find the square footage 
        regex = r'(?<= )(\d\d*[,\.]?\d+)+(?=[ .]?sq)'
        listsqftage=re.findall(regex,description.lower())
        f=[float(i.replace(',',''))for i in listsqftage]
        if len(f)!=0 : sqftage=float(max(f))
        else: sqftage = f  
        
        # find square footage in the floorplan
        floorplan_urls = tree.xpath(xp_floorplan)
        if len(floorplan_urls)!=0 : 
            floorplan_url =floorplan_urls[0]
#           print(floorplan_url)
            response = requests.get(floorplan_url)
            #print( type(response) ) # <class 'requests.models.Response'>
            flrpln = Image.open(io.BytesIO(response.content))
            #print( type(flrpln) ) # <class 'PIL.JpegImagePlugin.JpegImageFile'>
            text = pytesseract.image_to_string(flrpln)
            print( text )
        else: floorplan_url = floorplan_urls  
        
      
        
        
        # Latitute longitude
        latlongs = tree.xpath(xp_latlong)
        latlong=' '.join(latlongs)
        regexlat = r'(?<=latitude=)(-?\d\d*[\.]?\d+)'
        regexlon = r'(?<=longitude=)(-?\d\d*[\.]?\d+)'
        lat=re.findall(regexlat,latlong)
        if len(lat)!=0 : latitude=lat[0]
        else: latitude = lat
        lon = re.findall(regexlon,latlong)
        if len(lon)!=0 : longitude= lon[0]
        else: longitude = lon
        
        
        
        return [latitude , longitude , descWords , sqftage , firstlisted]
    
    def __get_page_results(self,page_url):
        """This is a hidden method to scrape the data from a single page
        of search results. It is used iteratively by the .get_results()
        method to scrape data from every page returned by the search."""

        # Set the correct xpath for the price.
        if self.rent_or_sale == "RENT":
            xp_prices = """//span[@class="propertyCard-priceValue"]/text()"""
        elif self.rent_or_sale == "SALE":
            xp_prices = """//div[@class="propertyCard-priceValue"]/text()"""

        # Set the xpaths for listing title, property address, 
        # listing URL, and agent URL.
        xp_titles = """//div[@class="propertyCard-details"]\
        //a[@class="propertyCard-link"]\
        //h2[@class="propertyCard-title"]/text()"""
        xp_addresses = """//address[@class="propertyCard-address"]//span/text()"""
        xp_layus = """//div[@class="propertyCard-description"]\
        //a[@class="propertyCard-link"]//span/text()"""
        xp_addedon = """//div[@class="propertyCard-detailsFooter"]\
        //div[@class="propertyCard-branchSummary"]\
        //span[@class="propertyCard-branchSummary-addedOrReduced"]/text()"""
        xp_weblinks = """//div[@class="propertyCard-details"]\
        //a[@class="propertyCard-link"]/@href"""
     
        # Use the requests library to get the whole web page.
        page = requests.get(page_url)

        # Process the html.
        tree = html.fromstring(page.content)
        
        # Create data lists from Xpaths.
        price_pcm = tree.xpath(xp_prices)
        titles = tree.xpath(xp_titles)
        addresses = tree.xpath(xp_addresses)
        laius = tree.xpath(xp_layus)
        addedon = tree.xpath(xp_addedon)
        urlbase = "http://www.rightmove.co.uk"
        weblinks = ["{}{}".format(urlbase, tree.xpath(xp_weblinks)[val]) \
                    for val in range(len(tree.xpath(xp_weblinks)))]
               
        ######### obtain the supplementary info on individual pages
        latitude =[]
        longitude = []
        descwords=[]
        sqftage=[]
        firstlisted=[]
        i=0
        for weblink in weblinks:
            if weblink != urlbase:
                info = self.__get_individual_info(weblink)
                latitude.append(info[0])
                longitude.append(info[1])
                descwords.append(info[2])
                sqftage.append(info[3])
                firstlisted.append(info[4])
                # type here the floorplan retrieval and processsing
       
          
        # Store the data in a temporary pandas DataFrame.
        data = [price_pcm, titles, addresses, laius, addedon , weblinks , latitude , longitude , descwords , sqftage , firstlisted]
       
        temp_df = pd.DataFrame(data)
       
        temp_df = temp_df.transpose()
        temp_df.columns = ["price", "type", "address", "short desc", "listing date",'url','latitude','longitude', 'descwords','sqftage','firstlisted' ]
        
        # Drop empty rows which come from placeholders in the html.
        temp_df = temp_df[temp_df["address"].notnull()]
        
        return temp_df
    

                
    def get_results(self):
        """Returns a pandas DataFrame with all results returned by the search."""

        # Create DataFrame to store results.
        full_results = pd.DataFrame(columns={"price", "type", "address", "short desc", "listing date",'url','latitude','longitude', 'descwords','sqftage','firstlisted' })
        # Iterate through pages of results, using the .__get_page_results method to scrape results.
        for page in range(0, self.result_pages_count+1, 1):

            # Create the URL of the specific results page.
            iteration_url = "{}{}{}".format(str(self.url), "&index=", str((page*24)))

            # Create a temporary dataframe of the page results.
            temp_df = self.__get_page_results(iteration_url)

            # Concatenate the temporary dataframe with the full dataframe.
            frames = [full_results, temp_df]
            full_results = pd.concat(frames)

        # Reset the index.
        full_results = full_results.reset_index(drop=True)

        # Convert price column to numeric type.
        full_results.price.replace(regex=True, inplace=True, to_replace=r"\D", value=r"")
        full_results.price = pd.to_numeric(full_results.price)

        # Extract postcodes to a separate column.
        full_results["postcode"] = full_results["address"].str.extract\
        (r"\b([A-Za-z][A-Za-z]?[0-9][0-9]?[A-Za-z]?)\b", expand=True)

        # Extract creation/modification date to a separate column.
        date_cond =    [full_results["listing date"].str.contains("today"),
                        full_results["listing date"].str.contains("yesterday"),
                        (~full_results["listing date"].str.contains("today") & ~full_results["listing date"].str.contains("yesterday"))]
        date_choices = [ dt.date.today().strftime( '%d/%m/%Y'),
                         (dt.date.today()-dt.timedelta(1)).strftime( '%d/%m/%Y'),
                         pd.to_datetime(full_results["listing date"].str[-10:],
                                       dayfirst=True,format= '%d/%m/%Y',errors='ignore')]
        full_results['date'] = np.select(date_cond, date_choices) 
                
        full_results["date_type"] = full_results["listing date"].str[:-10]
        full_results["date_Type"] = full_results["date_type"].str.strip()
        
         # Extract RM property ID
        full_results["RM_ID"] = full_results["url"].str[54:-5]
        
        #######Below we extract underlying information from type
        # Extract number of bedrooms from "type" to a separate column.
        full_results["number_bedrooms"] = full_results.type.str.extract(r"\b([\d][\d]?)\b", expand=True)
        full_results.loc[full_results["type"].str.contains("studio", case=False), "number_bedrooms"]=0
        full_results["number_bedrooms"]=full_results["number_bedrooms"].astype(float)
        # House, flat, detached, semi detached terraced penthouse duplex triplex
        full_results['flat'] = full_results.type.str.contains('apartment|flat|plex|maisonette|penthouse')
        full_results['house'] = ~full_results.type.str.contains('apartment|flat|plex|maisonette|penthouse|land|plot')
        full_results['detached'] = full_results.type.str.contains("detached") & ~full_results.type.str.contains("semi")
        full_results['semi-d'] = full_results.type.str.contains('semi')
        full_results['penthouse'] = full_results.type.str.contains('penthouse')
        full_results['duplex'] = full_results.type.str.contains('plex')
        full_results['land'] = full_results.type.str.contains('land|plot')
        full_results['offplan'] = full_results.type.str.contains('off-plan')
        
        # Clean up annoying white spaces and newlines in "type" column.
        for row in range(len(full_results)):
            type_str = full_results.loc[row, "type"]
            clean_str = type_str.strip("\n").strip()
            full_results.loc[row, "type"] = clean_str

        # Add column with datetime when the search was run (i.e. now).
        now = dt.datetime.today()
        full_results["search_date"] = now
        
        # Remove superfluous columns and data
        full_results = full_results.drop(['listing date'], axis= 1)

        return full_results
