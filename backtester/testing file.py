import pandas as pd
from copy import deepcopy
from tqdm import tqdm
import numpy as np
import pandas_market_calendars as mcal


backtest_instructions = '''Using the backtester
1. create a Backtest() object. Pass your strategy name. i.e. Backtest(strategy = your_strategy_class_name)
2. load your data with backtest.datahandler.load_data_from_excel(data_file_path,bars_to_load)
3. create your strategy class via inheritance from the Strategy class. i.e. your_strategy_class_name(Strategy):
4. code your strategy rules within a method called def strategy_logic(self)
3. run your strategy with backtest.test_strategy(), pass the starting cash you'd like or it will default to $100,000

Using the optimizer
1. create and Optimize() object
2. create your strategy class via inheritance from the Strategy class. i.e. your_strategy_class_name(Strategy):
3. your strategy_logic function should include the following parameters def strategy_logic(self, par1, par2): where par1 and par2 are values for two parameters in your strategy
4. write the rules for your strategy. Be sure to use the par1 and par2 parameter references
5. run Optimize.create_optimization_table method('para name 1',par1 range,'para name 2',par2 range, your_strategy_class_name,data_file_path, starting cash)'''


class Optimize:

    def create_optimization_table(self,par1,par1_range,par2,par2_range,strat_name,data_file_path,cash):

        bars_to_load = max(max(par1_range),max(par2_range))+1

        self.optimization_table_max_drawdown = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_max_drawdown.index.name = str(par1)
        self.optimization_table_max_drawdown.columns.name = str(par2)

        self.optimization_table_CAGR = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_CAGR.index.name = str(par1)
        self.optimization_table_CAGR.columns.name = str(par2)

        self.optimization_table_CAGRMDD = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_CAGRMDD.index.name = str(par1)
        self.optimization_table_CAGRMDD.columns.name = str(par2)

        no_of_iterations = len(par1_range)*len(par2_range)
        q = 1

        for i, val1 in enumerate(par1_range):
            for j, val2 in enumerate(par2_range):
                print('starting iteration '+str(q)+' of '+str(no_of_iterations))
                opt = Backtest(strategy = strat_name)
                opt.datahandler.load_data_from_excel(data_file_path,bars_to_load)
                opt._optimize_strategy(val1,val2,cash)

                opt.analysis._calc_CAGRMDD()

                max_drawdown = opt.analysis.max_drawdown
                CAGR = opt.analysis.CAGR
                CAGRMDD = opt.analysis.CAGRMDD

                self.optimization_table_max_drawdown.iloc[i,j] = max_drawdown
                self.optimization_table_CAGR.iloc[i,j] = CAGR
                self.optimization_table_CAGRMDD.iloc[i,j] = CAGRMDD

                q+=1

class Analysis:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.account = backtest.account
        self.backtest = backtest

    def analyze(self):
        pass

    def _create_underwater_plot(self):
        underwater_plot = self.portfolio.results.loc[:,['portfolio value']]
        underwater_plot.loc[:,'max'] = 0
        for i in range(len(self.portfolio.results)):
            max_val = self.portfolio.results.iloc[0:i,0].max()
            underwater_plot.iloc[i-1,1] = max_val
        underwater_plot.iloc[-1,1] = underwater_plot.iloc[:,0].max()
        self.underwater_plot = underwater_plot

    def _calc_drawdown(self):
        self._create_underwater_plot()
        self.drawdown_df = -(1-(self.underwater_plot.loc[:,'portfolio value']/self.underwater_plot.loc[:,'max']))
        self.max_drawdown = self.drawdown_df.min()

    def _calc_CAGR(self):
        end_val = self.portfolio.results.loc[self.datahandler.strategy_end_date,'portfolio value']
        start_val = self.portfolio.results.loc[self.datahandler.strategy_start_date,'portfolio value']
        no_of_years = (self.portfolio.results.index[-1] - self.portfolio.results.index[0]).days/365
        self.CAGR = ((end_val/start_val)**(1/no_of_years))-1

    def _calc_CAGRMDD(self):
        self._calc_drawdown()
        self._calc_CAGR()
        self.CAGRMDD = -(self.CAGR/self.max_drawdown)


    def results_overview(self):
        pass

