import sqlite3
import pandas as pd

con = sqlite3.connect('streeteasy_db.sqlite')
df_train = pd.read_sql("SELECT * FROM %s" % ('train_data'), con)
df_test = pd.read_sql("SELECT * FROM %s" % ('test_data'), con)
# use only new listings in the test set not found in the training set
df_test = df_test[~df_test['data_id'].isin(df_train['data_id'])]
# create an 'test' column to indicate membership in test set, then combine
df_train['test_set'] = 0
df_test['test_set'] = 1
df = pd.concat([df_train, df_test], axis=0)
df = df.fillna(0)  # if concat produced NaNs for train/test data, fill with 0


df.to_sql('all_data',con)

print df_train

#####################
import sqlite3
import pandas as pd
con = sqlite3.connect('streeteasy_db.sqlite')
var_list = "data_id, address, borough, price, sq_ft, beds, baths, neighborhood"
sql = "SELECT %s FROM %s WHERE price <= %d" % (var_list,'all_data',2000)
sql = sql + " INTERSECT SELECT %s FROM %s WHERE price >= %d" % (var_list,'all_data',1000)
sql = sql + " INTERSECT SELECT %s FROM %s WHERE beds == %d" % (var_list,'all_data',1)
df_train = pd.read_sql(sql,con)
print df_train.shape[0]


#######################


from sqlalchemy import create_engine, select, Table, MetaData
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///streeteasy_db.sqlite')
conn = engine.connect()
meta = MetaData()
all_data = Table('all_data', meta, autoload=True, autoload_with=engine)

s = select(['all_data'])

session = sessionmaker()
session.configure(bind=engine)
s = session()

