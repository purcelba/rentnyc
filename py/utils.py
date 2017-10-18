import pandas as pd
import numpy as np


def getGlobals():
    """
    Import global variables in a dict
    :return:
    GLOBAL, dict, with the following keys
        'basic_vars', list of basic varaibles from streeteasy.com database.
        'amen', list of amenities variables
        'trans', list of transportation variables
        'all_cols', combined list of basic, amen, and trans variables
        'db_name', name of the database
        'coef_table', name of the coefficient table in the database
        'data_table', name of the data table in the database
    """
    #define a dict
    GLOBAL = {}
    #global variables
    GLOBAL['basic_vars'] = ["sq_ft","days_on_streeteasy","rooms","beds","baths","unit_type","neighborhood"]
    GLOBAL['amen'] = ['bike_room', 'board_approval_required', 'cats_and_dogs_allowed',
                 'central_air_conditioning', 'concierge', 'cold_storage', 'community_recreation_facilities',
                 'children_playroom', 'deck', 'dishwasher', 'doorman', 'elevator', 'full_time_doorman',
                 'furnished', 'garage_parking', 'green_building', 'gym', 'garden', 'guarantors_accepted',
                 'laundry_in_building', 'live_in_super', 'loft', 'package_room', 'parking_available',
                 'patio', 'pets_allowed', 'roof_deck', 'smoke_free', 'storage_available', 'sublet',
                 'terrace', 'virtual_doorman', 'washer_dryer_in_unit', 'waterview', 'waterfront']
    GLOBAL['trans'] = ["line_A", "line_C", "line_E", "line_B", "line_D", "line_F", "line_M", "line_G", "line_L", "line_J", "line_Z",
                  "line_N", "line_Q", "line_R", "line_1", "line_2", "line_3", "line_4", "line_5", "line_6", "line_7", "line_S",
                  "LIRR", "PATH"]
    GLOBAL['all_cols'] = GLOBAL['basic_vars'] + GLOBAL['amen'] + GLOBAL['trans']
    #define the SQL table names
    GLOBAL['db_name'] = 'sqlite:///streeteasy_db.sqlite'
    GLOBAL['coef_table'] = "coef_table"
    GLOBAL['data_table'] = "all_data"
    #return global
    return GLOBAL

def getSQL(user_input, table, select):
    """
    Reads user input from search_results form.
    Query the database and return results.
    Note that this function relies on INTERSECT which is not available in some SQL languages (e.g., MySQL).

    :params
        user_input: dict with following keys
            - borough, str, name of borough or 'Any'
            - min_price, str, minimum price or 'Any'
            - max_price, str, maximum price or 'Any'
            - beds, str, '1','2','3','>3', or 'Any'
            - baths, str, '1','2','3','>3', or 'Any'
            -sortby, str, field to sort by, 'borough', 'price', 'beds', or 'baths'
        table, str, name of table in the database
        select, str, variables to select from table
    :return:
        sql, str, sql query in string form satisfying requested param ranges
    """
    #start with baseline query imposing expected data range
    sql = "SELECT %s FROM %s WHERE price < 20000 AND sq_ft < 15000" % (select,table)
    #append additional conditions if needed
    if user_input['borough'] != 'Any':
        sql = sql + " INTERSECT SELECT %s FROM %s WHERE borough LIKE '%s'" % (select,table,user_input['borough'])
    if user_input['min_price'] != 'Any':
        sql = sql + " INTERSECT SELECT %s FROM %s WHERE price >= %d" % (select,table,int(user_input['min_price']))
    if user_input['max_price'] != 'Any':
        sql = sql + " INTERSECT SELECT %s FROM %s WHERE price <= %d" % (select, table, int(user_input['max_price']))
    if user_input['beds'] != '>3' and user_input['beds'] != 'Any':
        sql = sql + " INTERSECT SELECT %s FROM %s WHERE beds == %d" % (select, table, int(user_input['beds']))
    elif user_input['beds'] == '>3':
        sql = sql + " INTERSECT SELECT %s FROM %s WHERE beds > 3" % (select, table)
    if user_input['baths'] != '>3' and user_input['baths'] != 'Any':
        sql = sql + " INTERSECT SELECT %s FROM %s WHERE baths == %d" % (select, table, int(user_input['baths']))
    elif user_input['baths'] == '>3':
        sql = sql + " INTERSECT SELECT %s FROM %s WHERE baths > 3" % (select, table)
    #sort
    sql = sql + " ORDER BY %s ASC" % (user_input['sortby'])
    #add semicolon
    sql = sql + ';'

    return sql


#format data for modeling
def format_data(df,trans_list,table,engine):
    """
    Performs standard data formatting.
    - Drop uninformative features
    - Convert missing values to 0 and add indicator variables
    - One-hot-feature encoding for categorical features
    - Compute interaction terms with neighborhoods
    
    :params
        df, DataFrame, single listing from the streeteasy database.
        trans_list, list of str, column names for transportation columns in the table
        table, str, name of database table
        engine, sqlalchemy object, connection to sqlite database
    :return:
        df, formatted DataFrame

    """
    #convert NaNs in transportation columns to zeros
    for t in trans_list:
        df[t] = df[t].fillna(value=0)
    #convert remaining NaNs to -1
    df.fillna(value=-1, inplace=True)
    #drop columns
    drop_cols = ['price','link','address','borough','data_id','index','level_0','realtor','scrape_date','test_set']
    for dc in drop_cols:
        df.drop(dc, 1, inplace=True)
    #query the database table to get list of neighborhood and unit types
    nhood_list = np.unique(pd.read_sql(table, engine, columns=['neighborhood']))
    unit_type_list = np.unique(pd.read_sql(table, engine, columns=['unit_type']))
    #unit_type_apartment, unit_type_rental_unit, etc. should be set to zero or one. note: use the methodToCall = getattr() trick to condense this code
    dummy_dict = {}
    for f in nhood_list:
        key = "neighborhood_%s" % (f)
        if f in df['neighborhood'][0]:
            dummy_dict[key] = 1
        else:
            dummy_dict[key] = 0
    for f in unit_type_list:
        key = "unit_type_%s" % (f)
        if f in df['unit_type'][0]:
            dummy_dict[key] = 1
        else:
            dummy_dict[key] = 0
    df = pd.concat((df.drop(['neighborhood','unit_type'],axis=1), pd.DataFrame(dummy_dict, index={0})), axis=1)
    # For 'sq_ft', 'rooms', 'baths', 'days on streeteasy', recode missing values from -1 to 0 and add a new feature for missing value.
    recode_list = ['sq_ft', 'rooms', 'baths', 'beds', 'days_on_streeteasy']
    for old_col in recode_list:
        new_col = "%s_miss" % (old_col)
        df[new_col] = 0  # add a new column of zeros
        df.set_value(df[old_col] == -1, new_col, 1)  # set new_col to 1 where old_col is missing
        df.set_value(df[old_col] == -1, old_col, 0)  # set old_col to zero where missing
    #add interaction terms
    interact_list = ['rooms', 'rooms_miss', 'beds', 'beds_miss', 'baths', 'baths_miss', 'sq_ft', 'sq_ft_miss',
                'days_on_streeteasy', 'days_on_streeteasy_miss']
    for c in interact_list:
        for n in nhood_list:
            new_col = '%s_%s' % (c, n)
            df[new_col] = float(df[c]) * float(df['neighborhood_' + n])
    #add intercept
    df['intercept'] = 1

    return df