class Strategy:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def strategy_logic(self):
        print('Make sure to add the parameter strategy = yourstrategyname when creating an instance of the Backtest class')
        
class Account:
    
    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.analysis = backtest.analysis
        self.strategy = backtest.strategy
        self.backtest = backtest
        
    def _reset_account(self, cash = 100000):
        self.assets = {'Cash':cash}
        self.liabilities = {}
        self.account_history = 0
        
    

class Portfolio:

    def _create_pointers(self,backtest):
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def _reset_portfolio(self,cash):
        self.positions = {}
        self.cash = cash
        self.portfolio_value = cash
        self.most_recent_order = 'No orders submitted'
        self.results = pd.DataFrame(0,columns = ['portfolio value','cash'],index = self.datahandler.data_series[0].index)
        self.position_history = pd.Series(0,index = self.datahandler.data_series[0].index)

    def _update_position_series(self,positions):
        self.position_history.loc[self.datahandler.current_date] = (deepcopy(positions),)

    def _update_portfolio_value(self):
        self.portfolio_value = self.cash
        for sym in self.positions:
            self.portfolio_value += self.positions[sym]['position value']

        self.results.loc[self.datahandler.current_date,'portfolio value'] = self.portfolio_value

    def _update_cash(self):
        self.results.loc[self.datahandler.current_date,'cash'] = self.cash


    def _update_portfolio(self):
        
        del_list=[]
        for sym in self.positions:
            if self.positions[sym]['shares'] == 0:
                del_list.append(sym)
                
        for sym in del_list:
            del self.positions[sym]

        for sym in self.positions:
            self.positions[sym]['position value'] = (self.datahandler.data[sym].loc[self.datahandler.current_date,'Adj Close'])*self.positions[sym]['shares']

        self._update_portfolio_value()
        self._update_cash()
        self._update_position_series(self.positions)
        
    def _update_portfolio_without_removals(self,most_recent_order):
        self.most_recent_order = most_recent_order
        order_dict = self.most_recent_order
        if order_dict['Symbol'] in self.positions:

            self.positions.update({order_dict['Symbol']:{'entry date':self.positions[order_dict['Symbol']]['entry date'],
                                                            'initial entry price': self.positions[order_dict['Symbol']]['initial entry price'],
                                                            'most recent trade date':order_dict['date of execution'],
                                                            'most recent order type':order_dict['order type'],
                                                            'shares':self.positions[order_dict['Symbol']]['shares']+order_dict['shares'],
                                                            'most recent trade price': order_dict['execution price'],}})

            self.cash = self.cash - (order_dict['shares']*order_dict['execution price'])

        if order_dict['Symbol'] not in self.positions:
            self.positions.update({order_dict['Symbol']:{'entry date':order_dict['date of execution'],
                                                            'most recent order type':order_dict['order type'],
                                                            'shares':order_dict['shares'],
                                                            'initial entry price': order_dict['execution price'],}})

            self.cash = self.cash - (order_dict['shares']*order_dict['execution price'])

        if self.cash < 0:
            print('WARNING: You are currently borrowing')

        for sym in self.positions:
            self.positions[sym]['position value'] = (self.datahandler.data[sym].loc[self.datahandler.current_date,'Adj Close'])*self.positions[sym]['shares']

        self._update_portfolio_value()
        self._update_cash()
        self._update_position_series(self.positions)    
            
