import requests
import sys
import re
import argparse
from crowbank.petadmin import Environment
from crowbank.fb_reviews import sql
from _sqlite3 import sqlite_version

# headers = { 'Authorization: Bearer 1huYkz44prHdcK89cc7YccEDf8IelgSFK_-hTKAHE', }

base = 'https://api.freeagent.com/v2/'

class FreeAgent:
    def __init__(self):
        self.parameters = {}
        self.items = {}
        self.bank_accounts = []
        self.transactions = []
        self.journals = []
        self.connection = None
        self.platform = sys.platform
        self.env = Environment('prod')

    def read_parameters(self):
        cur = self.env.get_cursor()
        sql = 'select api_key, api_value from tblfreeagent_api'
        cur.execute(sql)
        for row in cur:
            self.parameters[row[0]] = row[1]
    
    def refresh_access_token(self):
        resp = requests.post(self.base_url,
                             data = {'client_secret' : self.parameters['oauth_secret'],
                                     'grant_type' : 'refresh_token',
                                     'refresh_token' : self.parameters['refresh_token'],'client_id' : self.oauth_identifier})
        
        if resp.status_code == 200:
            self.parametrs['access_token'] = resp.json()['access_token']
            sql = "update tblfreeagent_api set api_value = '%s' where api_key = 'access_token'" % self.parametrs['access_token']
            self.env.execute(sql)
    
    def request(self, url, params = {}):
        headers = { 'Authorization': 'Bearer %s' % self.parameters['access_token'] }
        if url[:8] != self.parameters['base_url'][:8]:
            url = self.parameters['base_url'] + url
        resp = requests.get(url, headers=headers, params=params)
        resp = resp.json()
        return resp

#     def get_all_items(self, item_class, params = {}):
#         page = 1
#         cont = True
#         items = []
#         if not self.parameters:
#             self.read_parameters()
#         
#         while cont:
#             params.update( {'page' : page, 'per_page' : 100} )
#             url = self.parameters['base_url'] + item_class.item_name
#             resp = self.request(url, params)
#             resp = resp[item_class.item_name]
#             items += resp
#             print ("Loaded page %d" % page)
#             page += 1
#             if len(resp) < 100:
#                 cont = False
#         
#         mapped = map(lambda s: item_class(s), items)
#         self.items[item_class.item_name] = mapped
        
    def get_bank_accounts(self):
        if not 'bank_accounts' in self.items:
            self.items['bank_accounts'] = BankAccount.read(self.env)
        
        return self.items['bank_accounts']
            
#     def get_transactions(self, updated_since=None):
#         if not self.bank_accounts:
#             conn = self.get_connection()
#             cur = conn.cursor()
#             self.bank_accounts = BankAccount.read(cur)
#     
#         self.bank_transactions = []
#         for bank_account in self.bank_accounts:
#             params = {'bank_account' : bank_account.url}
#             if updated_since:
#                 params['updated_since'] = str(updated_since)
#             self.bank_transactions += self.get_all_items(BankTransaction, params)
#         self.bank_explanations = []
#         for t in self.bank_transactions:
#             self.bank_explanations += t.bank_transaction_explanations
            

