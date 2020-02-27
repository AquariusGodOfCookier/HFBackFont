import pymysql
import logging
import traceback
import io
import sys
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class DBConnect:
    def __init__(self, host, user, password, database,logPath):
        self.db = pymysql.connect(
            host=host, user=user, password=password, database=database
        )
        self.cursor = self.db.cursor()
        logging.basicConfig(
            filename=logPath + "\dblog.log",
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filemode="a",
        )

    def exce_data_all(self, sql):
        res = ""
        try:
            self.cursor.execute(sql)
            res = self.cursor.fetchall()
            return res
        except Exception as data:
            logging.error("%s____%s" % (Exception, data))

    def exce_data_one(self,sql):
        res = ""
        try:
            self.cursor.execute(sql)
            res = self.cursor.fetchone()
            return res
        except Exception as data:
            logging.error("%s____%s" % (Exception, data))
            return "error"

    def exce_data_commitsql(self,sql):
        try:
            self.cursor.execute(sql)
            self.db.commit()
            return "success"
        except Exception as data:
            self.db.rollback()
            print(data)
            return "error"

    def exce_data_commitsqls(self,objects):
        try:
            for sql in objects:
                self.cursor.execute(sql)
            self.db.commit() 
            return 'success'
        except Exception as data:
            self.db.rollback()
            print(data)
            return "error"   
    
    def exce_insert_data(self,objects,table):
        try:
            keyList = []
            valueList = []
            keyStr = '('
            valueStr = ''
            for data in objects:
                keyList.append(data)
                valueList.append('%s'%objects[data])
            keyStr = ','.join(keyList)
            valueStr = ','.join(valueList)
            sql = "insert into %s (%s) values (%s)"%(table,keyStr,valueStr)
            self.cursor.execute(sql)
            self.db.commit()
            return 'success'
        except Exception as data:
            self.db.rollback()
            logging.error("DBERRPR insert_data%s____%s" % (Exception, data))
            return 'error'
    
    def exce_update_data(self,sql):
        try:
            self.cursor.execute(sql)
            self.db.commit()
        except Exception as data:
            self.db.rollback()
            logging.info("DBERROR Update_data%s____%s" % (Exception, data))

    def close(self):
        try:
            self.db.close()
            return "关闭成功"
        except Exception as err:
            logging.error("close error '%s'" % err)