class Execution:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest
    
    def _clear_pending_orders(self):
        self.pending_orders = {}
        
    def _add_pending_order(self,order):
        if len(self.pending_orders) == 0:
            self.pending_orders[0] = order
        else:
            max_key = max(list(self.pending_orders.keys()))
            self.pending_orders[max_key+1] = order
            
    def _execute_order(self,order):
        self.portfolio._update_portfolio_without_removals(order)
                
    def _scan_and_execute_pending_orders(self):
        for key in self.pending_orders:
            order = self.pending_orders[key]
            order_type = order['order type']
            
            if order_type == 'Market':
                print('1')
                market_order_type = order['desired execution price']
                if market_order_type == 'Open':
                    print('2')
                    print(self.datahandler.current_date)
                    print(pd.Timestamp(order['date of placement']))
                    if self.datahandler.current_date > pd.Timestamp(order['date of placement']):
                        print('3')
                        sym = order['Symbol']
                        sym_data = self.datahandler.data[sym]
                        execution_price = sym_data.loc[self.datahandler.current_date,'Open']
                        order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date})
                        self._execute_order(order)
                        order.update({'status':'executed'})
                        
                if market_order_type == 'Close':
                    sym = order['Symbol']
                    sym_data = self.datahandler.data[sym]
                    execution_price = sym_data.loc[self.datahandler.current_date,'Close']
                    order.update({'execution price':execution_price,'date of execution':self.datahandler.current_date})
                    self._execute_order(order)
                    order.update({'status':'executed'})
                    #update market order method, update portfolio methods, figure out when to execute these new methods, deal with leverage
        self._update_pending_orders()
        
    def _update_pending_orders(self):
        del_list = []
        for key in self.pending_orders:
            order = self.pending_orders[key]
            if order['status'] == 'executed':
                del_list.append(key)
                
        for key in del_list:
            del self.pending_orders[key]
            
        self.pending_order_series[self.datahandler.current_date] = deepcopy(self.pending_orders)

    def market_order(self,symbol,quantity,price = 'Open'):

        if self.order_series.loc[self.datahandler.current_date] != ('No orders',):
            self.order_series.loc[self.datahandler.current_date] = (self.order_series.loc[self.datahandler.current_date] +
                                                        ({'date of placement':self.datahandler.current_date,
                                                         'order type':'Market',
                                                         'Symbol':symbol,
                                                         'shares':quantity,
                                                         'desired execution price':price,
                                                         'status':'pending'},))

        if self.order_series.loc[self.datahandler.current_date] == ('No orders',):
            self.order_series.loc[self.datahandler.current_date] = ({'date of placement':self.datahandler.current_date,
                                                         'order type':'Market',
                                                         'Symbol':symbol,
                                                         'shares':quantity,
                                                         'desired execution price':price,
                                                        'status':'pending'},)
            
        most_recent_order = (self.order_series.loc[self.datahandler.current_date])[-1]
        self._add_pending_order(most_recent_order)
        

