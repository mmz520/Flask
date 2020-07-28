import pg

def operate_postgre_tbl_product(sql):
    try:
        # pylint: disable=no-member
        db = pg.connect(dbname = 'postgres', host = 'localhost', user = 'postgres', passwd = '123456')                         

    except Exception as  e:
         print (e.args[0])
         return

    object=db.query(sql).dictresult()


    db.close()
    return object

#print (operate_postgre_tbl_product("select bid from bird"))

def operate_set(sql):
    try:
        # pylint: disable=no-member
        db = pg.connect(dbname = 'postgres', host = 'localhost', user = 'postgres', passwd = '123456')                         

    except Exception as  e:
         print (e.args[0])
         return
    db.query(sql)


    db.close()