class FreeAgentItem(object):
    @classmethod
    def adorn(cls, name):
        return cls.db_prefix + name
    
    @classmethod
    def strip(cls, name):
        return name.replace(cls.db_prefix, '')    
    
    @classmethod
    def read(cls, env):
        sql = "Select %s from %s" % (", ".join(map(cls.adorn, cls.db_types.keys())), cls.db_table)
        cur = env.get_cursor()
        cur.execute(sql)
        return [cls({key : value for (key, value) in zip(cls.db_types.keys(), row)}) for row in cur]

    @classmethod
    def download(cls, fa, params = {}):
        page = 1
        cont = True
        items = []
        if not fa.parameters:
            fa.read_parameters()
        
        while cont:
            params.update( {'page' : page, 'per_page' : 100} )
            url = fa.parameters['base_url'] + cls.item_name
            resp = fa.request(url, params)
            resp = resp[cls.item_name]
            items += resp
            print ("Loaded page %d" % page)
            page += 1
            if len(resp) < 100:
                cont = False
        
        mapped = map(cls, items)
        return mapped
    
    @classmethod
    def write_all(cls, env, items):
        for item in items:
            item.write(env)
    
    def __init__(self, response):
        self.dict = response
        if not 'id' in response:
            m = re.match('.*/(\d+)$', self.dict['url'])
            self.id = int(m.group(1))
            self.dict['id'] = self.id
        
    def __getattr__(self, name):
        if name in self.dict:
            return self.dict[name]
        else:
            return None
        
    def write(self, env):
        sql = "select count(*) from %s where %sid = %d" % (self.db_table, self.db_prefix, self.id)
        cur = env.get_cursor()
        cur.execute(sql)
        for row in cur:
            c = row[0]
        
        if c > 0:
            sql = "delete from %s where %sid = %d" % (self.db_table, self.db_prefix, self.id)
            env.execute(sql)
            
        keys = list(set(self.db_types.keys()) & set(self.dict.keys()))
        fields = map(self.adorn, keys)
        sql = "insert into %s (%s) values (" % (self.db_table + "_staging", ", ".join(fields))
        values = []
        for k in keys:
            v = self.dict[k]
            db_type = self.db_types[k]
            if db_type in ['string', 'date', 'datetime']:
                values.append("'%s'" % v.replace("'", "''"))
            elif db_type == 'boolean':
                values.append('1' if v else '0')
            else:
                values.append(str(v))
        sql += ', '.join(values)
        sql += ')'
        env.execute(sql)
        

class Category(FreeAgentItem):
    class_name = 'Category'
    item_name = 'categories'
    db_table = 'fa_category'
    db_prefix = 'fac_'
    db_types = {
        'id' : 'int',
        'url' : 'string',
        'description' : 'string',
        'nomical_code' : 'string',
        'group_description' : 'string',
        'auto_sales_tax_rate' : 'string',
        'allowable_for_tax' : 'boolean',
        'tax_reporting_name' : 'string'
    }
    
    
class User(FreeAgentItem):
    class_name = 'User'
    item_name = 'users'
    db_table = 'fa_user'
    db_prefix = 'fau_'
    db_types = {
        'id' : 'int',
        'url' : 'string',
        'email' : 'string',
        'first_name' : 'string',
        'last_name' : 'string',
        'ni_number' : 'string',
        'email' : 'string',
        'unique_tax_reference' : 'string',
        'role' : 'string',
        'opening_milage' : 'decimal',
        'send_invitation' : 'boolean',
        'permission_level' : 'int',
        'created_at' : 'datetime',
        'updated_at' : 'datetime',
        'existing_password' : 'string',
        'password' : 'string',
        'password_confirmation' : 'string'
        }


class BankAccount(FreeAgentItem):
    class_name = 'BankAccount'
    item_name = 'bank_accounts'
    db_table = 'fa_bankaccount'
    db_prefix = 'ba_'
    db_types = {
        'id' : 'int',
        'url' : 'string',
        'type' : 'string',
        'name' : 'string',
        'currency' : 'string',
        'is_personal' : 'boolean',
        'is_primary' : 'boolean',
        'status' : 'string',
        'bank_name' : 'string',
        'opening_balance' : 'money',
        'bank_code' : 'string',
        'current_balance' : 'money',
        'latest_activity_date' : 'date',
        'created_at' : 'datetime',
        'updated_at' : 'datetime',
        'account_number' : 'string',
        'sort_code' : 'string',
        'secondary_sort_code' : 'string',
        'iban' : 'string',
        'bic' : 'string',
        'email' : 'string'
    }


