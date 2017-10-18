from flask import Flask, render_template, request
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from py import utils

#import global variables
GLOBAL = utils.getGlobals()
#set up the app
rent_app = Flask(__name__)
#connect to the database
engine = create_engine(GLOBAL['db_name'])

@rent_app.route("/")
def home():
    return render_template('template.html')

@rent_app.route('/table', methods=['POST'])
def search_results():
    #read user input
    form_list = ['borough','min_price','max_price','beds','baths','sortby']
    user_input = {}
    for f in form_list:
        user_input[f] = request.form[f]
    #determine query based on user input
    sql = utils.getSQL(user_input,GLOBAL['data_table'],"data_id, address, borough, price, sq_ft, beds, baths, neighborhood")
    #query the database
    df = pd.read_sql(sql,engine)
    #formatting, replace missing values with dashes
    df.replace(-1, '-', inplace=True) #replace missing values
    n_results = df.shape[0]
    #draw the table
    return render_template('template3.html',n_results=n_results,df=df)

@rent_app.route('/results', methods=['POST'])
def results():
    #read user input
    listing_id = request.form['listing_id']
    #query the database for the requested listing
    sql = "SELECT * FROM %s WHERE data_id = %s;" % (GLOBAL['data_table'],listing_id)
    df_listing = pd.read_sql(sql,engine)
    #save some listing information for display before formatting
    listing_info = {}
    for i in ['price','address','neighborhood','borough','beds','baths','sq_ft']:
        listing_info[i] = df_listing[i][0]
        if i == 'price' or i == 'beds' or i == 'baths' or i == 'sq_ft':
            listing_info[i] = int(listing_info[i])
        if listing_info[i] == -1: listing_info[i] = '-' #replace missing values
    #format the dataframe for modeling
    df_listing = utils.format_data(df_listing, GLOBAL['trans'],GLOBAL['data_table'],engine)
    #load the fitted bootstrapped coefficients
    df_coef = pd.read_sql(GLOBAL['coef_table'], engine).T
    df_coef.columns = df_coef.iloc[1]
    df_coef = df_coef.drop(['key','feat'],axis=0)
    #convert to appropriate form for model evaluation
    df_coef = df_coef.sort_index('columns')
    df_listing = df_listing.sort_index('columns')
    df_listing = df_listing.applymap(lambda x:float(x)) #convert int to float
    #get model prediction for all sets of coef
    pred = df_listing.dot(df_coef.T)
    mean_pred = int(np.mean(pred,axis=1))
    ci_low = int(np.percentile(pred,2.5))
    ci_high = int(np.percentile(pred,97.5))
    #draw the page
    return render_template('template2.html', mean_pred=mean_pred, ci_low=ci_low, ci_high=ci_high, price=listing_info['price'], listing_info=listing_info)

#Need to develop forms to get input from the user
if __name__ == "__main__":
    rent_app.run()