class DataHandler:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def _create_date_iter(self):
        self._date_iter = iter(self.date_series)

    def _data_feed(self):
        self.current_date = next(self._date_iter)
        if self.current_date >= self.strategy_start_date:
            self.available_symbols = []
            for sym in self.sym_list:
                if self.current_date in self.data_series[sym].index:
                    sym_dates = pd.Series(self.data_series[sym].index)
                    idx = sym_dates[sym_dates == self.current_date].index[0]
                    if (idx+1) >=self._bars_to_load:
                        self.available_symbols.append(sym)
                        print('appended symbol '+str(sym))
            self.data = self.data_series[self.available_symbols]
            self.available_symbols = tuple(self.available_symbols)
            self.data = (self.data_series).apply(lambda df: df.loc[df.index <= self.current_date,:])
            self.data = (self.data).apply(lambda df: df.iloc[-(self._bars_to_load):,:])
            del_list = [sym for sym in self.data.index if len((self.data[sym]).index)==0]
            for sym in del_list:
                del self.data[sym]

    def _adjust_dates_and_transform_data(self,data_df,bars_to_load,freq):
        if 'min' in freq or 'T' in freq:
            raise AttributeError('This frequency currently not supported')
        elif 'H' in freq:
            raise AttributeError('This frequency currently not supported')
        elif freq == '1D':

            start_dates = []
            end_dates = []
            for ticker in data_df.Symbol.unique():
                
                sym = data_df.loc[data_df.Symbol == ticker,:]
                sym_dates = list(sym.index)
                begin_date = sym_dates[0]
                end_date = sym_dates[-1]
                start_dates.append(begin_date)
                end_dates.append(end_date)
            start_date = min(start_dates)
            end_date = max(end_dates)

            nyse = mcal.get_calendar('NYSE')
            sch = nyse.schedule(start_date = start_date, end_date = end_date)
            indx = mcal.date_range(sch, frequency='1D')

            cleaned_dates = []
            for date in indx:
                clean_date = pd.Timestamp(str(date.month)+'/'+str(date.day)+'/'+str(date.year), tz = 'UTC')
                cleaned_dates.append(clean_date)
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)
            
            data_df.index = cleaned_dates

        elif freq =='1W':
            
            start_dates = []
            end_dates = []
            for ticker in data_df.Symbol.unique():
                
                sym = data_df.loc[data_df.Symbol == ticker,:]
                sym_dates = list(sym.index)
                begin_date = sym_dates[0]
                end_date = sym_dates[-1]
                start_dates.append(begin_date)
                end_dates.append(end_date)

            start_date = min(start_dates)
            end_date = max(end_dates)

            days_to_add = 4-end_date.dayofweek
            adj_end_date = end_date + pd.Timedelta(str(days_to_add)+' days')

            nyse = mcal.get_calendar('NYSE')
            sch = nyse.schedule(start_date = start_date, end_date = adj_end_date)
            indx = mcal.date_range(sch, frequency='1D')

            cleaned_dates = []
            for date in indx:
                clean_date = pd.Timestamp(str(date.month)+'/'+str(date.day)+'/'+str(date.year), tz = 'UTC')
                cleaned_dates.append(clean_date)
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)

            ilist = []
            for i in range(len(cleaned_dates.dayofweek)):
                if i >0:
                    prev_val = cleaned_dates.dayofweek[i-1]
                    cur_val = cleaned_dates.dayofweek[i]
                    if cur_val<prev_val:
                        ilist.append(i-1)
            ilist.append(i)
            cleaned_dates = cleaned_dates[ilist]

            paired_dates = pd.Series(cleaned_dates,index = data_df.index.unique())

            new_index = pd.DatetimeIndex([paired_dates[date] for date in data_df.index], tz = 'UTC')
            data_df.index = new_index

        elif freq == '1M':

            start_dates = []
            end_dates = []
            for ticker in data_df.Symbol.unique():
                
                sym = data_df.loc[data_df.Symbol == ticker,:]
                sym_dates = list(sym.index)
                begin_date = sym_dates[0]
                end_date = sym_dates[-1]
                start_dates.append(begin_date)
                end_dates.append(end_date)

            start_date = adj_start_date =  min(start_dates)
            end_date =  adj_end_date =  max(end_dates)
            
            if end_date.day <28:
                adj_end_date = end_date + pd.Timedelta(str(32)+' days')

            else:
                start_day = adj_start_date.dayofweek
                if start_day == 5 or start_day == 6:
                    days_to_subtract = start_day-4
                    adj_start_date = start_date - pd.Timedelta(str(days_to_subtract)+' days')

            nyse = mcal.get_calendar('NYSE')
            sch = nyse.schedule(start_date = adj_start_date, end_date = adj_end_date)
            indx = mcal.date_range(sch, frequency='1D')

            cleaned_dates = []
            for date in indx:
                clean_date = pd.Timestamp(str(date.month)+'/'+str(date.day)+'/'+str(date.year), tz = 'UTC')
                cleaned_dates.append(clean_date)
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)

            ilist = []
            for i in range(len(cleaned_dates)):
                if i > 0:
                    prev_val = cleaned_dates.month[i-1]
                    cur_val = cleaned_dates.month[i]
                    if cur_val != prev_val:
                        ilist.append(i-1)
            if end_date.day>=28:
                ilist.append(i)
            
            cleaned_dates = cleaned_dates[ilist]

            paired_dates = pd.Series(cleaned_dates,index = data_df.index.unique())

            new_index = pd.DatetimeIndex([paired_dates[date] for date in data_df.index], tz = 'UTC')
            data_df.index = new_index
            

        sym_list = data_df.Symbol.unique()
        i = 0
        for sym in sym_list:
            if i == 1:
                sym_data = data_df.loc[data_df.loc[:,'Symbol']==sym,:]
                ds = pd.Series([sym_data])
                ds.index = [sym]
                data_series = data_series.append(ds)
            if i == 0:
                sym_data = data_df.loc[data_df.loc[:,'Symbol']==sym,:]
                data_series = pd.Series([sym_data])
                data_series.index = [sym]
                i = 1

        self.data_series = data_series
        self._bars_to_load = bars_to_load
        self.data_start_date = start_date
        self.strategy_start_date = cleaned_dates[bars_to_load-1]
        self.data_end_date = self.strategy_end_date= cleaned_dates[-1]
        self.sym_list = sym_list
        self.date_series = pd.Series(cleaned_dates)

    def load_data_from_excel(self,path,bars_to_load,freq):
        data_df = pd.read_excel(path,index_col = 'Date')
        self._adjust_dates_and_transform_data(data_df,bars_to_load,freq)
    
    def load_data_from_dataframe(self,dataframe,bars_to_load,freq):
        data_df = dataframe
        self._adjust_dates_and_transform_data(data_df,bars_to_load,freq)