class BankTransactionExplanation(FreeAgentItem):
    class_name = 'BankTransactionExplanation'
    item_name = 'bank_transaction_explanation'
    db_table = 'fa_bankexplanation'
    db_prefix = 'fabe_'
    db_types = {
        'id' : 'int',
        'url' : 'string',
        'bank_account' : 'string',
        'bank_transaction' : 'string',
        'type' : 'string',
        'ec_status' : 'string',
        'place_of_supply' : 'string',
        'dated_on' : 'date',
        'gross_value' : 'money',
        'sales_tax_rate' : 'decimal',
        'second_sales_tax_rate' : 'decimal',
        'manual_sales_tax_amount' : 'money',
        'manual_second_sales_tax_amount' : 'money',
        'description' : 'string',
        'category' : 'string',
        'cheque_number' : 'string',
        'marked_for_review' : 'boolean',
        'is_money_in' : 'boolean',
        'is_money_out' : 'boolean',
        'is_money_aid_to_user' : 'boolean',
        'is_locked' : 'boolean',
        'locked_reason' : 'string',
        'project' : 'string',
        'rebill_type' : 'string',
        'rebill_factor' : 'decimal',
        'receipt_reference' : 'string',
        'paid_invoice' : 'string',
        'foreign_currency_value' : 'money',
        'paid_bill' : 'string',
        'paid_user' : 'string',
        'transfer_bank_account' : 'string',
        'stock_item' : 'string',
        'stock_altering_quantity' : 'int',
        'asset_life_years' : 'int',
        'disposed_asset' : 'string'
        }

    @classmethod
    def download(cls, fa, params = {}):
        explanations = []
        if 'bank_transactions' in fa.items:
            transactions = fa.items['bank_transactions']
        else:
            transactions = BankTransaction.download(fa, params)
        for t in transactions:
            explanations += t.bank_transaction_explanations
        
        return explanations     


class BankTransaction(FreeAgentItem):
    class_name = 'BankTransaction'
    item_name = 'bank_transactions'
    db_table = 'fa_banktransaction'
    db_prefix = 'fabt_'
    db_types = {
        'id' : 'int',
        'url' : 'string',
        'amount' : 'money',
        'bank_account' : 'string',
        'dated_on' : 'date',
        'description' : 'string',
        'uploaded_at' : 'datetime',
        'unexplained_amount' : 'money',
        'is_manual' : 'boolean'
    }


    @classmethod
    def download(cls, fa, updated_since=None):
        accounts = fa.get_bank_accounts()

        transactions = []
        for account in accounts:
            params = {'bank_account' : account.url}
            if updated_since:
                params['updated_since'] = str(updated_since)
            transactions += super().download(BankTransaction, params)
        return transactions
    
    
    def __init__(self, response):
        super().__init__(response)
        self.dict['bank_transaction_explanations'] = map(BankTransactionExplanation, self.dict['bank_transaction_explanations'])
        pass
    

class JournalEntry(FreeAgentItem):
    class_name = 'JournalEntry'
    item_name = ''
    db_table = 'fa_journal_entry'
    db_prefix = 'faje_'
    db_types = {
        'id' : 'int',
        'journal_set_id' : 'int',
        'url' : 'string',
        'category' : 'string',
        'debit_value' : 'money',
        'user' : 'string',
        'stock_item' : 'string',
        'stock_altering_quantity' : 'int',
        'bank_account' : 'string'
    }

    @classmethod
    def download(cls, fa, params = {}):
        if 'journal_sets' in fa.items:
            sets = fa.items['journal_sets']
        else:
            sets = JournalSet.download(fa, params)
            
        entries = []
        for s in sets:
            entries += s.journal_entries
            
        return entries
    
    
class JournalSet(FreeAgentItem):
    class_name = 'JournalSet'
    item_name = 'journal_sets'
    db_table = 'fa_jounral_set'
    db_prefix = 'faj_'
    db_types = {
        'id' : 'int',
        'url' : 'string',
        'dated_on' : 'date',
        'description' : 'string',
        'tag' : 'string'
        }
    
    def __init__(self, response):
        super().__init__(response)
        self.dict['journal_entries'] = map(JournalEntry, self.dict['journal_entries'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="Primary command such as download, upload, refresh")
    parser.add_argument("-item_type", choices=['journals', 'categories', 'accounts', 'users'], help="Item type to download/upload [transactions (default) / journals / categories / accounts / users]")
    parser.add_arguemnt("-asof", type=str, action="store", help="Cutoff modification date for downloads; defaults to most recent download of given type")

    args = parser.parse_args()
    command = args.command
    
    fa = FreeAgent()
    
    if command == 'download':
        if args.item_type == 'journals':
            fa['journal_sets'] = JournalSet.download(fa)
            JournalSet.write_all(fa.env, items)
            
        download(args.item_type, args.asof)
        return
    
# def main():
#     fa = FreeAgent()
# 
#     fa.get_transactions()
#     
#     conn = fa.get_connection()
#     cur = conn.cursor()
#     
#     for t in fa.bank_transactions:
#         t.write(cur)
#     for e in fa.bank_explanations:
#         e.write(cur)
#     conn.commit()


if __name__ == '__main__':
    main()