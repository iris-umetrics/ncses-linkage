#!/usr/bin/env python
# coding: utf-8

# # Overview
# 
# This notebook contains code to clean and normalize person name data. It is designed to work with a source_names.csv file, which contains the following fields:
# 
# 1. first_name: This should actually be a concatenation of a first name and a middle name, as per descriptions of the SED/SDR PII data structure
# 2. last_name: the last name
# 3. complete_name: This should be all of the name data concatenated together (first_name + last_name)
# 4. mob: month of birth
# 5. yob: year of birth
# 
# Steps:
# 1. Pull in name file
# 2. Pull in nickname lookup file
# 3. Apply the name cleaning function to relevant fields
# 4. Apply the nickname normalization function to relevant fields
# 5. Output a production CSV to be passed to hashing script

# # Setup

# ## Imports

# In[197]:


import string
import unidecode

import numpy as np
import pandas as pd


# ## Directories
# 
# By default, all files will be read from and output to the same directory as the code. This can be adjusted if desired.
# 

# In[198]:


root_path = '.'
path_separator = '/'

input_directory_name = ''
output_directory_name = ''

input_directory = root_path + path_separator + input_directory_name
output_directory = root_path + path_separator + output_directory_name


# ## File/Field Names
# 
# These variables will need to be changed to match your name and lookup file if they differ from the established defaults. If column names differ from the default they can be changed here as well.

# In[199]:


#File Names
name_file = 'source_names'
lookup_file = 'nickname_lookup'
backup_lookup_file = 'backup_nickname_mapping'


# There are 2 options to use for lookup:
# 1. American English Nickname Collection (https://catalog.ldc.upenn.edu/LDC2012T11) (AENC_create_lookup script output)
# 2. Back-up Nickname lookup file (with 3,685 name pairs)

# #### Option 1

# In[206]:


#Load lookup table
lookup_input = pd.read_csv(input_directory+lookup_file+'.csv', encoding= 'utf_8',dtype='object',keep_default_na=False)


# #### Option 2

# In[ ]:


#Load backup lookup table
lookup_input = pd.read_csv(input_directory+backup_lookup_file+'.csv', encoding= 'utf_8',dtype='object',keep_default_na=False)


# In[200]:


#Field Names

#This code is designed to work with both the first name and middle name being contained in the same field,
#concatenated together with a space
fandmname = 'first_name'
lname = 'last_name'
cname = 'complete_name'
mob = 'mob'
yob = 'yob'


# # Ingest Data

# In[201]:


#PII files must be UTF-8 compliant
name_input = pd.read_csv(input_directory+name_file+'.csv', encoding= 'utf_8',dtype='object',keep_default_na=False)


# In[202]:


#View input data
name_input.head()


# # Clean Names/MOB/YOB
# 
# This section cleans the name and month of birth fields. First, if first names have multiple words in them only the first word is kept in the first name field, and any other words are prepended to the middle name field. This is done to enforce consistency with a cleaning process that happens on UMETRICS data, as middle initials/names in the first name field are relatively common in that dataset. Then, all non-ascii characters are replaced with ascii equivalents, all characters are converted to lowercase, and any non-letter character is eliminated. For months, any leading zeros are removed and any value other than 1-12 is eliminated. Then years are cleaned by removing any years outside of 1902-2009. These are the years for which there is valid UMETRICS data.

# ## Define Functions

# In[203]:


def clean_name_part(original):
    working = original
    # Strip unicode down to ascii (e.g. Ë becomes E; ñ becomes n)
    working = unidecode.unidecode_expect_ascii(working)
    # Make all lowercase
    working = working.lower()
    # Remove absolutely everything except the lowercase letters (via ASCII codes)
    working = "".join(c for c in working if c in string.ascii_lowercase)
    return working

def clean_month(input_month):
    working_month = input_month
    #Strip out any leading zeros
    working_month = working_month.lstrip('0')
    #Only accept values from 1-12
    if working_month not in [str(x) for x in range(1,13)]:
        working_month = ''
    return working_month

def clean_year(input_year):
    working_year = input_year
    #In tests on the UMETRICS YOB data, YOB values prior to 1902 were only used as placeholders for NULL
    if working_year not in [str(x) for x in range(1902,2010)]:
        working_year = ''   
    return working_year


# ## Cleaning

# In[204]:


#Put cleaned values in a new dataframe
name_working = name_input

#Create a raw version of the first name field for easy comparison/error checking
fandmname_raw = fandmname + '_raw'
name_working[fandmname_raw] = name_working[fandmname]

#UMETRICS parsed data for matching uses only the first word as a first name
#Any additional names are moved to the middle
#Removing middle names from first names
name_working['middle_name_prepend'] = name_working[fandmname].str.split().str[1:].apply(lambda x: ''.join([str(i) for i in x]))
name_working['middle_names'] = name_working['middle_name_prepend'] #+ name_working[mname]
name_working[fandmname] = name_working[fandmname].str.split().str[0]
name_working.drop('middle_name_prepend',axis=1,inplace=True)
name_working['middle_initial'] = name_working['middle_names'].str[0]

#Replace any NaN values added by the first name manipulation
name_working.fillna('',inplace=True)

#Clean names
name_working[[fandmname,'middle_names','middle_initial',lname,cname]] = name_working[[fandmname,'middle_names','middle_initial',lname,cname]].applymap(clean_name_part)
#Clean months
name_working[mob] = name_working[mob].apply(clean_month)

name_working[yob] = name_working[yob].apply(clean_year)


# In[205]:


#View cleaned data
name_working.head()


# # Name Alias Lookup
# 
# Many names have multiple aliases (e.g. Robert, Rob, Bob, etc.) This section groups names based on common name-alias pairings using the output of the AENC_create_lookup script, then applies a single value to each group

# In[207]:


#Convert name values to lowercase
lookup_input['raw_name'] = lookup_input['raw_name'].str.lower()
lookup_input['name_group'] = lookup_input['name_group'].str.lower()


# In[208]:


#Join the alias table and the name table
alias_working = name_working.merge(lookup_input,how='left',left_on=fandmname,right_on='raw_name')
#Generate a flag to track the names impacted by the alias change for QA purposes
alias_working['alias_impact_flag'] = np.where(alias_working[fandmname] == alias_working['raw_name'],1,0)
#Create a "first_nickname" field that contains the matching alias
#The original cleaned first name is maintained so that matches can be run on both hashes
alias_working['first_nickname'] = alias_working['name_group'].fillna(alias_working[fandmname])
alias_working.drop(['raw_name','name_group'],axis=1,inplace=True)


# # Export CSV
# 
# This script will create a file in the output directory named "clean_names.csv" that can be loaded into the hashing script. It can also generate a QC CSV for looking at the changes to the data.

# In[209]:


#Output a QC csv that has raw names and the alias impact flag
#name_QC = alias_working[[fandmname,'first_nickname','middle_names','middle_initial',lname,cname,mob,yob,fandmname_raw,'alias_impact_flag']]
#name_QC.to_csv(output_directory+'clean_names_QC.csv', encoding='utf_8', index=False)


# In[210]:


#Arrange the columns in order
name_cleaned = alias_working[[fandmname,'first_nickname','middle_names','middle_initial',lname,cname,mob,yob]]
#Export production file
name_cleaned.to_csv(output_directory+'clean_names.csv', encoding='utf_8', index=False)