class Backtest:

    def __init__(self,strategy = Strategy,portfolio = Portfolio,
                 execution = Execution, datahandler = DataHandler,
                 analysis = Analysis, optimize = Optimize, account = Account):

        self.strategy = strategy()
        self.portfolio = portfolio()
        self.execution = execution()
        self.datahandler = datahandler()
        self.analysis = analysis()
        self.account = account()

        self.strategy._create_pointers(self)
        self.portfolio._create_pointers(self)
        self.datahandler._create_pointers(self)
        self.execution._create_pointers(self)
        self.analysis._create_pointers(self)
        self.account._create_pointers(self)

    def test_strategy(self,cash = 100000):
        self.datahandler._create_date_iter()

        self.portfolio._reset_portfolio(cash)
        
        self.execution._clear_pending_orders()

        self.execution.order_series = pd.Series([('No orders',) for x in range(len(self.datahandler.data_series[0]))])
        self.execution.order_series.index = self.datahandler.data_series[0].index
        
        self.execution.pending_order_series = pd.Series([('No pending orders',) for x in range(len(self.datahandler.data_series[0]))])
        self.execution.pending_order_series.index = self.datahandler.data_series[0].index

        for i in tqdm(range(len(self.datahandler.data_series[0]))):
            self.datahandler._data_feed() #updates self.datahandler.data
            self.portfolio._update_portfolio()
            if self.datahandler._bars_to_load == len(self.datahandler.data[0]):
                self.execution._scan_and_execute_pending_orders()
                self.strategy.strategy_logic()
                self.execution._scan_and_execute_pending_orders()
            self.portfolio._update_portfolio()
            self.analysis.analyze()

    def _optimize_strategy(self,val1,val2,cash = 100000):

        self.datahandler._create_date_iter()

        self.portfolio._reset_portfolio(cash)

        self.strategy.signal_series = pd.Series([('No signals',) for x in range(len(self.datahandler.data_series[0]))])
        self.strategy.signal_series.index = self.datahandler.data_series[0].index

        self.execution.order_series = pd.Series([('No orders',) for x in range(len(self.datahandler.data_series[0]))])
        self.execution.order_series.index = self.datahandler.data_series[0].index

        for i in range(len(self.datahandler.data_series[0])):
            self.datahandler._data_feed() #updates self.datahandler.data
            self.portfolio._update_portfolio()
            if self.datahandler._bars_to_load == len(self.datahandler.data[0]):
                self.strategy.strategy_logic(val1,val2)
            self.portfolio._update_portfolio()
            self.analysis.analyze()



backtest = Backtest()
backtest.datahandler.load_data_from_excel(r"C:\Users\jatni\Desktop\Files\Personal Files\Python\Fake Dataset Monthly.xlsx",3,'1M')



backtest.datahandler._create_date_iter()



backtest.datahandler._data_feed()
backtest.datahandler._data_feed()
backtest.datahandler._data_feed()









